# =============================================================================
# Dockerfile para API Iris com JWT (Modularizado)
# =============================================================================

# Imagem base: Python 3.11 slim (menor e mais segura)
FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Definir diretorio de trabalho dentro do container
WORKDIR /app

COPY pyproject.toml uv.lock ./

# Instalar dependencias
RUN uv sync --frozen --no-dev

# Copiar o pacote app inteiro (codigo + modelos)
COPY app/ ./app/

# Expor a porta (documentacao, Render usa $PORT)
EXPOSE 8000

# Comando para iniciar a API (agora app.main:app)
# Usamos $PORT para compatibilidade com Render/Heroku
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]