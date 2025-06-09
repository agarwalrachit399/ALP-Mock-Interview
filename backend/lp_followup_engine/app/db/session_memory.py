from collections import defaultdict

class SessionMemory:
    def __init__(self, principle: str):
        self.principle = principle
        self.history = []

    def add_main_question(self, question: str, user_response: str):
        self.history.append({"role": "interviewer", "type": "main", "content": question})
        self.history.append({"role": "candidate", "content": user_response})

    def add_followup_turn(self, bot_question: str, user_response: str):
        self.history.append({"role": "interviewer", "type": "followup", "content": bot_question})
        self.history.append({"role": "candidate", "content": user_response})

    def get_history(self):
        return self.history

class SessionMemoryManager:
    def __init__(self):
        self.sessions = defaultdict(dict)

    def has_session(self, session_id: str, principle: str):
        return principle in self.sessions[session_id]

    def start_lp(self, session_id: str, principle: str, question: str, user_input: str):
        if principle not in self.sessions[session_id]:
            self.sessions[session_id][principle] = SessionMemory(principle)
        self.sessions[session_id][principle].add_main_question(question, user_input)

    def add_followup(self, session_id: str, principle: str, bot_question: str, user_input: str):
        self.sessions[session_id][principle].add_followup_turn(bot_question, user_input)

    def get_history(self, session_id: str, principle: str):
        return self.sessions[session_id][principle].get_history()
