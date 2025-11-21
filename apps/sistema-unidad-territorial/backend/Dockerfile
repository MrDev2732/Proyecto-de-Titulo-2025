# Dockerfile para el backend FastAPI
FROM python:3.13-slim

# Variables de entorno para Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /apps

# Instalar Poetry
RUN pip install poetry==1.7.1

# Copiar archivos de dependencias
COPY pyproject.toml poetry.lock poetry.toml ./

# Instalar dependencias (sin dev)
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root --only main

# Copiar el código fuente
COPY . .

# Crear directorios necesarios
RUN mkdir -p uploads logs

# El frontend build se copia desde el workflow de GitHub
# La estructura esperada es: dist/frontend/
# Esto se monta en /app/dist/frontend/ en el contenedor

# Exponer puerto
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Comando para ejecutar la aplicación
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
