import requests
import logging
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config.constants import MODERATION_ENDPOINT

class ModerationService:
    def moderate(self, question, user_input):
        try:
            payload = {"question": question, "user_input": user_input}
            response = requests.post(MODERATION_ENDPOINT, json=payload)
            response.raise_for_status()
            return response.json().get("status", "safe")
        except requests.exceptions.RequestException as e:
            logging.error(f"Moderation error: {e}")
            return "safe"