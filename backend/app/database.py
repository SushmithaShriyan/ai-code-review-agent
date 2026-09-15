"""
MongoDB connection layer.

We use Motor (the async MongoDB driver) because FastAPI is async end to end -
using a blocking driver like pymongo directly in request handlers would
block the event loop under load. This is a good talking point for interviews
about why you picked the tools you picked.
"""

import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

client = AsyncIOMotorClient(settings.mongodb_uri, tlsCAFile=certifi.where())
db = client[settings.mongodb_db_name]

reviews_collection = db["reviews"]
