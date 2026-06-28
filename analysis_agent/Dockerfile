FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.30.0" \
    "sqlalchemy[asyncio]>=2.0.30" \
    "asyncpg>=0.29.0" \
    "pydantic>=2.8.0" \
    "pydantic-settings>=2.3.0" \
    "httpx>=0.27.0" \
    "bcrypt>=4.0.0" \
    "python-jose[cryptography]>=3.3.0" \
    "redis[asyncio]>=5.0.0" \
    "aiosmtplib>=3.0.0" \
    "websockets>=12.0" \
    "email-validator>=2.0.0" \
    "aiosqlite>=0.19.0"

COPY analysis_agent/ ./analysis_agent/

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "analysis_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
