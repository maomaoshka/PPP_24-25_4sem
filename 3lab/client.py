import asyncio
import httpx
import websockets
from typing import Dict, Callable
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from app.api.endpoints import FastApiServerInfo
from app.websocket.endpoints import WebsocketInfo
from app.core.config import Settings
import json
import os, sys

class AsyncClient:
    def __init__(self):
        self.base_url = f"http://{Settings.IP}:{Settings.PORT}"
        self.ws_url = f"ws://{Settings.IP}:{Settings.PORT}/ws/{WebsocketInfo.NOTIFICATIONS}"
        self.user_token: str = None
        self.user_email: str = None
        self.running = True
        self.session = PromptSession()
        self.commands: Dict[str, Callable] = {"login": self.login, "registr": self.register, \
            "cls": self.clear_console, "exit": self.exit, "bin": self.bin}
        self.ws_task: asyncio.Task = None
        self.input_task: asyncio.Task = None
        self.active_tasks = list()
    async def show_notification(self, message: str):
        with patch_stdout():
            print(f"[УВЕДОМЛЕНИЕ]: {message}")
            sys.stdout.flush()
    
    async def safe_print(self, message: str):
        with patch_stdout():
            prefix = f"[{self.user_email.split('@')[0]}@{self.user_token}]" if self.user_token else "[guest@anon]"
            print(f"{prefix} --> {message}\n", end="")
            sys.stdout.flush()
    async def websocket_listener(self):
        while self.running:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    async for message in ws:
                        data = json.loads(message)
                        if data['task_id'] in self.active_tasks:
                            await self.show_notification(json.dumps(data, ensure_ascii=False))
                            if data["status"] == "done":
                                self.active_tasks.remove(data['task_id'])
            except Exception as e:
                await self.safe_print(f"WebSocket error: {str(e)}")
                await asyncio.sleep(5)
    # авторизация
    async def login(self):
        email = await self.session.prompt_async("e-mail: ")
        password = await self.session.prompt_async("password: ", is_password=True)
        self.session.is_password = False
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{self.base_url}{FastApiServerInfo.LOGIN_ENDPOINT}",
                    json={"email": email, "password": password})
                if response.status_code == 200:
                    data = response.json()
                    self.user_token = data['token']
                    self.user_email = data['email']
                    await self.safe_print("пользователь авторизован")
                else:
                    await self.safe_print(f"произошла ошибка: {response.text}")
                    
            except Exception as e:
                await self.safe_print(f"ошибка соединения: {str(e)}")
    # регистрация
    async def register(self):
        email = await self.session.prompt_async("e-mail: ")
        password = await self.session.prompt_async("password: ", is_password=True)
        self.session.is_password = False
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{self.base_url}{FastApiServerInfo.SIGN_UP_ENDPOINT}",
                    json={"email": email, "password": password})
                if response.status_code == 200:
                    data = response.json()
                    self.user_token = data['token']
                    self.user_email = data['email']
                    await self.safe_print("новый пользователь зарегистрирован")
                else:
                    await self.safe_print(f"произошла ошибка: {response.text}")
            except Exception as e:
                await self.safe_print(f"ошибка соединения: {str(e)}")
    
    # функция под бинаризацию картинок
    async def bin(self):
        name = await self.session.prompt_async("имя файла: ")
        URL = await self.session.prompt_async("URL картинки: ")
        async with httpx.AsyncClient() as client:
            try:
                if not self.user_token:
                    raise Exception("пройдите авторизацию") 
                response = await client.post(
                    f"{self.base_url}/tasks/{WebsocketInfo.BINARIZATION}",
                    json = {"image_name": name, "image_url": URL}, headers={"Authorization": f"Bearer {self.user_token}"})
                self.active_tasks.append(response.json().get('task_id'))
                # тут айдишник летит в список задач на выполнение
            except Exception as e:
                await self.safe_print(f"произошла ошибка: {str(e)}") 
    
    async def clear_console(self):
        os.system("cls" if os.name == "nt" else "clear")
        await self.safe_print("почистили мусор")

    async def exit(self):
        self.running = False
        await self.safe_print("пока-пока!")
        sys.exit()

    async def command_handler(self):
        while self.running:
            try:
                command = await self.session.prompt_async("чего желаете? ", refresh_interval=0.1)
                
                if command in self.commands:
                    await self.commands[command]()
                elif command == "help":
                    await self.safe_print("список команд: " + ", ".join(self.commands))
                else:
                    await self.safe_print("такой команды нет")

            except KeyboardInterrupt:
                await self.exit()
            except Exception as e:
                await self.safe_print(f"произошла ошибка: {str(e)}")
    
    async def run(self):
        self.ws_task = asyncio.create_task(self.websocket_listener())
        self.input_task = asyncio.create_task(self.command_handler())
        await asyncio.gather(self.ws_task, self.input_task, return_exceptions=True)

if __name__ == "__main__": 
    client = AsyncClient()
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        pass