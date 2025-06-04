import time, json
from app.celery.celery_app import celery_app
from app.core.config import Settings
import numpy as np
import cv2
from urllib.request import urlopen
from PIL import Image
from redis import Redis

@celery_app.task(bind=True, name="app.celery.tasks.run_bin")
def binarization(self, name: str, url: str, readFlag=cv2.IMREAD_COLOR):
    r = Redis(host=Settings.REDIS_HOST, port=Settings.REDIS_PORT, db=0)
    result = {
        "status": "STARTED",
        "task_id": self.request.id,
    }
    r.publish("notifications", json.dumps(result))
    # бинаризация
    resp = urlopen(url)
    img = np.asarray(bytearray(resp.read()), dtype="uint8")
    img = cv2.imdecode(img, readFlag)
    height, width, _= img.shape
    gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

    result = {"status": "PROGRESS", "task_id": self.request.id, "progress": 50}
    r.publish("notifications", json.dumps(result))

    thresh = cv2.threshold(gray,0,255,cv2.THRESH_OTSU)[1]
    im = Image.fromarray(thresh)
    im.save(f"{name}.jpeg")
    result = {"status": "COMPLETED", "task_id": self.request.id, "binarized_image": str(thresh)}
    r.publish("notifications", json.dumps(result))