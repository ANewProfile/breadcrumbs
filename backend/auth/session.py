from fastapi import Request, HTTPException
from database import sessions_collection, users_collection
from services.user_service import get_user_for_session

SESSION_COOKIE_NAME = "breadcrumbs_session"


def get_current_user(request: Request) -> dict:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    user = get_user_for_session(sessions_collection, users_collection, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def get_current_user_optional(request: Request) -> dict | None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    return get_user_for_session(sessions_collection, users_collection, token)
