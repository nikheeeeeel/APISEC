import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration settings."""
    
    # JWT Configuration
    JWT_SECRET_KEY: str = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
    JWT_ALGORITHM: str = 'HS256'
    JWT_EXPIRATION_HOURS: int = 24
    
    # OAuth Configuration
    GOOGLE_CLIENT_ID: Optional[str] = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET: Optional[str] = os.getenv('GOOGLE_CLIENT_SECRET')
    GITHUB_CLIENT_ID: Optional[str] = os.getenv('GITHUB_CLIENT_ID')
    GITHUB_CLIENT_SECRET: Optional[str] = os.getenv('GITHUB_CLIENT_SECRET')
    
    # OAuth Redirect URLs
    GOOGLE_REDIRECT_URI: str = 'http://localhost:8001/auth/oauth/callback/google'
    GITHUB_REDIRECT_URI: str = 'http://localhost:8001/auth/oauth/callback/github'
    
    # OAuth Provider URLs
    GOOGLE_AUTH_URL: str = 'https://accounts.google.com/o/oauth2/v2/auth'
    GOOGLE_TOKEN_URL: str = 'https://oauth2.googleapis.com/token'
    GOOGLE_USER_INFO_URL: str = 'https://www.googleapis.com/oauth2/v2/userinfo'
    
    GITHUB_AUTH_URL: str = 'https://github.com/login/oauth/authorize'
    GITHUB_TOKEN_URL: str = 'https://github.com/login/oauth/access_token'
    GITHUB_USER_INFO_URL: str = 'https://api.github.com/user'
    
    # Frontend URL
    FRONTEND_URL: str = 'http://localhost:5173'
    
    @classmethod
    def is_oauth_configured(cls, provider: str) -> bool:
        """Check if OAuth provider is properly configured."""
        if provider == 'google':
            return bool(cls.GOOGLE_CLIENT_ID and cls.GOOGLE_CLIENT_SECRET)
        elif provider == 'github':
            return bool(cls.GITHUB_CLIENT_ID and cls.GITHUB_CLIENT_SECRET)
        return False

config = Config()
