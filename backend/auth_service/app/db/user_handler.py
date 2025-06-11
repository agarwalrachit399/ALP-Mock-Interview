from pymongo import MongoClient
from datetime import datetime
import os
from bson.objectid import ObjectId

# Load DB URI from env
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["alp_interviews"]
user_collection = db["users"]

class UserDB:

    @staticmethod
    def get_user_by_email(email: str):
        return user_collection.find_one({"email": email})

    @staticmethod
    def create_user(name: str, email: str, hashed_password: str):
        user = {
            "name": name,
            "email": email,
            "hashed_password": hashed_password,
            "created_at": datetime.now()
        }
        result = user_collection.insert_one(user)
        user["_id"] = result.inserted_id
        return user

    @staticmethod
    def get_user_by_id(user_id: str):
        return user_collection.find_one({"_id": ObjectId(user_id)})
