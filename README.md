# Agent Factory

This repo contains all tasks and code for Codon's Agent Factory, including orchestration, observability, and testing.

## Tools & Services

- **Postgres**: Database for persistent storage.
- **Redis**: Fast key-value store for caching.
- **Jaeger**: Distributed tracing.
- **Prometheus**: Metrics collection.
- **Grafana** (optional): Dashboards (currently commented out).
- **Python**: Main language, with dependencies managed in `requirements.txt` and `requirements-dev.txt`.

## How to Use

1. **Clone the repo**
   ```zsh
   git clone https://github.com/iamJesusHusbands/codon-tasks.git
   cd codon-tasks
   ```

2. **Set up your environment**
   - Copy `.env.example` to `.env` and edit as needed.

3. **Create a virtual environment and install dependencies**
   ```zsh
   bash dev.sh
   ```

4. **Start all services**
   ```zsh
   docker compose up -d
   ```

5. **Access services**
   - Postgres: `localhost:5432`
   - Redis: `localhost:6379`
   - Jaeger UI: [http://localhost:16686](http://localhost:16686)
   - Prometheus: [http://localhost:9090](http://localhost:9090)
   - Grafana (if enabled): [http://localhost:3000](http://localhost:3000)

## Code Structure

- `graph.py`: Example LangGraph app with echo node and in-memory checkpointing.
- `tests/test_graph.py`: Pytest-based tests for `graph.py`.
- `requirements.txt`: Main dependencies.
- `requirements-dev.txt`: Dev dependencies (includes pytest, ruff, black, mypy, etc.).
- `dev.sh`: Script to set up Python environment and dependencies.
- `docker-compose.yml`: Service definitions.
- `prometheus.yml`: Prometheus config.
- `.env.example`: Example environment variables.
- `telemetry_init.py`: Sets up OpenTelemetry tracing for the project.

## Testing

- Run tests with:
  ```zsh
  pytest
  ```
  or
  ```zsh
  python -m pytest
  ```

## Continuous Integration (CI)

Automated testing and checks are set up in:
- `.github/workflow/ci.yml`

_Last updated: 27 August 2025_
