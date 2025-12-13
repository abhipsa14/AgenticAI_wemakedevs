"""
Application configuration and settings.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/study_assistant.db")

# ChromaDB
CHROMA_PERSIST_DIR = str(BASE_DIR / "chroma_db")

# Application
APP_NAME = "Study Assistant"
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# LLM Settings
DEFAULT_LLM_MODEL = "gpt-4o-mini"
EMBEDDING_MODEL = "text-embedding-3-small"

# File upload settings
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB

# Study session settings
DEFAULT_SESSION_DURATION = 45  # minutes
MAX_CATCHUP_SESSIONS_PER_DAY = 2
