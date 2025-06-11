import logging
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from custom_logging.db_handler import MongoLogger

class InteractionLogger:
    def __init__(self,user_id):
        self.user_id = user_id
        self.db_logger = MongoLogger()

    def log_lp_block(self, session_id, lp, main_question, main_answer, followups):
        self.db_logger.log_lp_block(session_id,self.user_id, lp, main_question, main_answer, followups)

    def log_interaction(self, speaker, action, content):
        logging.info(f"{speaker.upper()} {action}: {content}")