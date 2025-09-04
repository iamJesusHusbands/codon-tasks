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
app.add_middleware(OpenTelemetryMiddleware)

# 4) Define a simple route to test
@app.get("/ping")
def ping():
    # When you visit http://localhost:8000/ping
    # You’ll see a new trace in Jaeger with details of this request
    return {"pong": True}


