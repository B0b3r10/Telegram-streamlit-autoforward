import logging
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))
from src.db import engine, Base

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def main():
    logger.info("Connecting db...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("FINISHED CREATE TABLES...")
    except Exception as e:
        logger.critical(f"ERROR: {e}")

if __name__ == "__main__":
    main()