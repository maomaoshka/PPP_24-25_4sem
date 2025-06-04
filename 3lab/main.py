from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status
import redis.asyncio as redis
import asyncio, json, os
from app.schemas.schemas import User, Image
import secrets
import sqlite3
import uvicorn
from app.api.endpoints import FastApiServerInfo 
from app.websocket.endpoints import WebsocketInfo
from app.core.config import Settings 
from app.celery.celery_app import celery_app
from app.celery.celery_app import REDIS_BROKER
from app.celery.tasks import binarization

DB_PATH = "app/db/database.db"
app = FastAPI()

class ConnectionManager: # параллельно работаем с кучей клиентов
    def __init__(self):
        self.active: list[WebSocket] = []
    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)
    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)
    async def broadcast(self, msg: dict):
        text = json.dumps(msg)
        for ws in self.active:
            await ws.send_text(text)

manager = ConnectionManager()

@app.on_event("startup")
async def on_startup():
    global redis
    redis = await redis.from_url(REDIS_BROKER, decode_responses=True)
    asyncio.create_task(notify_loop())

async def notify_loop():
    sub = redis.pubsub()
    await sub.subscribe(WebsocketInfo.NOTIFICATIONS)
    while True:
        msg = await sub.get_message(ignore_subscribe_messages=True, timeout=None)
        if msg and msg["data"]:
            data = json.loads(msg["data"])
            await manager.broadcast(data)
        await asyncio.sleep(0.01)

@app.websocket(f"/ws/{WebsocketInfo.NOTIFICATIONS}")
async def ws_notifications(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)

# это та штука, которая потом отправится на celery
@app.post(f"/tasks/{WebsocketInfo.BINARIZATION}")
async def run_bin(req: Image):
    task = binarization.delay(req.image_name, req.image_url)
    return {"task_id": task.id}

@app.post(FastApiServerInfo.SIGN_UP_ENDPOINT)
async def sign_up(user: User):
    token, id = None, None
    existing_users = dict()
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM Users WHERE email = ?", (user.email,))
    rows = cursor.fetchall()
    if rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь уже зарегистрирован.")
    else:
        cursor.execute("INSERT INTO Users (email, password) VALUES (?, ?)", (user.email, user.password))
        connection.commit()
        cursor.execute("SELECT id FROM Users WHERE email = ? AND password = ?", (user.email, user.password))
        id = cursor.fetchall()[0][0]
        token = secrets.token_urlsafe()
        existing_users[id] = {"id": id, "email": user.email, "token": token}
    connection.close()
    return existing_users[id]

# это штучка для авторизации по базе
@app.post(FastApiServerInfo.LOGIN_ENDPOINT)
async def login(user: User):
    token, id = None, None
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM Users WHERE email = ? AND password = ?", 
                   (user.email,user.password))
    rows = cursor.fetchone()
    if rows:
        id, email, password = rows
        token = secrets.token_urlsafe()
    else:
        connection.close()
        return {"Message": "Incorrect password"}
    
    connection.close()
    return {"id": id, "email": email, "token": token}

if __name__ == "__main__":
    uvicorn.run(app, host=Settings.IP, port=Settings.PORT)