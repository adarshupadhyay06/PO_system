"""
Authentication router.
Supports:
  1. Demo login (username/password) — for local testing without OAuth.
  2. Google OAuth 2.0 PKCE flow — production identity.
"""
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from core.config import settings
from core.security import create_access_token
from schemas.schemas import DemoLoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Auth"])

# ── Demo accounts (local dev only) ────────────────────────────
DEMO_USERS = {
    "admin": {"password": "admin123", "email": "admin@pomsystem.com", "name": "Admin User", "role": "admin"},
    "buyer": {"password": "buyer123", "email": "buyer@pomsystem.com", "name": "Buyer User",  "role": "buyer"},
}

GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO  = "https://www.googleapis.com/oauth2/v3/userinfo"


@router.post("/demo-login", response_model=TokenResponse)
async def demo_login(payload: DemoLoginRequest):
    """Demo login — no real IDP needed. For local development."""
    user = DEMO_USERS.get(payload.username)
    if not user or user["password"] != payload.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token_data = {"sub": user["email"], "email": user["email"], "name": user["name"], "role": user["role"]}
    token = create_access_token(token_data)
    return TokenResponse(access_token=token, user={"email": user["email"], "name": user["name"], "role": user["role"]})


@router.get("/google/login")
async def google_login():
    """Redirect user to Google OAuth consent screen."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Google OAuth not configured")

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{query}")


@router.get("/google/callback")
async def google_callback(code: str, request: Request):
    """Exchange auth code for tokens and issue our own JWT."""
    async with httpx.AsyncClient() as client:
        try:
            token_resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.OAUTH_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
            token_resp.raise_for_status()
            google_tokens = token_resp.json()

            user_resp = await client.get(
                GOOGLE_USERINFO,
                headers={"Authorization": f"Bearer {google_tokens['access_token']}"},
            )
            user_resp.raise_for_status()
            user_info = user_resp.json()

        except httpx.HTTPError as exc:
            raise HTTPException(status_code=400, detail=f"OAuth error: {exc}")

    token_data = {
        "sub": user_info["sub"],
        "email": user_info["email"],
        "name": user_info.get("name", ""),
        "picture": user_info.get("picture", ""),
        "role": "buyer",
    }
    token = create_access_token(token_data)

    # Redirect to frontend with JWT in query param (frontend stores in memory/localStorage)
    frontend = settings.FRONTEND_ORIGIN
    return RedirectResponse(f"{frontend}/?token={token}&name={token_data['name']}")


@router.get("/me")
async def get_me(request: Request):
    """Return the payload of the supplied Bearer token."""
    from core.security import get_current_user, bearer_scheme
    creds = await bearer_scheme(request)
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")
    from core.security import decode_token
    return decode_token(creds.credentials)
