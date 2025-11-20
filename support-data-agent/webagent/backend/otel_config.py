"""OpenTelemetry Configuration - Vendor Agnostic

Uses pure OpenTelemetry APIs to support ANY observability backend that
supports OTLP (OpenTelemetry Protocol): Phoenix, Jaeger, Tempo, Datadog,
New Relic, Honeycomb, etc.

Configuration via environment variables:
- OTEL_SERVICE_NAME: Service identifier
- OTEL_EXPORTER_OTLP_ENDPOINT: Collector endpoint (e.g., http://localhost:4317)
- OTEL_EXPORTER_OTLP_INSECURE: Use insecure connection (true/false)
- OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT: Capture LLM prompts/responses
"""

import logging
import os

from opentelemetry import context as otel_context
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)

# Create resource with service metadata
resource = Resource.create(
    {
        "service.name": os.getenv("OTEL_SERVICE_NAME", "external-webagent-backend"),
        "service.version": os.getenv("APP_VERSION", "1.0.0"),
        "deployment.environment": os.getenv("ENV", "production"),
    }
)

# Create tracer provider
tracer_provider = TracerProvider(resource=resource)

# Configure OTLP exporter (works with ANY OTLP-compatible backend)
otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
otlp_insecure = os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "true").lower() == "true"

otlp_exporter = OTLPSpanExporter(
    endpoint=otlp_endpoint,
    insecure=otlp_insecure,
)


class ConversationSpanProcessor(SpanProcessor):
    """Automatically propagates conversation_id to all spans in a trace.

    This processor reads conversation_id from the OpenTelemetry context and adds it
    as an attribute to every span. This enables querying all spans (including child
    spans like agent_run, tool calls, LLM calls) by conversation_id.
    """

    def on_start(self, span, parent_context=None):
        """Called when span starts - inject conversation_id from context."""
        # Try current context first (works for same-process child spans created by PydanticAI)
        conv_id = otel_context.get_value("conversation_id")

        # Fallback to parent_context (for cross-process propagation via HTTP headers)
        if not conv_id and parent_context:
            conv_id = otel_context.get_value("conversation_id", context=parent_context)

        if conv_id:
            span.set_attribute("conversation_id", conv_id)

    def on_end(self, span):
        """Called when span ends - no action needed."""
        pass

    def shutdown(self):
        """Called on shutdown - no cleanup needed."""
        pass

    def force_flush(self, timeout_millis=None):
        """Force flush - no buffering, return immediately."""
        return True


# Register span processors (order matters: ConversationSpanProcessor runs first)
tracer_provider.add_span_processor(ConversationSpanProcessor())
tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

# Set as global tracer provider
trace.set_tracer_provider(tracer_provider)

# Get tracer for creating spans
tracer = trace.get_tracer(__name__)

# Enable content capture for GenAI instrumentation
os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "true")

logger.info("✓ OpenTelemetry tracing initialized")
logger.info(f"   Service: {resource.attributes['service.name']}")
logger.info(f"   OTLP Endpoint: {otlp_endpoint}")
logger.info("   Backend: Vendor-agnostic (supports Phoenix, Jaeger, Datadog, etc.)")
