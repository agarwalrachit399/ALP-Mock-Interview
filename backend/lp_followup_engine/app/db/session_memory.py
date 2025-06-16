from collections import defaultdict
import time
import threading
from typing import Optional

class SessionMemory:
    def __init__(self, principle: str):
        self.principle = principle
        self.history = []
        self.created_at = time.time()
        self.last_accessed = time.time()

    def add_main_question(self, question: str, user_response: str):
        self.history.append({"role": "interviewer", "type": "main", "content": question})
        self.history.append({"role": "candidate", "content": user_response})
        self.last_accessed = time.time()

    def add_followup_turn(self, bot_question: str, user_response: str):
        self.history.append({"role": "interviewer", "type": "followup", "content": bot_question})
        self.history.append({"role": "candidate", "content": user_response})
        self.last_accessed = time.time()

    def get_history(self):
        self.last_accessed = time.time()
        return self.history

    def get_memory_usage(self) -> dict:
        """Get memory usage statistics for this session"""
        return {
            "principle": self.principle,
            "history_length": len(self.history),
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "age_seconds": time.time() - self.created_at
        }

class SessionMemoryManager:
    def __init__(self, session_timeout_seconds: int = 7200):  # 1 hour default timeout
        self.sessions = defaultdict(dict)
        self.session_timeout = session_timeout_seconds
        self._lock = threading.Lock()  # Thread safety for cleanup operations
        
    def has_session(self, session_id: str, principle: str):
        with self._lock:
            return principle in self.sessions[session_id]

    def start_lp(self, session_id: str, principle: str, question: str, user_input: str):
        with self._lock:
            if principle not in self.sessions[session_id]:
                self.sessions[session_id][principle] = SessionMemory(principle)
            self.sessions[session_id][principle].add_main_question(question, user_input)

    def add_followup(self, session_id: str, principle: str, bot_question: str, user_input: str):
        with self._lock:
            if principle in self.sessions[session_id]:
                self.sessions[session_id][principle].add_followup_turn(bot_question, user_input)

    def get_history(self, session_id: str, principle: str):
        with self._lock:
            if principle in self.sessions[session_id]:
                return self.sessions[session_id][principle].get_history()
            return []

    def cleanup_session(self, session_id: str) -> bool:
        """Clean up a specific session"""
        with self._lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                print(f"🧹 [MEMORY] Cleaned up session: {session_id}")
                return True
            return False

    def cleanup_session_principle(self, session_id: str, principle: str) -> bool:
        """Clean up a specific principle within a session"""
        with self._lock:
            if session_id in self.sessions and principle in self.sessions[session_id]:
                del self.sessions[session_id][principle]
                # If no principles left, remove the session entirely
                if not self.sessions[session_id]:
                    del self.sessions[session_id]
                print(f"🧹 [MEMORY] Cleaned up {principle} from session: {session_id}")
                return True
            return False

    def cleanup_expired_sessions(self) -> int:
        """Clean up sessions that have exceeded the timeout"""
        current_time = time.time()
        expired_sessions = []
        
        with self._lock:
            for session_id, principles in self.sessions.items():
                # Check if any principle in the session has expired
                session_expired = False
                for principle_data in principles.values():
                    age = current_time - principle_data.last_accessed
                    if age > self.session_timeout:
                        session_expired = True
                        break
                
                if session_expired:
                    expired_sessions.append(session_id)
            
            # Remove expired sessions
            for session_id in expired_sessions:
                del self.sessions[session_id]
                print(f"🧹 [MEMORY] Expired session cleaned: {session_id}")
        
        if expired_sessions:
            print(f"🧹 [MEMORY] Cleaned up {len(expired_sessions)} expired sessions")
        
        return len(expired_sessions)

    def get_memory_stats(self) -> dict:
        """Get comprehensive memory usage statistics"""
        with self._lock:
            total_sessions = len(self.sessions)
            total_principles = sum(len(principles) for principles in self.sessions.values())
            total_history_entries = 0
            oldest_session = None
            newest_session = None
            
            current_time = time.time()
            
            for session_id, principles in self.sessions.items():
                for principle_data in principles.values():
                    total_history_entries += len(principle_data.history)
                    
                    # Track oldest and newest sessions
                    if oldest_session is None or principle_data.created_at < oldest_session:
                        oldest_session = principle_data.created_at
                    if newest_session is None or principle_data.created_at > newest_session:
                        newest_session = principle_data.created_at
            
            return {
                "total_sessions": total_sessions,
                "total_principles": total_principles,
                "total_history_entries": total_history_entries,
                "memory_usage_estimate_kb": total_history_entries * 0.5,  # Rough estimate
                "oldest_session_age_seconds": current_time - oldest_session if oldest_session else 0,
                "newest_session_age_seconds": current_time - newest_session if newest_session else 0,
                "session_timeout_seconds": self.session_timeout
            }

    def get_session_details(self, session_id: str) -> Optional[dict]:
        """Get detailed information about a specific session"""
        with self._lock:
            if session_id not in self.sessions:
                return None
            
            principles_data = {}
            for principle, principle_data in self.sessions[session_id].items():
                principles_data[principle] = principle_data.get_memory_usage()
            
            return {
                "session_id": session_id,
                "principles": principles_data,
                "total_principles": len(principles_data)
            }

    def force_cleanup_all(self) -> int:
        """Force cleanup of all sessions (for emergency use)"""
        with self._lock:
            session_count = len(self.sessions)
            self.sessions.clear()
            print(f"🧹 [MEMORY] Force cleaned all {session_count} sessions")
            return session_count