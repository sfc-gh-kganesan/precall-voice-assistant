/**
 * OpenTelemetry Configuration - Vendor Agnostic
 *
 * Uses pure OpenTelemetry APIs to support ANY observability backend that
 * supports OTLP (OpenTelemetry Protocol): Phoenix, Jaeger, Tempo, Datadog,
 * New Relic, Honeycomb, etc.
 *
 * Configuration via environment variables (.env):
 * - VITE_OTEL_SERVICE_NAME: Service identifier
 * - VITE_OTEL_EXPORTER_OTLP_ENDPOINT: Collector HTTP endpoint
 */

import { WebTracerProvider } from '@opentelemetry/sdk-trace-web';
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-base';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { Resource } from '@opentelemetry/resources';
import { ATTR_SERVICE_NAME, ATTR_SERVICE_VERSION } from '@opentelemetry/semantic-conventions';
import { registerInstrumentations } from '@opentelemetry/instrumentation';
import { FetchInstrumentation } from '@opentelemetry/instrumentation-fetch';
import { trace } from '@opentelemetry/api';

// Create resource with service metadata
const resource = Resource.default().merge(
  new Resource({
    [ATTR_SERVICE_NAME]: import.meta.env.VITE_OTEL_SERVICE_NAME || 'external-webagent-voice',
    [ATTR_SERVICE_VERSION]: import.meta.env.VITE_APP_VERSION || '1.0.0',
  })
);

// Create tracer provider
export const provider = new WebTracerProvider({ resource });

// Configure OTLP exporter (works with ANY OTLP-compatible backend)
const otlpEndpoint = import.meta.env.VITE_OTEL_EXPORTER_OTLP_ENDPOINT || 'http://localhost:4318/v1/traces';

const exporter = new OTLPTraceExporter({
  url: otlpEndpoint,
});

// Use BatchSpanProcessor for better performance
provider.addSpanProcessor(new BatchSpanProcessor(exporter));

// Register provider globally
provider.register();

// Auto-instrument fetch API for HTTP calls
registerInstrumentations({
  instrumentations: [
    new FetchInstrumentation({
      propagateTraceHeaderCorsUrls: [
        /.*/,  // Propagate trace context to all origins
      ],
      clearTimingResources: true,
    }),
  ],
});

// Get tracer for creating spans
export const tracer = trace.getTracer('webagent-voice');

console.log('✓ OpenTelemetry tracing initialized for voice agent');
console.log(`   Service: ${resource.attributes[ATTR_SERVICE_NAME]}`);
console.log(`   OTLP Endpoint: ${otlpEndpoint}`);
console.log('   Backend: Vendor-agnostic (supports Phoenix, Jaeger, Datadog, etc.)');
