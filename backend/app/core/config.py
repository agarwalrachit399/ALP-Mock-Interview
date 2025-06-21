import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class Settings:
    def __init__(self):
        """Initialize settings with validation"""
        self._validate_required_env_vars()
        self._load_validated_settings()
    
    def _validate_required_env_vars(self):
        """Validate all required environment variables"""
        required_vars = {
            "JWT_SECRET_KEY": "JWT secret for authentication",
            "MONGO_URI": "MongoDB connection string", 
            "GEMINI_API_KEY": "Gemini AI API key for followups/moderation",
            "SPEECHMATICS_API_KEY": "Speechmatics API key for speech-to-text",
            "RIME_API_KEY": "Rime API key for text-to-speech"
        }
        
        missing_vars = []
        invalid_vars = []
        
        for var_name, description in required_vars.items():
            value = os.getenv(var_name)
            
            if not value:
                missing_vars.append(f"  - {var_name}: {description}")
            elif not self._validate_var_format(var_name, value):
                invalid_vars.append(f"  - {var_name}: Invalid format")
        
        if missing_vars or invalid_vars:
            error_msg = "🚨 CONFIGURATION ERROR - Application cannot start:\n\n"
            
            if missing_vars:
                error_msg += "❌ Missing required environment variables:\n"
                error_msg += "\n".join(missing_vars) + "\n\n"
            
            if invalid_vars:
                error_msg += "❌ Invalid environment variables:\n" 
                error_msg += "\n".join(invalid_vars) + "\n\n"
            
            error_msg += "💡 Please check your .env file and ensure all required variables are set."
            
            logger.critical(error_msg)
            raise ValueError(error_msg)
        
        logger.info("✅ All required environment variables validated")
    
    def _validate_var_format(self, var_name: str, value: str) -> bool:
        """Validate specific environment variable formats"""
        if var_name == "JWT_SECRET_KEY":
            return len(value) >= 32  # Minimum 32 characters for security
        
        elif var_name == "MONGO_URI":
            return value.startswith(("mongodb://", "mongodb+srv://"))
        
        elif var_name == "GEMINI_API_KEY":
            return value.startswith("AIza") and len(value) > 20
        
        elif var_name == "SPEECHMATICS_API_KEY":
            return len(value) > 10  # Basic length check
        
        elif var_name == "RIME_API_KEY":
            return len(value) > 10  # Basic length check
        
        return True  # Default to valid if no specific validation
    
    def _load_validated_settings(self):
        """Load settings after validation"""
        # Database
        self.MONGO_URI: str = os.getenv("MONGO_URI")
        
        # API Keys
        self.GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
        self.SPEECHMATICS_API_KEY: str = os.getenv("SPEECHMATICS_API_KEY")
        self.RIME_API_KEY: str = os.getenv("RIME_API_KEY")
        
        # JWT Configuration
        self.JWT_SECRET: str = os.getenv("JWT_SECRET_KEY")
        self.JWT_ALGORITHM: str = "HS256"
        self.JWT_EXPIRY_MINUTES: int = 60
        
        # Session Configuration
        self.SESSION_DURATION_LIMIT: int = 30 * 60  # in seconds
        self.MIN_LP_QUESTIONS: int = 1
        self.FOLLOW_UP_COUNT: int = 2

settings = Settings()