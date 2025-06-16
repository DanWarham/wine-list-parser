import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from .env file
load_dotenv()

# OpenAI configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')  # Default to gpt-3.5-turbo for cost efficiency

# LWIN configuration
LWIN_XLSX_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'specs', 'LWINdatabase.xlsx')

# Parsing configuration
MIN_CONFIDENCE_THRESHOLD = 0.75
BATCH_SIZE = 5  # Number of entries to process in parallel
CACHE_SIZE = 1000  # Number of entries to cache for AI parsing 

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # Use service role for backend

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) 