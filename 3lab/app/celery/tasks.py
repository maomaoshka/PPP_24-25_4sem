# time нужно для иммитации длительности процесса
# json нужен, чтобы обрабатывать запросы 
import time, json
# Параметры сервера Celery
from app.celery.celery_app import celery_app
# Параметры сервера HTTP и Redis
from app.core.config import Settings
# Чтобы преобразовать полученную картинку в array 
import numpy as np
# Работа с изображением
import cv2
# Для получения изображения по URL
from urllib.request import urlopen
# Для экспорта numpy в img
from PIL import Image
# Для уведомдений от Celery
from redis import Redis

# В name явно объявляю путь и имя "тяжелого" процесса
@celery_app.task(bind=True, name="app.celery.tasks.long_running_parse")
def long_running_parse(self): # url: str
    # Открываю соединенеие с каналом Redis
    r = Redis(host=Settings.REDIS_HOST, port=Settings.REDIS_PORT, db=0)
    # Пушим уведомление
    result = {"task_id": self.request.id, "status": "in progress"}
    r.publish("notifications", json.dumps(result))
    # пример “тяжёлой” операции
    time.sleep(5)
    # Пушим уведомление
    result = {"task_id": self.request.id, "status": "done"}
    r.publish("notifications", json.dumps(result))
    return result

# Бинаризация изображения
@celery_app.task(bind=True, name="app.celery.tasks.run_bin")
def binarization(self, name: str, url: str, readFlag=cv2.IMREAD_COLOR):
    # Открываю соединенеие с каналом Redis
    r = Redis(host=Settings.REDIS_HOST, port=Settings.REDIS_PORT, db=0)
    # Пушим уведомление о начале работы 
    result = {
        "status": "STARTED",
        "task_id": self.request.id,
    }
    r.publish("notifications", json.dumps(result))
    # -------------------------------- Бинаризация изображения --------------------------------
    # Получаем изображение по url 
    resp = urlopen(url)
    img = np.asarray(bytearray(resp.read()), dtype="uint8")
    img = cv2.imdecode(img, readFlag)
    # Бинаризуем изображение
    height, width, _= img.shape
    gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

    # Пушим уведомление о прогрессе работы
    result = {
        "status": "PROGRESS",
        "task_id": self.request.id,
        "progress": 50
    }
    r.publish("notifications", json.dumps(result))

    thresh = cv2.threshold(gray,0,255,cv2.THRESH_OTSU)[1]
    # Экспортирую изображение
    im = Image.fromarray(thresh)
    im.save(f"{name}.jpeg")
    # -------------------------------- Бинаризация изображения --------------------------------
    # Пушим уведомление о конце работы
    result = {
        "status": "COMPLETED",
        "task_id": self.request.id,
        "binarized_image": str(thresh) # f"{name}.png"
    }
    r.publish("notifications", json.dumps(result))