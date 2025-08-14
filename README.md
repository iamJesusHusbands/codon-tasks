# Agent Factory

This project is for quickly seting up a development environment using Docker. I've tried to include the tools for databases, caching, tracing, and monitoring—all with simple commands. From the product requirements document

## What's Included?

## I am still doing research on what all of these different tools do.

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

## Important Files

- `docker-compose.yml`: Lists all the services and how to run them.
- `prometheus.yml`: Settings for Prometheus.
- `.env.example`: Shows what environment variables you can set.
- `requirements.txt`: Python packages (if you use Python).
- `dev.sh`: Helper script for development (if needed).

## Notes
- All your data is saved in Docker volumes, so it won't disappear when you stop containers.
- Grafana is ready to use if you want dashboards—just uncomment it in `docker-compose.yml`.

---

If you get stuck, check the official docs for each tool or ask for help!
