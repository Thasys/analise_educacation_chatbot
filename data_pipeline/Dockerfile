FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --upgrade pip \
    && pip install -e ".[dev]" \
    && pip install "dbt-core>=1.8" "dbt-duckdb>=1.8"

COPY src ./src

# Mantemos o container apto a rodar tanto coletores (python -m src.flows.X)
# quanto dbt (dbt build, dbt seed, etc). Use:
#   docker compose run --rm data_pipeline python -m src.flows.worldbank
#   docker compose run --rm -w /dbt data_pipeline dbt build
CMD ["python", "-c", "print('data_pipeline container OK - use docker compose run --rm data_pipeline <comando>')"]
