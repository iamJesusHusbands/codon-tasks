# Agent Factory

This repo is all the tasks I need to completed related to Codon's Agent Factory

## I am still doing research on what all of these different tools do.

## Tools

- **Postgres**: A database to store your app's data.
- **Redis**: A fast key-value store for caching and quick data access.
- **Jaeger**: Lets you see how requests move through your app (tracing).
- **Prometheus**: Collects and shows metrics about your app and services.
- **Grafana** (optional): Makes dashboards to visualize your data (not enabled by default).

## How to Use

1. **Get the code**
   ```zsh
   git clone https://github.com/iamJesusHusbands/codon-tasks.git
   cd codon-tasks
   ```

2. **Set up your environment variables**
   - Copy `.env.example` to `.env`:
     ```zsh
     cp .env.example .env
     ```
   - Edit `.env` if you want to change default usernames, passwords, or ports.

3. **Start everything**
   ```zsh
   docker compose up -d
   ```
   This will start all the services in the background.

4. **Open the tools in your browser**
   - Postgres: `localhost:5432` (for apps to connect)
   - Redis: `localhost:6379` (for apps to connect)
   - Jaeger UI: [http://localhost:16686](http://localhost:16686)
   - Prometheus: [http://localhost:9090](http://localhost:9090)
   - Grafana (if enabled): [http://localhost:3000](http://localhost:3000)

## Files

- `docker-compose.yml`: Lists all the services and how to run them.
- `prometheus.yml`: Settings for Prometheus.
- `.env.example`: Shows what environment variables i've set. Can also set different variables.
- `requirements.txt`: Python packages.
- `dev.sh`: Helper script for development.

## Notes

## Continuous Integration (CI)

This project now includes a CI workflow for automated testing and checks. You can find the workflow file at:

- `.github/workflow/ci.yml`

Last updated: 14 August 2025
