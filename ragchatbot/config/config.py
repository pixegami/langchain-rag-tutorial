import os
from dotenv import load_dotenv

# Load the .env file from the root directory
load_dotenv()

APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", 8000))
APP_RELOAD = os.getenv("APP_RELOAD", "True")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TOKEN_RETRIEVAL_SECRET = os.getenv("TOKEN_RETRIEVAL_SECRET")

RATE_LIMIT = os.getenv("RATE_LIMIT", 60)
TIME_WINDOW = os.getenv("TIME_WINDOW", 60)
TEMP_BAN_DURATION = 300
THROTTLE_TIME = 2
MAX_THREADS = 10

# Sanity checks
if not APP_HOST:
    raise RuntimeError("APP_HOST not found in environment variables.")
if not APP_PORT:
    raise RuntimeError("APP_PORT not found in environment variables.")
if not APP_RELOAD:
    raise RuntimeError("APP_RELOAD not found in environment variables.")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not found in environment variables.")

if not RATE_LIMIT:
    raise RuntimeError("RATE_LIMIT not found in environment variables.")
if not TIME_WINDOW:
    raise RuntimeError("TIME_WINDOW not found in environment variables.")
if not TOKEN_RETRIEVAL_SECRET:
    raise RuntimeError("TOKEN_RETRIEVAL_SECRET not found in environment variables.")
