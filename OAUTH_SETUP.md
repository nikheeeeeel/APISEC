# OAuth Setup Guide

This guide will help you configure Google and GitHub OAuth for the APISEC application.

## 🚀 Quick Start

1. **Environment file is ready**: `backend/.env` has been created
2. **Traditional login works**: Use `admin/admin` credentials
3. **OAuth buttons are visible**: Ready to be configured

## 🔧 Google OAuth Setup

### 1. Create Google Cloud Console Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Go to **APIs & Services → Credentials**
4. Click **+ CREATE CREDENTIALS → OAuth 2.0 Client IDs**
5. Select **Web application**
6. Configure:
   - **Name**: APISEC Development
   - **Authorized JavaScript origins**: `http://localhost:5173`
   - **Authorized redirect URIs**: `http://localhost:8001/auth/oauth/callback/google`

### 2. Get Credentials
- Copy **Client ID** and **Client Secret**
- Update `backend/.env`:
```env
GOOGLE_CLIENT_ID=your_actual_google_client_id
GOOGLE_CLIENT_SECRET=your_actual_google_client_secret
```

## 🐙 GitHub OAuth Setup

### 1. Create GitHub OAuth App
1. Go to [GitHub Settings → Developer settings](https://github.com/settings/developers)
2. Click **OAuth Apps → New OAuth App**
3. Configure:
   - **Application name**: APISEC Development
   - **Homepage URL**: `http://localhost:5173`
   - **Authorization callback URL**: `http://localhost:8001/auth/oauth/callback/github`

### 2. Get Credentials
- Copy **Client ID** and **Client Secret**
- Update `backend/.env`:
```env
GITHUB_CLIENT_ID=your_actual_github_client_id
GITHUB_CLIENT_SECRET=your_actual_github_client_secret
```

## 🔄 Restart Backend

After updating `.env`, restart the backend:
```bash
cd backend
source ../.venv/bin/activate
python main.py
```

## ✅ Test OAuth

1. Go to http://localhost:5173/login
2. Click "Google" or "GitHub" buttons
3. You'll be redirected to OAuth provider
4. After authorization, you'll return to the app logged in

## 🛡️ Security Notes

- **Never commit** `.env` file to version control
- **Use different credentials** for production
- **Configure proper domains** for production deployment
- **Enable HTTPS** for production OAuth callbacks

## 🔍 Troubleshooting

### OAuth Not Configured Error
- Check that environment variables are set correctly
- Restart backend after updating `.env`
- Verify client IDs and secrets match

### Redirect URI Mismatch
- Ensure redirect URIs in OAuth settings exactly match:
  - Google: `http://localhost:8001/auth/oauth/callback/google`
  - GitHub: `http://localhost:8001/auth/oauth/callback/github`

### Invalid Client Error
- Double-check client ID and secret values
- Ensure OAuth app is active/not suspended
- Verify app is configured for correct environment

## 📱 Production Deployment

For production deployment:
1. **Update redirect URIs** to your production domain
2. **Configure CORS** to allow your production frontend
3. **Use HTTPS** for all OAuth callbacks
4. **Set proper environment variables** in production

## 🎯 Current Status

✅ **Traditional Login**: Working (admin/admin)  
⏳ **OAuth**: Ready for configuration  
🔧 **Environment File**: Created at `backend/.env`

The authentication system is fully functional - just add your OAuth credentials to enable social login!
