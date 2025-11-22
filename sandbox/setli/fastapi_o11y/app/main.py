import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.routing import APIRoute
from loguru import logger
from pydantic import BaseModel
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

from snowflake.telemetry.logs import SnowflakeLogFormatter
import logging

logger = logging.getLogger("service")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(SnowflakeLogFormatter())
logger.addHandler(handler)

# Emit logs with record attributes (`extra` argument)
logger.warning("warning log record with attributes", extra={"custom": True})
logger.debug("debug log with nested attributes", extra={"nested": {"key1": [1, 2, 3]}})

load_dotenv()


class HealthCheckResponse(BaseModel):
    status: str
    success: bool
    system_name: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {app.title}...")
    for r in app.routes:
        if isinstance(r, APIRoute):
            logger.info(r.path)
    yield
    logger.info(f"Stopping {app.title}...")


# Initialize app and tracing
app = FastAPI(title="Example Service", version="0.1.0", lifespan=lifespan)
resource = Resource(attributes={"service.name": "example-app"})
provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("my.tracer.name")
LoggingInstrumentor().instrument()
FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)

@app.get("/")
async def root():
    return {"message": "There's no place like home 🏠"}


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    name = os.getenv("SYSTEM_NAME", "unknown")
    logger.debug("bob")
    return HealthCheckResponse(status="Good to go", success=True, system_name=name)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True, log_level="debug", log_config="log_conf.yaml")
