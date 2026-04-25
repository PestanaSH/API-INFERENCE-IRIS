"""
Rate Limiting with SlowAPI  
Protects the API against abuse and DDoS attacks  

Rate Limiting = limiting the number of requests over time  
Example: 30 requests per minute per IP  

Why use it:  

SlowAPI is based on Flask-Limiter, adapted for FastAPI  
"""
import os

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse

from app.logging_config import logger
from app.metrics import RATE_LIMIT_EXCEEDED

# =============================================================================
# LIMITER CONFIGURATION
# =============================================================================

# Function that identifies the client (by IP)
# In production, you can use the X-Forwarded-For header if behind a proxy
def get_client_identifier(request: Request) -> str:
    """
    Returns a unique client identifier for rate limiting.

    Uses the client's IP address. In production behind a load balancer,
    consider using hte X-Forwarded-For header.
    """
    # If behind a proxy (Render, AWS, etc.), get the real IP.
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


DEFAULT_RATE_LIMIT = os.getenv("RATE_LIMIT_DEFAULT", "60/minute")
PREDICT_RATE_LIMIT = os.getenv("RATE_LIMIT_PREDICT", "30/minute")
BATCH_RATE_LIMIT = os.getenv("RATE_LIMIT_BATCH", "10/minute")
LOGIN_RATE_LIMIT = os.getenv("RATE_LIMIT_LOGIN", "10/minute")

limiter = Limiter(
    key_func=get_client_identifier,
    default_limits=[DEFAULT_RATE_LIMIT],
    storage_uri="memory://", 
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom handler when the rate limit is exceeded.

    Returns a user-friendly JSON instead of plain text.
    Also logs the event and increments a Prometheus metric.
    """
    client_ip = get_client_identifier(request)
    endpoint = request.url.path

    logger.warning(
        "rate_limit_exceeded",
        extra={
            "client_ip": client_ip,
            "endpoint": endpoint,
            "limit": str(exc.detail),
        }
    )

    # Prometheus metric
    RATE_LIMIT_EXCEEDED.labels(endpoint=endpoint, client_ip=client_ip).inc()

    return JSONResponse(
        status_code=439,
        content={
            "error": "rate_limit_exceeded",
            "message": f"Muitas requisicoes. Limite: {exc.detail}",
            "retry_after_seconds": 60, 
        },
        headers={"Retry-After": "60"}
    )


