# backend/auth/google_auth.py
import os
import json
import requests
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.oauth2 import id_token as google_id_token
from google.auth.transport.requests import Request

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/calendar.events",
]

CLIENT_ID = os.getenv("GOOGLE_WEB_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_WEB_CLIENT_SECRET")
REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8000/auth/google/callback")


def _client_config() -> dict:
    return {
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


def _flow(code_verifier: str | None = None) -> Flow:
    return Flow.from_client_config(
        _client_config(), scopes=SCOPES, redirect_uri=REDIRECT_URI, code_verifier=code_verifier
    )


def build_authorization_url(state: str) -> tuple[str, str]:
    flow = _flow()
    # access_type=offline -> issue a refresh_token; prompt=consent -> issue one
    # every time (Google otherwise only grants it on a user's very first consent).
    url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
        state=state,
    )
    # authorization_url() auto-generates a PKCE code_verifier on the Flow instance
    # (and embeds its hash as code_challenge in the URL). The callback rebuilds a
    # *new* Flow to exchange the code, so this verifier must round-trip via the
    # caller (a cookie) or Google will reject the exchange with "Missing code verifier".
    return url, flow.code_verifier


def exchange_code_for_credentials(code: str, code_verifier: str) -> Credentials:
    flow = _flow(code_verifier=code_verifier)
    flow.fetch_token(code=code)
    return flow.credentials


def decode_identity(credentials: Credentials) -> dict:
    """Returns the {sub, email, name, picture} claims from the ID token issued alongside the credentials."""
    claims = google_id_token.verify_oauth2_token(
        credentials.id_token, Request(), CLIENT_ID
    )
    return {
        "sub": claims["sub"],
        "email": claims.get("email"),
        "name": claims.get("name"),
        "picture": claims.get("picture"),
    }


def credentials_to_dict(credentials: Credentials) -> dict:
    return json.loads(credentials.to_json())


def revoke_credentials(credentials: Credentials) -> None:
    """
    Tells Google to revoke this grant, so Breadcrumbs also disappears from the
    user's "third-party apps with account access" list — not just forgotten
    locally. Best-effort: a failed revoke shouldn't block a local disconnect.
    """
    token = credentials.token or credentials.refresh_token
    if not token:
        return
    try:
        requests.post(
            "https://oauth2.googleapis.com/revoke",
            params={"token": token},
            headers={"content-type": "application/x-www-form-urlencoded"},
            timeout=5,
        )
    except requests.RequestException:
        pass


def get_credentials_for_user(user_doc: dict, users_collection) -> Credentials:
    """Rebuilds this user's stored Google credentials, refreshing (and persisting
    the refreshed token) if the access token has expired."""
    stored = user_doc.get("google_credentials")
    if not stored:
        raise ValueError("User has not connected a Google account")

    creds = Credentials.from_authorized_user_info(stored, SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            users_collection.update_one(
                {"_id": user_doc["_id"]},
                {"$set": {"google_credentials": credentials_to_dict(creds)}},
            )
        else:
            raise ValueError("Google credentials are invalid and cannot be refreshed")

    return creds
