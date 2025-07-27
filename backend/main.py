import logging
import sys
import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
# from app.api import api_router
from app.api_v2 import api_router as api_router_v2

# Configure logging immediately
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

logger = logging.getLogger(__name__)

try:
    logger.info("Starting FastAPI application initialization...")
    
    app = FastAPI()
    
    logger.info("FastAPI app created successfully")
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",  # Your frontend dev port
            "http://localhost:3001",  # If Next.js switched to 3001
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )
    
    logger.info("CORS middleware added successfully")
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Global exception handler caught: {type(exc).__name__}: {exc}")
        logger.error(f"Request URL: {request.url}")
        logger.error(f"Request method: {request.method}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"Internal server error: {str(exc)}",
                "type": type(exc).__name__
            }
        )
    
    logger.info("Global exception handler registered")
    
    # app.include_router(api_router, prefix="/api")
    logger.info("Attempting to include API router v2...")
    app.include_router(api_router_v2, prefix="/api/v2")
    logger.info("API router v2 included successfully")
    
    logger.info("FastAPI application initialization completed successfully")
    
except Exception as e:
    logger.error(f"Error during FastAPI initialization: {type(e).__name__}: {e}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    raise
