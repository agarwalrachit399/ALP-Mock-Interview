from pymongo import MongoClient
from app.core.config import settings

client = MongoClient(settings.MONGO_URI)
db = client["alp_interviews"]
collection = db["sessions"]

def get_all_conversations_by_session(session_id: str) -> list:
    return list(collection.find({"session_id": session_id}))
