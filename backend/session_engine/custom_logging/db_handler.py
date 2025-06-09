from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

class MongoLogger:
    def __init__(self, db_name="alp_interviews", collection_name="sessions"):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]

    def log_lp_block(self, session_id, principle, main_question, main_answer, followups):
        doc = {
            "session_id": session_id,
            "principle": principle,
            "main_question": {
                "question": main_question,
                "answer": main_answer
            },
            "followups": followups,
            "timestamp": datetime.now().isoformat()
        }
        self.collection.insert_one(doc)

    def close(self):
        self.client.close()