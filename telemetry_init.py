# telemetry_init.py 
import os
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

service_name = os.getenv("OTEL_SERVICE_NAME", "agent-factory")
trace.set_tracer_provider(TracerProvider(resource=Resource.create({"service.name": service_name})))
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

tracer = trace.get_tracer("setup")
with tracer.start_as_current_span("startup"):
    pass
