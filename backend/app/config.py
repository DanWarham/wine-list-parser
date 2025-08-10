import os
import logging
import traceback

# Configure logging with reduced verbosity
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors by default
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Reduce verbosity from external libraries
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('openai').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('requests').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

try:
    logger.info("[config] Starting configuration loading...")
    
    from dotenv import load_dotenv
    logger.info("[config] dotenv import successful")
    
    from supabase import create_client, Client
    logger.info("[config] supabase import successful")

    # Load environment variables from .env file
    load_dotenv()
    logger.info("[config] Environment variables loaded")

    # OpenAI configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')  # Default to gpt-3.5-turbo for cost efficiency
    logger.info(f"[config] OpenAI config loaded - Model: {OPENAI_MODEL}")

    # Parsing configuration
    MIN_CONFIDENCE_THRESHOLD = 0.75
    logger.info("[config] Parsing configuration loaded")

    # AI Hybrid Rule Generation Configuration
    AI_RULE_GENERATION_ENABLED = os.getenv('AI_RULE_GENERATION_ENABLED', 'true').lower() == 'true'
    SAMPLE_SIZE_RATIO = float(os.getenv('SAMPLE_SIZE_RATIO', '0.02'))  # 2% of entries
    MIN_SAMPLE_SIZE = int(os.getenv('MIN_SAMPLE_SIZE', '5'))
    MAX_SAMPLE_SIZE = int(os.getenv('MAX_SAMPLE_SIZE', '10'))  # Reduced from 20 to 10
    
    # AI Fallback Configuration - LOWERED THRESHOLDS
    MIN_CONFIDENCE_THRESHOLD_HYBRID = float(os.getenv('MIN_CONFIDENCE_THRESHOLD_HYBRID', '0.4'))  # Lowered from 0.7 to 0.4
    MIN_FIELDS_EXTRACTED_THRESHOLD = int(os.getenv('MIN_FIELDS_EXTRACTED_THRESHOLD', '3'))  # New: minimum fields required
    AI_FALLBACK_MAX_ENTRIES = int(os.getenv('AI_FALLBACK_MAX_ENTRIES', '50'))  # New: limit AI usage for large files
    AI_FALLBACK_SAMPLE_RATIO = float(os.getenv('AI_FALLBACK_SAMPLE_RATIO', '0.3'))  # New: use AI on 30% of problematic entries
    
    FALLBACK_AI_MODEL = os.getenv('FALLBACK_AI_MODEL', 'gpt-3.5-turbo')
    RULE_GENERATION_MODEL = os.getenv('RULE_GENERATION_MODEL', 'gpt-3.5-turbo')  # Changed from gpt-4 to gpt-3.5-turbo
    logger.info(f"[config] AI configuration loaded - AI_RULE_GENERATION_ENABLED: {AI_RULE_GENERATION_ENABLED}")

    # Validation configuration
    MIN_VALIDATION_ENTRIES = int(os.getenv('MIN_VALIDATION_ENTRIES', '5'))
    VALIDATION_SPLIT_RATIO = float(os.getenv('VALIDATION_SPLIT_RATIO', '0.2'))  # 20% for validation
    logger.info("[config] Validation configuration loaded")

    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # Use service role for backend
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("[config] Missing Supabase configuration - SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set")
        raise ValueError("Missing Supabase configuration")
    
    logger.info("[config] Supabase configuration loaded")

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("[config] Supabase client created successfully")
    
    logger.info("[config] Configuration loading completed successfully")

except ImportError as e:
    logger.error(f"[config] Import error: {e}")
    logger.error(f"[config] Traceback: {traceback.format_exc()}")
    raise
except Exception as e:
    logger.error(f"[config] Error during configuration: {e}")
    logger.error(traceback.format_exc())
    raise 