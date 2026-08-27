from fastapi import HTTPException, Request
from limits import parse
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter
from auth.session import SESSION_COOKIE_NAME

# In-memory: fine for Railway's single-instance Hobby deployment. If this ever
# runs multiple instances, counts would need a shared store (e.g. Redis)
# instead, since each instance would otherwise track its own count.
_storage = MemoryStorage()
_strategy = MovingWindowRateLimiter(_storage)

# Generous enough that normal usage (adding many tasks, polling the task
# list, editing settings) never comes close, but caps how much load one
# session or bot can put on the database before it's throttled.
_DEFAULT_LIMIT = parse("300/minute")

_TOO_MANY_REQUESTS = HTTPException(status_code=429, detail="Too many requests — please slow down and try again shortly.")


def _identity(request: Request) -> str:
    """Keys by session cookie when present so one signed-in user's limit
    doesn't get shared with (or dodged by) anyone else on the same IP —
    NAT'd households/offices, shared campus wifi, etc. Falls back to IP for
    the pre-login endpoints (OAuth start/callback) where no session exists yet."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        return f"session:{token}"
    return f"ip:{request.client.host}" if request.client else "ip:unknown"


def default_rate_limit(request: Request) -> None:
    """Global dependency, applied to every route in main.py, so no single
    user/bot can hammer the API or database no matter which endpoint they hit."""
    if not _strategy.hit(_DEFAULT_LIMIT, "global", _identity(request)):
        raise _TOO_MANY_REQUESTS


def rate_limit(limit_str: str):
    """Extra, tighter limit for one route on top of the global default —
    for endpoints that call out to Google's Calendar API or do bulk/
    destructive writes, where a burst is expensive rather than just noisy.
    Usage: @router.post(..., dependencies=[Depends(rate_limit("10/minute"))])
    """
    limit = parse(limit_str)

    def dependency(request: Request) -> None:
        if not _strategy.hit(limit, request.url.path, _identity(request)):
            raise _TOO_MANY_REQUESTS

    return dependency
