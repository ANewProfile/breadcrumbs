from fastapi import HTTPException, Request
from limits import parse
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter
from auth.session import SESSION_COOKIE_NAME

# fine for now, but need a shared store like Redis if this gets too big and runs multiple instances
_storage = MemoryStorage()
_strategy = MovingWindowRateLimiter(_storage)

# very generous for normal people
_DEFAULT_LIMIT = parse("300/minute")

_TOO_MANY_REQUESTS = HTTPException(status_code=429, detail="Too many requests — please slow down and try again shortly.")


def _identity(request: Request) -> str:
    """Keys by session cookie when present so multiple people from same house WiFi (and thus same IP) doesn't mess things up. Calls back to IP for
    the pre-login endpoints (OAuth start/callback) where no session exists yet."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        return f"session:{token}"
    return f"ip:{request.client.host}" if request.client else "ip:unknown"


def default_rate_limit(request: Request) -> None:
    """Global rate limiting to protect against you know what."""
    if not _strategy.hit(_DEFAULT_LIMIT, "global", _identity(request)):
        raise _TOO_MANY_REQUESTS


def rate_limit(limit_str: str):
    """Extra limit for one route on top of the global default
    for endpoints that call out to Google's Calendar API or do bulk 
    writes.
    Usage: @router.post(..., dependencies=[Depends(rate_limit("10/minute"))])
    """
    limit = parse(limit_str)

    def dependency(request: Request) -> None:
        if not _strategy.hit(limit, request.url.path, _identity(request)):
            raise _TOO_MANY_REQUESTS

    return dependency
