import os
import secrets
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from auth.google_auth import (
    build_authorization_url,
    exchange_code_for_credentials,
    decode_identity,
    credentials_to_dict,
)
from auth.session import get_current_user_optional, SESSION_COOKIE_NAME
from rate_limit import rate_limit
from services.user_service import upsert_user, store_google_credentials, create_session, delete_session
from database import users_collection, sessions_collection

router = APIRouter()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN") or None
STATE_COOKIE_NAME = "breadcrumbs_oauth_state"
VERIFIER_COOKIE_NAME = "breadcrumbs_oauth_verifier"
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 days, matches user_service.SESSION_TTL_DAYS


@router.get("/google/login", dependencies=[Depends(rate_limit("20/minute"))])
def google_login():
    state = secrets.token_urlsafe(24)
    url, code_verifier = build_authorization_url(state)
    response = RedirectResponse(url)
    response.set_cookie(
        STATE_COOKIE_NAME,
        state,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        domain=COOKIE_DOMAIN,
        max_age=600,
    )
    response.set_cookie(
        VERIFIER_COOKIE_NAME,
        code_verifier,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        domain=COOKIE_DOMAIN,
        max_age=600,
    )
    return response


@router.get("/google/callback", dependencies=[Depends(rate_limit("20/minute"))])
def google_callback(request: Request, code: str, state: str):
    expected_state = request.cookies.get(STATE_COOKIE_NAME)
    if not expected_state or expected_state != state:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    code_verifier = request.cookies.get(VERIFIER_COOKIE_NAME)
    if not code_verifier:
        raise HTTPException(status_code=400, detail="Missing OAuth code verifier")

    credentials = exchange_code_for_credentials(code, code_verifier)
    identity = decode_identity(credentials)

    user = upsert_user(
        users_collection,
        google_sub=identity["sub"],
        email=identity["email"],
        name=identity["name"],
        picture=identity["picture"],
    )
    store_google_credentials(users_collection, user["_id"], credentials_to_dict(credentials))
    token = create_session(sessions_collection, user["_id"])

    response = RedirectResponse(FRONTEND_URL)
    response.delete_cookie(STATE_COOKIE_NAME, domain=COOKIE_DOMAIN)
    response.delete_cookie(VERIFIER_COOKIE_NAME, domain=COOKIE_DOMAIN)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        domain=COOKIE_DOMAIN,
        max_age=SESSION_MAX_AGE,
    )
    return response


@router.post("/logout")
def logout(request: Request):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    delete_session(sessions_collection, token)
    response = JSONResponse({"ok": True})
    response.delete_cookie(SESSION_COOKIE_NAME, domain=COOKIE_DOMAIN)
    return response


@router.get("/me")
def me(user: dict | None = Depends(get_current_user_optional)):
    if not user:
        return {"user": None}
    return {
        "user": {
            "id": str(user["_id"]),
            "email": user.get("email"),
            "name": user.get("name"),
            "picture": user.get("picture"),
            "google_connected": bool(user.get("google_credentials")),
        }
    }
