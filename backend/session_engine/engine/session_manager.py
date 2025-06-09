import time
import uuid

class SessionManager:
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.start_time = None

    def start_session(self):
        self.start_time = time.time()

    def time_remaining(self, limit):
        return limit - (time.time() - self.start_time)

    def get_session_id(self):
        return self.session_id