from fastapi import FastAPI
from app.schemas.schemas import User
import secrets
import sqlite3
import uvicorn
from app.api.endpoints import FastApiServerInfo

DB_PATH = "app/db/database.db"

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "it works"}

# Добавление нового пользователя в бд
@app.post(FastApiServerInfo.SIGN_UP_ENDPOINT)
async def sign_up(user: User):
    token, id = None, None
    existing_users = dict()
    # Соединение с бд
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    # Запрос на поиск пользователя по почте
    cursor.execute("SELECT * FROM Users WHERE email = ?", 
                   (user.email,))
    rows = cursor.fetchall()
    if not rows:
        cursor.execute("INSERT INTO Users (email, password) VALUES (?, ?)", 
                    (user.email, user.password))
        # словарь для return
        connection.commit()
        # id
        cursor.execute("SELECT id FROM Users WHERE email = ? AND password = ?", 
                    (user.email, user.password))
        id = cursor.fetchall()[0][0]
        # токен
        token = secrets.token_urlsafe()
        # записываю в existing_users
        existing_users[id] = {
                "id": id,
                "email": user.email,
                "token": token  
            }
        
    connection.close()
    return existing_users

# информация авторизованного пользователя
logged_user = {
    "id": -1,
    "email": "_@_._"
}
# авторизация
@app.post(FastApiServerInfo.LOGIN_ENDPOINT)
async def login(user: User):
    token, id = None, None
    # Соезинение с бд
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    # Запрос на поиск пользователя по паролю и почте
    cursor.execute("SELECT * FROM Users WHERE email = ? AND password = ?", 
                   (user.email,user.password))
    # Такой пользователь всегда один
    rows = cursor.fetchone()
    if rows:
        # Распаковываю данные о пользователя
        id, email, password = rows
        # Генерирую токен
        token = secrets.token_urlsafe()
        # Добавляю ответ
        logged_user["id"] = id
        logged_user["email"] = email
    else:
        # Если введн не первый password, то возвращаю сообщение об ошибке
        connection.close()
        return {"Message": "Incorrect password"}
    
    connection.close()
    # Вместо возврата logged
    return {
        "id": logged_user["id"],
        "email": logged_user["email"],
        "token": token
    }

# Вывод информации об авторизованном пользователе
@app.post(FastApiServerInfo.USER_INFO_ENDPOINT)
async def login():
    return logged_user

if __name__ == "__main__":
    # Чтобы не прописывать каждый раз команду uvicorn main:app --host 127.0.0.1 --port 12000 
    # и удобно устанавливать нужный IP и PORT, всё выношу в класс FastApiServerInfo в app/api/models
    uvicorn.run(app, host=FastApiServerInfo.IP, port=FastApiServerInfo.PORT)