from pymongo import MongoClient
from datetime import datetime
from bson.objectid import ObjectId
from app.core.config import settings

import logging
import time
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger(__name__)

def create_database_connection():
    """Create MongoDB connection with error handling and retries"""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            # Configure connection with proper settings
            client = MongoClient(
                settings.MONGO_URI,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                connectTimeoutMS=10000,         # 10 second connection timeout
                socketTimeoutMS=20000,          # 20 second socket timeout
                maxPoolSize=10,                 # Connection pool size
                retryWrites=True
            )
            
            # Test the connection
            client.admin.command('ping')
            logger.info("✅ MongoDB connection established successfully")
            return client
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"❌ MongoDB connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.critical("💥 All MongoDB connection attempts failed - using fallback mode")
                return None
        except Exception as e:
            logger.critical(f"💥 Unexpected database error: {e}")
            return None

# Initialize connection
client = create_database_connection()
db = client["alp_interviews"] if client is not None else None

# Shared collections with safe access
users_collection = db["users"] if client is not None else None
sessions_collection = db["sessions"] if client is not None else None

def check_database_health():
    """Check if database connection is healthy"""
    global client, db, users_collection, sessions_collection
    
    try:
        if client is None:  # Fix: was 'if not client'
            return False
        client.admin.command('ping')
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        # Attempt reconnection
        logger.info("Attempting database reconnection...")
        client = create_database_connection()
        if client is not None:  # Fix: was 'if client'
            db = client["alp_interviews"]
            users_collection = db["users"]
            sessions_collection = db["sessions"]
            return True
        return False

class UserDB:
    """User database operations"""
    
    @staticmethod
    def get_user_by_email(email: str):
        if not check_database_health():
            logger.error("Database unavailable for get_user_by_email")
            return None
        
        try:
            return users_collection.find_one({"email": email})
        except Exception as e:
            logger.error(f"Database error in get_user_by_email: {e}")
            return None

    @staticmethod
    def create_user(name: str, email: str, hashed_password: str):
        if not check_database_health():
            raise Exception("Database unavailable")
        
        try:
            user = {
                "name": name,
                "email": email,
                "hashed_password": hashed_password,
                "created_at": datetime.now()
            }
            result = users_collection.insert_one(user)
            user["_id"] = result.inserted_id
            return user
        except Exception as e:
            logger.error(f"Database error in create_user: {e}")
            raise Exception("Failed to create user")

    @staticmethod
    def get_user_by_id(user_id: str):
        if not check_database_health():
            logger.error("Database unavailable for get_user_by_id")
            return None
        
        try:
            return users_collection.find_one({"_id": ObjectId(user_id)})
        except Exception as e:
            logger.error(f"Database error in get_user_by_id: {e}")
            return None