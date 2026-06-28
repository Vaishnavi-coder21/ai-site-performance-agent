import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration settings
class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    INPUT_DIR = "input"
    OUTPUT_DIR = "output"
    REPORTS_DIR = "reports"
    LOGS_DIR = "logs"

# Ensure directories exist
for directory in [Config.INPUT_DIR, Config.OUTPUT_DIR, Config.REPORTS_DIR, Config.LOGS_DIR]:
    os.makedirs(directory, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(Config.LOGS_DIR, "app.log")),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info("Application configured and logging initialized.")
