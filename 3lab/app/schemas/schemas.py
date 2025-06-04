from pydantic import BaseModel

class User(BaseModel):
    email: str
    password: str
class Image(BaseModel):
    image_name: str
    image_url: str