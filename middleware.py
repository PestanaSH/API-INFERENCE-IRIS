"""
Middlewares for Logging and Metrics
Intercepts all requests for automatic logging

Middleware = code that runs BEFORE and AFTER each request
Allows:

* Automatically measure response time
* Add a trace_id for tracing
* Log all requests without modifying endpoints

"""
import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.logging_config import logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs all requests automatically.

    Adds to each request:

    * trace_id: Unique ID (UUID) to trace the request across all logs
    * latency_ms: Response time in milliseconds
    * Response headers with trace_id and timing

    Flow:

        1. Request arrives
        2. Middleware generates a trace_id and marks the start time
        3. Request is processed by the endpoint
        4. Middleware calculates latency and logs it
        5. Response is returned with extra headers
    """
    
    async def dispatch(self, request: Request, call_next):
        # Generates a unique trace_id for tracing
        # Allows correlating logs from the same request
        trace_id = str(uuid.uuid4())[:8]  # First 8 characters of the UUID
        request.state.trace_id = trace_id
        
        # Captures the start time
        start_time = time.perf_counter()
        
        # Processes the request (calls the endpoint)
        response = await call_next(request)
        
        # Calculates latency
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        # Structured request logging
        # Does not log /metrics to avoid noise (Prometheus scrapes it every 15 seconds)
        if request.url.path != "/metrics":
            logger.info(
                "request_completed",
                extra={
                    "trace_id": trace_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "latency_ms": round(latency_ms, 2),
                    "client_ip": request.client.host if request.client else None,
                }
            )
        
        # Adds tracing headers to the response
        # Useful for client-side debugging
        response.headers["X-Trace-ID"] = trace_id
        response.headers["X-Response-Time-Ms"] = str(round(latency_ms, 2))
        
        return response