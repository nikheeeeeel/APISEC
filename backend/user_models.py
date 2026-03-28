from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    """User creation model."""
    username: str
    email: EmailStr
    password: Optional[str] = None
    oauth_provider: Optional[str] = None
    oauth_id: Optional[str] = None

class UserLogin(BaseModel):
    """User login model."""
    username: str
    password: str

class UserResponse(BaseModel):
    """User response model."""
    id: int
    username: str
    email: str
    oauth_provider: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserLoginResponse(BaseModel):
    """User login response model."""
    access_token: str
    token_type: str
    user: UserResponse

class OAuthUserInfo(BaseModel):
    """OAuth user information model."""
    id: str
    email: str
    name: Optional[str] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    provider: str
