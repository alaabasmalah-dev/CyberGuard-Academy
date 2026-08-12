import os
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .. import models, security
from ..database import get_db

router = APIRouter(prefix="/api/auth", tags=["oauth"])

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI", "http://localhost:8000/api/auth/github/callback")


# ── Google (real login) ───────────────────────────────────────────────────────

@router.get("/google")
def google_login():
    if not GOOGLE_CLIENT_ID:
        return RedirectResponse(f"{FRONTEND_URL}/auth-callback?error=config")

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "select_account",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return RedirectResponse(url)


@router.get("/google/callback")
def google_callback(code: str | None = None, error: str | None = None, db: Session = Depends(get_db)):
    if error:
        return RedirectResponse(f"{FRONTEND_URL}/auth-callback?error=access_denied")
    if not code:
        return RedirectResponse(f"{FRONTEND_URL}/auth-callback?error=no_code")

    try:
        with httpx.Client(timeout=10) as client:
            token_res = client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
            token_res.raise_for_status()
            access_token = token_res.json()["access_token"]

            userinfo_res = client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            userinfo_res.raise_for_status()
            info = userinfo_res.json()
    except Exception:
        return RedirectResponse(f"{FRONTEND_URL}/auth-callback?error=server_error")

    if not info.get("email_verified", True):
        return RedirectResponse(f"{FRONTEND_URL}/auth-callback?error=email_not_verified")

    email = info["email"].lower()
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        user = models.User(
            name=info.get("name", email.split("@")[0]),
            email=email,
            hashed_password=None,
            role="Student",
            picture=info.get("picture"),
            provider="google",
            onboarding_completed=False,
        )
        db.add(user)
    else:
        user.picture = info.get("picture") or user.picture
        user.provider = user.provider or "google"
    db.commit()
    db.refresh(user)

    jwt_token = security.create_access_token({"sub": str(user.id)})
    return RedirectResponse(f"{FRONTEND_URL}/auth-callback?token={jwt_token}")


# ── GitHub (account connect, not login) ───────────────────────────────────────

@router.get("/github")
def github_connect(token: str | None = None):
    if not GITHUB_CLIENT_ID:
        return RedirectResponse(f"{FRONTEND_URL}/onboarding/github?github_error=config")

    # We're mid-onboarding here, so we pass the current user's JWT through
    # `state` — GitHub echoes it back untouched on the callback, which is how
    # we know *whose* account to attach the GitHub profile to.
    state = token or secrets.token_urlsafe(16)
    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": GITHUB_REDIRECT_URI,
        "scope": "read:user",
        "state": state,
    }
    url = "https://github.com/login/oauth/authorize?" + urlencode(params)
    return RedirectResponse(url)


@router.get("/github/callback")
def github_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    if error:
        return RedirectResponse(f"{FRONTEND_URL}/onboarding/github?github_error=access_denied")
    if not code:
        return RedirectResponse(f"{FRONTEND_URL}/onboarding/github?github_error=no_code")

    user_id = security.decode_user_id(state) if state else None
    if user_id is None:
        return RedirectResponse(f"{FRONTEND_URL}/onboarding/github?github_error=state_mismatch")

    try:
        with httpx.Client(timeout=10) as client:
            token_res = client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": GITHUB_CLIENT_ID,
                    "client_secret": GITHUB_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": GITHUB_REDIRECT_URI,
                },
                headers={"Accept": "application/json"},
            )
            token_res.raise_for_status()
            gh_access_token = token_res.json().get("access_token")
            if not gh_access_token:
                return RedirectResponse(f"{FRONTEND_URL}/onboarding/github?github_error=invalid_token")

            profile_res = client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {gh_access_token}"},
            )
            profile_res.raise_for_status()
            profile = profile_res.json()
    except Exception:
        return RedirectResponse(f"{FRONTEND_URL}/onboarding/github?github_error=server_error")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        return RedirectResponse(f"{FRONTEND_URL}/onboarding/github?github_error=session_error")

    user.github_connected = True
    user.github_username = profile.get("login")
    db.commit()

    params = {
        "github_status": "success",
        "github_login": profile.get("login", ""),
        "github_avatar": profile.get("avatar_url", ""),
        "github_html_url": profile.get("html_url", ""),
    }
    return RedirectResponse(f"{FRONTEND_URL}/onboarding/github?" + urlencode(params))
