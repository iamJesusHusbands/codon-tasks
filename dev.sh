```bash
#!/usr/bin/env bash
set -euo pipefail

# --- 1) Check Python ---
if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 not found. Install Python 3.10+ and retry." >&2
  exit 1
fi

# --- 2) Create and activate virtual env ---
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

# --- 3) Upgrade pip tools & install requirements ---
python -m pip install --upgrade pip setuptools wheel
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
else
  echo "Error: requirements.txt not found at project root." >&2
  exit 1
fi

# --- 4) Ensure a .env file exists ---
if [ -f .env ]; then
  echo ".env already exists — leaving it as is."
elif [ -f .env.example ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
else
  # Minimal defaults: safe for local dev only .. looking into production best practices
  cat > .env <<'EOF'
# App
APP_PORT=8000
APP_LOG_LEVEL=info

# Postgres
POSTGRES_USER=agent
POSTGRES_PASSWORD=agentpw
POSTGRES_DB=agentdb
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# OpenTelemetry (Jaeger all-in-one exposes OTLP on 4318 HTTP)
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_SERVICE_NAME=mcp-agent-factory
EOF
  echo "Wrote minimal .env"
fi

# --- 5) Bring up local infra with Docker Compose ---
if ! command -v docker >/dev/null 2>&1; then
  echo "Error: Docker is required. Install Docker Desktop/Engine." >&2
  exit 1
fi
# Compose V2 lives under `docker compose`
if ! docker compose version >/dev/null 2>&1; then
  echo "Error: 'docker compose' CLI not found. Update Docker to a version with Compose V2." >&2
  exit 1
fi

docker compose up -d

# --- 6) Next steps ---
echo
echo "Done! Dev infra is running (detached)."
echo
echo "Services:"
echo "- Postgres:   localhost:5432  (db=agentdb user=agent pw=agentpw)"
echo "- Redis:      localhost:6379"
echo "- Jaeger UI:  http://localhost:16686"
echo "- Prometheus: http://localhost:9090"
echo
echo "Next steps:"
echo "1) Activate venv:    source .venv/bin/activate"
echo "2) Run your app:     uvicorn app.main:app --reload --port \${APP_PORT:-8000}"
echo "3) Metrics endpoint: http://localhost:\${APP_PORT:-8000}/metrics"

```