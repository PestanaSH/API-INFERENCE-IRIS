"""
API Iris com JWT - Versao Producao (Modularizada)
Pronta para deploy em container/cloud
"""
import os
import pickle
import logging
from pathlib import Path

import numpy as np
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

# Importa funcoes do modulo auth
from app.auth import (
    create_token,
    get_current_user,
    authenticate_user,
    TOKEN_EXPIRE_MINUTES,
)


# =============================================================================
# CONFIGURACOES
# =============================================================================
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")


# =============================================================================
# LOGGING
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


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
if not MODELO_OK:
    logger.warning("Modelo NAO encontrado! API funcionara sem predicao.")


# =============================================================================
# APLICACAO FASTAPI
# =============================================================================
app = FastAPI(
    title="API Iris com JWT",
    description="API de classificacao de flores Iris com autenticacao JWT. Deploy em producao.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


@app.get("/")
def home():
    """Informacoes da API."""
    return {
        "api": "Iris Classifier",
        "versao": "2.0.0",
        "ambiente": ENVIRONMENT,
        "modelo_carregado": MODELO_OK,
        "docs": "/docs",
        
    }


@app.get("/health")
def health():
    """Health check para monitoramento."""
    return {
        "status": "healthy" if MODELO_OK else "degraded",
        "modelo": MODELO_OK,
        "ambiente": ENVIRONMENT,
    }


@app.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest):
    """Faz login e retorna token JWT."""
    user = authenticate_user(credentials.username, credentials.password)
    
    if not user:
        logger.warning(f"Login falhou para: {credentials.username}")
        raise HTTPException(status_code=401, detail="Usuario ou senha incorretos")
    
    token = create_token(user["username"], user["role"])
    logger.info(f"Login bem-sucedido: {user['username']}")
    return TokenResponse(access_token=token, expires_in=TOKEN_EXPIRE_MINUTES * 60)


@app.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    """Retorna informacoes do usuario logado."""
    return current_user


@app.post("/predict", response_model=IrisResponse)
def predict(payload: IrisRequest, current_user: dict = Depends(get_current_user)):
    """Faz predicao (requer autenticacao)."""
    if not MODELO_OK:
        raise HTTPException(status_code=503, detail="Modelo nao disponivel")
    
    features = np.array([[
        payload.sepal_length, payload.sepal_width,
        payload.petal_length, payload.petal_width
    ]])
    
    pred_idx = modelo.predict(features)[0]
    probs = modelo.predict_proba(features)[0]
    classe = classes[pred_idx]
    
    logger.info(f"Predicao: {classe} por {current_user['username']}")
    
    return IrisResponse(
        sucesso=True,
        classe=classe,
        probabilidades={classes[i]: round(float(p), 4) for i, p in enumerate(probs)},
        usuario=current_user["username"]
    )

