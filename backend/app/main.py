import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('backend_debug.log')
    ]
)

# Enable DEBUG logging for all loggers
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger('uvicorn').setLevel(logging.DEBUG)
logging.getLogger('fastapi').setLevel(logging.DEBUG)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api_v2 import api_router as api_router_v2

from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger = logging.getLogger(__name__)
    logger.debug(f"Request: {request.method} {request.url}")
    logger.debug(f"Headers: {dict(request.headers)}")
    
    response = await call_next(request)
    
    logger.debug(f"Response: {response.status_code}")
    return response

# Include API routers
app.include_router(api_router_v2, prefix="/api/v2")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger = logging.getLogger(__name__)
    logger.error(f"[GLOBAL EXCEPTION] {exc}")
    return JSONResponse(status_code=500, content={"detail": str(exc)}) 