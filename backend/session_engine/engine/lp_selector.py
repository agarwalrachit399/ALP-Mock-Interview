import random

class LPSelector:
    def __init__(self, lp_questions):
        self.lp_questions = lp_questions
        self.asked = set()

    def pick_new_lp(self):
        remaining = list(set(self.lp_questions.keys()) - self.asked)
        if not remaining:
            return None
        lp = random.choice(remaining)
        self.asked.add(lp)
        return lp