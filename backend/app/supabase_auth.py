import os
import jwt
from fastapi import Depends, HTTPException, Request, status
from app.database import get_db
from app.models import User
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")  # Set this in your .env

def get_current_user(request: Request, db=Depends(get_db)):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        logger.error("Missing or invalid auth header")
        raise HTTPException(status_code=401, detail="Missing or invalid auth header")
    
    token = auth_header.split(" ")[1]
    try:
        logger.info(f"Attempting to decode token with secret: {SUPABASE_JWT_SECRET[:5]}...")
        # Decode without verification first to get the claims
        unverified = jwt.decode(token, options={"verify_signature": False})
        logger.info(f"Token claims: {unverified}")
        
        # Now verify with proper options
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={
                "verify_aud": False,  # Supabase tokens don't have an audience
                "verify_iat": False,  # Skip iat validation
                "verify_exp": True,   # Still verify expiration
            }
        )
        user_id = payload["sub"]
        logger.info(f"Token decoded successfully. User ID: {user_id}")
        
        user = db.query(User).filter_by(supabase_user_id=user_id).first()
        if not user:
            logger.error(f"User not found in database for supabase_user_id: {user_id}")
            raise HTTPException(status_code=401, detail="User not found in database")
        
        logger.info(f"User found: {user.email} with role {user.role.value}")
        return user
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid token: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Authentication error: {str(e)}")

def require_role(role: str):
    def role_checker(user=Depends(get_current_user)):
        if not user or user.role.value != role:
            logger.error(f"User {user.email if user else 'None'} does not have required role: {role}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have required role: {role}"
            )
        return user
    return role_checker
