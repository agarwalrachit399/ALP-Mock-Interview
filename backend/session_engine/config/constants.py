SESSION_DURATION_LIMIT = 60 * 60  # in seconds
MIN_LP_QUESTIONS = 3
FOLLOW_UP_COUNT = 4
LLM_ENDPOINT = "http://localhost:8000/generate-followup"
SHOULD_GENERATE_ENDPOINT = "http://localhost:8000/should-followup"
MODERATION_ENDPOINT = "http://localhost:8100/moderate"
QUESTION_FILE = "/Users/rachitagarwal/Desktop/ALP Mock Interviewes/backend/session_engine/questions.json"