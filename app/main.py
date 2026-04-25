from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from prometheus_fastapi_instrumentator import Instrumentator
from app.middleware import LoggingMiddleware
from app.rate_limit import limiter, rate_limit_exceeded_handler
from app.routers import auth, info, predict
from app.core import API_VERSION

app = FastAPI(
    title="Iris API v2",
    description="""
## Iris Flower Classification API

Complete version with all course features:

### Features
- 🔐 **JWT Authentication** - Secure login with tokens
- 🚦 **Rate Limiting** - Protection against abuse
- 📊 **Prometheus Metrics** - Real-time monitoring
- 📝 **Structured Logs** - JSON for observability
- 📦 **Batch Prediction** - Process multiple flowers at once

### Main Endpoints
- `POST /login` - Get JWT token
- `POST /predict` - Single prediction
- `POST /predict/batch` - Batch prediction (NEW!)
- `GET /metrics` - Prometheus metrics
- `GET /health` - Health check

### Request Limits (Rate Limiting)
- `/login`: 10 req/minute
- `/predict`: 30 req/minute
- `/predict/batch`: 10 req/minute
""",
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2/bundles/redoc.standalone.js",
)

# Rate Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(LoggingMiddleware)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")

app.include_router(info.router)
app.include_router(auth.router)
app.include_router(predict.router)