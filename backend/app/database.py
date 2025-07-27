import os
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    logger.info("[database] Starting database module initialization...")
    
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker, Session
    logger.info("[database] SQLAlchemy imports successful")
    
    from dotenv import load_dotenv
    logger.info("[database] dotenv import successful")

    load_dotenv()
    logger.info("[database] Environment variables loaded")

    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        logger.error("[database] DATABASE_URL environment variable not set")
        raise ValueError("DATABASE_URL environment variable not set")
    
    logger.info(f"[database] DATABASE_URL configured: {DATABASE_URL[:20]}...")

    engine = create_engine(DATABASE_URL)
    logger.info("[database] SQLAlchemy engine created")
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("[database] Session maker configured")
    
    logger.info("[database] Database module initialization completed successfully")

except ImportError as e:
    logger.error(f"[database] Import error: {e}")
    logger.error(f"[database] Traceback: {traceback.format_exc()}")
    raise
except Exception as e:
    logger.error(f"[database] Database initialization error: {type(e).__name__}: {e}")
    logger.error(f"[database] Traceback: {traceback.format_exc()}")
    raise

def get_db():
    try:
        db: Session = SessionLocal()
        yield db
    except Exception as e:
        logger.error(f"[database] Error creating database session: {type(e).__name__}: {e}")
        logger.error(f"[database] Traceback: {traceback.format_exc()}")
        raise
    finally:
        try:
            db.close()
        except Exception as e:
            logger.error(f"[database] Error closing database session: {type(e).__name__}: {e}")
