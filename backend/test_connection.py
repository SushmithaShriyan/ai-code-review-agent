import certifi
from pymongo import MongoClient

uri = "mongodb+srv://admin_2:SUSHMITHA2004@cluster1.pzodbef.mongodb.net/?appName=Cluster1"

client = MongoClient(uri, tlsCAFile=certifi.where())
try:
    client.admin.command("ping")
    print("SUCCESS: Connected to MongoDB!")
except Exception as e:
    print("FAILED:", e)