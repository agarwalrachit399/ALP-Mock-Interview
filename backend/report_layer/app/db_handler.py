from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["alp_interviews"]
collection = db["sessions"]

def get_all_conversations_by_session(session_id: str) -> list:
    return list(collection.find({"session_id": session_id}))
# "3fdc148d-00e5-4d81-a5f6-1a6bf791b456"