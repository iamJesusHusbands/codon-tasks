from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Telemetry (you wrote this earlier)
from app.telemetry import init_tracing
# Auto-instrument HTTP requests (from your earlier task)
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware

# (Optional) Use your secrets loader anywhere you need secrets
from app.secrets_loader import secrets

from prometheus_fastapi_instrumentator import Instrumentator

# 1) Initialize OpenTelemetry once at startup so spans export to your collector
init_tracing()

# 2) Create the FastAPI app
app = FastAPI(title="Agent Factory Web")

# instrument and expose at /metrics
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

# (Nice) Add a basic health endpoint if you want to exclude from tracing
@app.get("/health")
def health():
    return {"ok": True}
