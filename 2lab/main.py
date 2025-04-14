from fastapi import FastAPI

import secrets
import uvicorn
import sqlite3

from app.api.endpoints import FastApiServerInfo
from app.schemas.schemas import User

DB_PATH = "app/db/database.db" # тут видимо надо будет тоже дописать штучку для линукса
app = FastAPI()

@app.get("/")
async def root():
    return {"message": "it works!"} # просто проверка для себя

@app.post(FastApiServerInfo.SIGN_UP_ENDPOINT)
async def sign_up(user: User):
    token, id = None, None
    current_users = dict()
    connect = sqlite3.connect(DB_PATH)
    cursor = connect.cursor()

    cursor.execute("SELECT * FROM Users WHERE email = ?", (user.email,))
    rows = cursor.fetchall()
    if not rows:
        cursor.execute("INSERT INTO Users (email, password) VALUES (?, ?)", (user.email, user.password))
        connect.commit()
        # айдишник
        cursor.execute("SELECT id FROM Users WHERE email = ? AND password = ?", (user.email, user.password))
        id = cursor.fetchall()[0][0]
        # токен
        token = secrets.token_urlsafe()
        # записываю в current_users
        current_users[id] = {
                "id": id,
                "email": user.email,
                "token": token  
            }
    connect.close()
    return current_users

# информация авторизованного пользователя
current_user = {
    "id": -1,
    "email": "_@_._"}

# авторизация
@app.post(FastApiServerInfo.LOGIN_ENDPOINT)
async def login(user: User):
    token, id = None, None
    connect = sqlite3.connect(DB_PATH)
    cursor = connect.cursor()
    # поиск пользователя по почте и паролю
    cursor.execute("SELECT * FROM Users WHERE email = ? AND password = ?", (user.email,user.password))
    rows = cursor.fetchone()
    if rows:
        # данные о пользователях
        id, email, password = rows
        token = secrets.token_urlsafe()
        current_user["id"] = id
        current_user["email"] = email
    else:
        connect.close()
        return {"Message": "Incorrect password"}
    
    connect.close()

    return {"id": current_user["id"],
        "email": current_user["email"],
        "token": token}

@app.post(FastApiServerInfo.USER_INFO_ENDPOINT)
async def login():
    return current_user

if __name__ == "__main__":
    uvicorn.run(app, host=FastApiServerInfo.IP, port=FastApiServerInfo.PORT)