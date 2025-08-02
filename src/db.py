import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from . import config, models

logger = logging.getLogger(__name__)

DATABASE_URL = (
    f"postgresql+psycopg2://{config.DB_USER}:{config.DB_PASSWORD}@"
    f"{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
)

try:
    engine = create_engine(DATABASE_URL, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = models.Base
    logger.info("sessions SQLAlchemy created")
except Exception as e:
    logger.critical(f"ERROR SQLAlchemy: {e}")
    engine = None
    SessionLocal = None

def get_session():
    if not SessionLocal:
        return None
    return SessionLocal()
