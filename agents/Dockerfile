FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --upgrade pip \
    && pip install -e ".[agents,rag]" \
    && pip install "uvicorn[standard]>=0.30"

COPY src ./src

EXPOSE 8001

CMD ["uvicorn", "src.server.main:app", "--host", "0.0.0.0", "--port", "8001"]
