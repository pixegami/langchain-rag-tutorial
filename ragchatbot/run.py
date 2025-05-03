import uvicorn
from config.config import APP_HOST, APP_PORT, APP_RELOAD
import logging
import os

from config.logging_config import CustomFormatter

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
handler.setFormatter(CustomFormatter())

logger.addHandler(handler)

if __name__ == "__main__":
    if not os.path.exists("chroma"):
        logging.warning("'chroma' directory not found!")
        logging.critical("Please run 'python knowledge_base/create_database.py' first to create your knowledge base.")
        choice = input("Do you want to continue anyway? (y/n): ")
        if choice.lower() != 'y':
            raise RuntimeError
    logging.info("Starting server...")
    uvicorn.run(
        "src.main:app",
        host=APP_HOST,
        port=APP_PORT,
        reload=APP_RELOAD)
    logging.info("Server started")
