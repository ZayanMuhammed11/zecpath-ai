import os
from dotenv import load_dotenv

load_dotenv()

# LLM Configuration
GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LLM_MODEL      = "llama-3.3-70b-versatile"  # change here to upgrade model

# Database
DATABASE_URL = os.getenv("DATABASE_URL")

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Scoring defaults
DEFAULT_SHORTLIST_THRESHOLD = 70
DEFAULT_WEIGHTS = {
    "skills":     40,
    "experience": 30,
    "education":  20,
    "location":   10
}

# App
APP_ENV  = os.getenv("APP_ENV", "development")
APP_PORT = int(os.getenv("APP_PORT", 8001))