import httpx
from fastapi import HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict, Any
from config import config
import logging

logger = logging.getLogger(__name__)
from user_models import OAuthUserInfo

class OAuthService:
    """OAuth service for handling external authentication providers."""
    
    @staticmethod
    async def get_google_user_info(code: str) -> OAuthUserInfo:
        """Exchange Google OAuth code for user information."""
        async with httpx.AsyncClient() as client:
            # Exchange code for access token
            token_data = {
                'client_id': config.GOOGLE_CLIENT_ID,
                'client_secret': config.GOOGLE_CLIENT_SECRET,
                'code': code,
                'redirect_uri': config.GOOGLE_REDIRECT_URI,
                'grant_type': 'authorization_code'
            }
            
            token_response = await client.post(config.GOOGLE_TOKEN_URL, data=token_data)
            if token_response.status_code != 200:
                logger.error(f"Google OAuth token exchange failed: {token_response.status_code}")
                logger.error(f"Response: {token_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to exchange Google OAuth code"
                )
            
            token_json = token_response.json()
            access_token = token_json.get('access_token')
            
            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No access token received from Google"
                )
            
            # Get user information
            headers = {'Authorization': f'Bearer {access_token}'}
            user_response = await client.get(config.GOOGLE_USER_INFO_URL, headers=headers)
            
            if user_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get Google user information"
                )
            
            user_data = user_response.json()
            
            return OAuthUserInfo(
                id=user_data.get('id'),
                email=user_data.get('email'),
                name=user_data.get('name'),
                username=user_data.get('email').split('@')[0] if user_data.get('email') else None,
                avatar_url=user_data.get('picture'),
                provider='google'
            )
    
    @staticmethod
    async def get_github_user_info(code: str) -> OAuthUserInfo:
        """Exchange GitHub OAuth code for user information."""
        async with httpx.AsyncClient() as client:
            # Exchange code for access token
            token_data = {
                'client_id': config.GITHUB_CLIENT_ID,
                'client_secret': config.GITHUB_CLIENT_SECRET,
                'code': code,
                'redirect_uri': config.GITHUB_REDIRECT_URI
            }
            
            token_response = await client.post(config.GITHUB_TOKEN_URL, data=token_data)
            if token_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to exchange GitHub OAuth code"
                )
            
            token_json = token_response.json()
            access_token = token_json.get('access_token')
            
            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No access token received from GitHub"
                )
            
            # Get user information
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            user_response = await client.get(config.GITHUB_USER_INFO_URL, headers=headers)
            
            if user_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get GitHub user information"
                )
            
            user_data = user_response.json()
            
            # Get user email (GitHub requires separate API call for email)
            email_response = await client.get('https://api.github.com/user/emails', headers=headers)
            if email_response.status_code == 200:
                emails = email_response.json()
                primary_email = next((e['email'] for e in emails if e['primary']), None)
            else:
                primary_email = None
            
            return OAuthUserInfo(
                id=str(user_data.get('id')),
                email=primary_email or f"{user_data.get('login')}@users.noreply.github.com",
                name=user_data.get('name'),
                username=user_data.get('login'),
                avatar_url=user_data.get('avatar_url'),
                provider='github'
            )

oauth_service = OAuthService()
