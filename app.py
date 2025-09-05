# app.py

from fastapi import FastAPI
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from telemetry import init_tracing  # OTel setup function from telemetry.py

# 1) Initialize tracing
init_tracing()

# 2) Create the FastAPI app instance
app = FastAPI()

# 3) Add the OpenTelemetry middleware
#    - This automatically creates a trace span for every incoming HTTP request
#    - The span will include method (GET/POST), path, status code, and timing info
# but exclude "noisy" endpoints that we don’t want to trace.
# Excluding these prevents clutter in Jaeger and saves storage.
app.add_middleware(
    OpenTelemetryMiddleware,
    excluded_urls="/health,/metrics,/live,/ready/readiness,/ping,/favicon.ico,/robots.txt"  # Comma-separated or regex pattern
)

# 4) Define a simple route to test
@app.get("/ping")
def ping():
    # When you visit http://localhost:8000/ping
    # You’ll see a new trace in Jaeger with details of this request
    return {"pong": True}


