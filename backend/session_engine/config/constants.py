import os
SESSION_DURATION_LIMIT = 30 * 60  # in seconds
MIN_LP_QUESTIONS = 3
FOLLOW_UP_COUNT = 2
LLM_ENDPOINT = "http://localhost:8000/generate-followup"
SHOULD_GENERATE_ENDPOINT = "http://localhost:8000/should-followup"
MODERATION_ENDPOINT = "http://localhost:8100/moderate"
REPORT_ENDPOINT = "http://localhost:8080/get_report"
SESSION_ENGINE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

QUESTION_FILE = os.path.join(SESSION_ENGINE_DIR, "questions.json")
