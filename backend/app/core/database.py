from pymongo import MongoClient
from datetime import datetime
from bson.objectid import ObjectId
from app.core.config import settings

# Shared MongoDB client and database
client = MongoClient(settings.MONGO_URI)
db = client["alp_interviews"]

# Shared collections
users_collection = db["users"]
sessions_collection = db["sessions"]

class UserDB:
    """User database operations"""
    
    @staticmethod
    def get_user_by_email(email: str):
        return users_collection.find_one({"email": email})

    @staticmethod
    def create_user(name: str, email: str, hashed_password: str):
        user = {
            "name": name,
            "email": email,
            "hashed_password": hashed_password,
            "created_at": datetime.now()
        }
        result = users_collection.insert_one(user)
        user["_id"] = result.inserted_id
        return user

    @staticmethod
    def get_user_by_id(user_id: str):
        return users_collection.find_one({"_id": ObjectId(user_id)})