from fastapi import FastAPI, Request, Form, Depends, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Telemetry initialization
from app.telemetry import init_tracing
# Auto-instrument HTTP requests with OpenTelemetry
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware

# (Optional) Use your secrets loader anywhere you need secrets
from app.secrets_loader import secrets

# Prometheus metrics
from prometheus_fastapi_instrumentator import Instrumentator

# >>> Cost-cap integration
# - cost_guard() gives each request its own cost tracker
# - CostCapExceeded is the error we raise if the request exceeds the budget
from app.executor_guard import cost_guard
from app.cost_cap import CostCapExceeded

# 1) Initialize OpenTelemetry once at startup so spans export to your collector
init_tracing()

# 2) Create the FastAPI app
app = FastAPI(title="Agent Factory Web")

# instrument and expose Prometheus metrics at /metrics
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# 3) Add OTel middleware (auto-creates a span per HTTP request)
#    Exclude noisy paths if you have them (health/metrics)
app.add_middleware(
    OpenTelemetryMiddleware,
    excluded_urls="/health,/metrics"
)

# 4) Jinja setup: tell FastAPI where templates live
templates = Jinja2Templates(directory="templates")
# (Optional) add global variables available in all templates:
templates.env.globals["year"] = "2025"

# 5) Serve static files at /static
app.mount("/static", StaticFiles(directory="static"), name="static")

# ------------------------------
# Cost-cap: FastAPI integration
# ------------------------------

def get_tracker():
    """
    Dependency that provides a per-request CostTracker.
    - We use a context manager so each request gets its own tracker.
    - On request end, you could emit logs/metrics about total spend.
    """
    with cost_guard() as tracker:
        yield tracker

@app.exception_handler(CostCapExceeded)
async def cost_cap_handler(_, exc: CostCapExceeded):
    """
    If a request tries to spend more than the configured cap:
    - Return a clear JSON error so the client knows what happened.
    - 402 is 'Payment Required' (rarely used) but semantically close.
      You could also use 429 (rate limiting) if you prefer.
    """
    return JSONResponse(
        status_code=402,
        content={
            "error": "cost_cap_exceeded",
            "message": str(exc),
            "cap": getattr(exc, "cap", None),
            "attempted": getattr(exc, "attempted", None),
        },
    )

# ---- Routes ----

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    # Example of using your secrets loader (if needed):
    # openai_key = secrets.get("OPENAI_API_KEY")  # will raise KeyError if missing
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/echo", response_class=HTMLResponse)
def echo_form(request: Request):
    # Show the form with no result yet
    return templates.TemplateResponse("echo_result.html", {"request": request, "echoed": None})

@app.post("/echo", response_class=HTMLResponse)
def echo_submit(request: Request, text: str = Form(...)):
    # Handle form post, return a page with the echoed text
    return templates.TemplateResponse("echo_result.html", {"request": request, "echoed": text})

# API that demonstrates cost tracking.
# Replace the "simulated usage" with real usage from your LLM client later.
@app.post("/ask")
async def ask(q: str, response: Response, tracker = Depends(get_tracker)):
    """
    Demo endpoint to show how to report usage against the cost cap.

    As a beginner mental model:
    1. You call your LLM/tool.
    2. The LLM returns a 'usage' object (prompt_tokens, completion_tokens, etc.).
    3. You pass that usage to tracker.add_usage(model, prompt_tokens, completion_tokens).
    4. If the total would exceed the cap, a CostCapExceeded error is raised.
    """

    # --- Simulated LLM usage (replace with REAL usage from the provider response) ---
    # Example pricing is configured via env (PRICE__... vars).
    tracker.add_usage(model="gpt4o", prompt_tokens=800, completion_tokens=200)

    # If we're near the cap (e.g., >= 80%), you can signal it with a response header.
    if hasattr(tracker, "near_threshold") and tracker.near_threshold():
        response.headers["X-Cost-Warn"] = "true"

    # A real endpoint would return your model's answer here.
    return {"answer": f"Echo: {q}"}

# Basic health endpoint if you want to exclude from tracing
@app.get("/health")
def health():
    return {"ok": True}
