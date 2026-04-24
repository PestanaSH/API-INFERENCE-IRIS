"""
API Iris com JWT - Versao Producao (Modularizada)
Pronta para deploy em container/cloud
"""
import os
import pickle
import time
from pathlib import Path
import numpy as np

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from prometheus_fastapi_instrumentator import Instrumentator

from app.auth import (
    create_token,
    get_current_user,
    authenticate_user,
    TOKEN_EXPIRE_MINUTES,
)
from app.logging_config import setup_logging
from middleware import LoggingMiddleware
from app.metrics import(
    PREDICTIONS_TOTAL,
    LOGIN_ATTEMPTS,
    PREDICTION_LATENCY,
    MODEL_LOADED,
)

# =============================================================================
# CONFIGS
# =============================================================================
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
API_VERSION = "2.1.0"


# =============================================================================
# LOGGING
# =============================================================================
logger = setup_logging(os.getenv("LOG_LEVEL", "INFO"))


# =============================================================================
# SCHEMAS
# =============================================================================
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class IrisRequest(BaseModel):
    sepal_length: float = Field(..., ge=0, le=10, description="Comprimento da sepala (cm)")
    sepal_width: float = Field(..., ge=0, le=10, description="Largura da sepala (cm)")
    petal_length: float = Field(..., ge=0, le=10, description="Comprimento da petala (cm)")
    petal_width: float = Field(..., ge=0, le=10, description="Largura da petala (cm)")


class IrisResponse(BaseModel):
    sucesso: bool
    classe: str
    probabilidades: dict
    usuario: str


# =============================================================================
# CARREGAMENTO DO MODELO
# =============================================================================
MODEL_PATHS = [
    Path("app/models/modelo_iris.pkl"),      # Estrutura modularizada
    Path("models/modelo_iris.pkl"),           # Alternativa
    Path("/app/app/models/modelo_iris.pkl"),  # Dentro do container
    Path("modelo_iris.pkl"),                  # Raiz (fallback)
]

modelo = None
classes = None

for model_path in MODEL_PATHS:
    if model_path.exists():
        with open(model_path, 'rb') as f:
            modelo = pickle.load(f)
        classes_path = model_path.parent / "classes_iris.pkl"
        if classes_path.exists():
            with open(classes_path, 'rb') as f:
                classes = pickle.load(f)
        logger.info(f"Modelo carregado de: {model_path}")
        break

MODELO_OK = modelo is not None and classes is not None

MODEL_LOADED.set(1 if MODELO_OK else 0)

if not MODELO_OK:
    logger.warning("model_not_found", extra={"searched_paths": [str(p) for p in MODEL_PATHS]})


# =============================================================================
# FASTAPI APP
# =============================================================================
app = FastAPI(
    title="API Iris With Monitoring",
    description="Classification API with structured logs and Prometheus metrics",
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2/bundles/redoc.standalone.js"
)

app.add_middleware(LoggingMiddleware)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.get("/")
def home():
    """API Informations"""
    return {
        "api": "Iris Classifier",
        "versao": API_VERSION,
        "ambiente": ENVIRONMENT,
        "modelo_carregado": MODELO_OK,
        "docs": "/docs",
        "metrics": "/metrics",
        "health": "/health",
    }


@app.get("/health")
def health():
    """Health check"""
    return {
        "status": "healthy" if MODELO_OK else "degraded",
        "modelo": MODELO_OK,
        "ambiente": ENVIRONMENT,
        "version": API_VERSION,
    }


@app.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, request: Request):
    """Make login and retorn JWT token."""
    user = authenticate_user(credentials.username, credentials.password)
    trace_id = getattr(request.state, 'trace_id', 'N/A')

    if not user:
        LOGIN_ATTEMPTS.labels(status="failed").inc()

        logger.warning("login_failed", extra={
            "username": credentials.username,
            "trace_id": trace_id, 
        })
        raise HTTPException(status_code=401, detail="Usuario ou senha incorretos")

    LOGIN_ATTEMPTS.labels(status="success").inc()

    token = create_token(user["username"], user["role"])

    logger.info("login_success", extra={
        "username": user["username"],
        "role": user["role"],
        "trace_id": trace_id,
    })

    return TokenResponse(access_token=token, expires_in=TOKEN_EXPIRE_MINUTES * 60)

@app.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return current_user


@app.post("/predict", response_model=IrisResponse)
def predict(payload: IrisRequest, request: Request, current_user: dict = Depends(get_current_user)):
 
    if not MODELO_OK:
        raise HTTPException(status_code=503, detail="Modelo nao disponivel")
    
    trace_id = getattr(request.state, 'trace_id', 'N/A')


    # Measures prediction latency
    start = time.perf_counter()

    features = np.array([[
        payload.sepal_length, payload.sepal_width,
        payload.petal_length, payload.petal_width
    ]])
    
    pred_idx = modelo.predict(features)[0]
    probs = modelo.predict_proba(features)[0]
    classe = classes[pred_idx]
    confidence = float(max(probs))

    latency = time.perf_counter() - start
    
    PREDICTIONS_TOTAL.labels(classe=classe, user=current_user["username"]).inc()
    PREDICTION_LATENCY.observe(latency)

    logger.info("prediction_completed", extra={
        "trace_id": trace_id,
        "user": current_user["username"], 
        "classe": classe,
        "confidence": round(confidence, 4),
        "latency_ms": round(latency * 1000, 2),
        "features": {
            "sepal_length": payload.sepal_length,
            "sepal_width": payload.sepal_width,
            "petal_length": payload.petal_length,
            "petal_width": payload.petal_width,
        }
    })
    
    return IrisResponse(
        sucesso=True,
        classe=classe,
        probabilidades={classes[i]: round(float(p), 4) for i, p in enumerate(probs)},
        usuario=current_user["username"]
    )

