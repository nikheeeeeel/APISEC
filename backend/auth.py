from jose import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from fastapi import HTTPException, status
from config import config
import secrets

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    """Authentication service for handling JWT tokens and password hashing."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def create_access_token(data: Dict[str, Any]) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(hours=config.JWT_EXPIRATION_HOURS)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    @staticmethod
    def generate_oauth_state() -> str:
        """Generate a secure state parameter for OAuth flow."""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def create_oauth_auth_url(provider: str, state: str) -> str:
        """Create OAuth authorization URL."""
        if provider == 'google':
            params = {
                'client_id': config.GOOGLE_CLIENT_ID,
                'redirect_uri': config.GOOGLE_REDIRECT_URI,
                'scope': 'openid email profile',
                'response_type': 'code',
                'state': state,
                'access_type': 'offline'
            }
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            return f"{config.GOOGLE_AUTH_URL}?{query_string}"
        
        elif provider == 'github':
            params = {
                'client_id': config.GITHUB_CLIENT_ID,
                'redirect_uri': config.GITHUB_REDIRECT_URI,
                'scope': 'user:email',
                'state': state
            }
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            return f"{config.GITHUB_AUTH_URL}?{query_string}"
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported OAuth provider: {provider}"
            )

auth_service = AuthService()
