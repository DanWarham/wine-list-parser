from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import api_router, auth_router

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(api_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
