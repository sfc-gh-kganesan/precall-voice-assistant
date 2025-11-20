"""
Snowflake Trace Writer Service

Receives OTLP traces over HTTP and writes them to Snowflake.
Acts as a bridge between OpenTelemetry Collector and Snowflake.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any

import snowflake.connector
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from snowflake.connector import SnowflakeConnection

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Snowflake Trace Writer")

# Global Snowflake connection
snowflake_conn: SnowflakeConnection = None


def get_snowflake_connection() -> SnowflakeConnection:
    """Get or create Snowflake connection"""
    global snowflake_conn

    if snowflake_conn is None or snowflake_conn.is_closed():
        snowflake_conn = snowflake.connector.connect(
            user=os.getenv("SNOWFLAKE_USER", "AURA"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
            database=os.getenv("TRACES_DATABASE", "AI_FDE"),
            schema=os.getenv("TRACES_SCHEMA", "CX360_DEMO"),
        )
        logger.info("✓ Connected to Snowflake for trace storage")
        logger.info(f"  Database: {os.getenv('TRACES_DATABASE', 'AI_FDE')}")
        logger.info(f"  Schema: {os.getenv('TRACES_SCHEMA', 'CX360_DEMO')}")

    return snowflake_conn


def parse_otlp_attributes(attributes: list[dict]) -> dict[str, Any]:
    """Parse OTLP key-value attributes to dict"""
    result = {}
    for attr in attributes:
        key = attr.get("key", "")
        value = attr.get("value", {})

        # Extract value based on type
        if "stringValue" in value:
            result[key] = value["stringValue"]
        elif "intValue" in value:
            result[key] = int(value["intValue"])
        elif "doubleValue" in value:
            result[key] = float(value["doubleValue"])
        elif "boolValue" in value:
            result[key] = value["boolValue"]

    return result


def extract_gen_ai_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    """Extract GenAI semantic convention attributes"""
    gen_ai = {}

    # Extract input/output from gen_ai.input.messages / gen_ai.output.messages
    if "gen_ai.input.messages" in attributes:
        try:
            messages = json.loads(attributes["gen_ai.input.messages"])
            if messages and isinstance(messages, list):
                # Extract text from first message
                parts = messages[0].get("parts", [])
                if parts and isinstance(parts, list):
                    gen_ai["input_text"] = parts[0].get("content", "")
        except Exception as e:
            logger.debug(f"Could not parse gen_ai.input.messages: {e}")

    if "gen_ai.output.messages" in attributes:
        try:
            messages = json.loads(attributes["gen_ai.output.messages"])
            if messages and isinstance(messages, list):
                parts = messages[0].get("parts", [])
                if parts and isinstance(parts, list):
                    gen_ai["output_text"] = parts[0].get("content", "")
        except Exception as e:
            logger.debug(f"Could not parse gen_ai.output.messages: {e}")

    # Also check for direct input/output attributes
    if "input" in attributes:
        gen_ai["input_text"] = gen_ai.get("input_text", attributes["input"])
    if "output" in attributes:
        gen_ai["output_text"] = gen_ai.get("output_text", attributes["output"])

    # Model name
    if "gen_ai.request.model" in attributes:
        gen_ai["model_name"] = attributes["gen_ai.request.model"]

    # Token counts
    if "gen_ai.usage.input_tokens" in attributes:
        gen_ai["token_count_input"] = attributes["gen_ai.usage.input_tokens"]
    if "gen_ai.usage.output_tokens" in attributes:
        gen_ai["token_count_output"] = attributes["gen_ai.usage.output_tokens"]

    return gen_ai


def write_span_to_snowflake(span_data: dict[str, Any], resource_attrs: dict[str, Any]) -> None:
    """Write a single span to Snowflake"""
    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()

        # Parse span attributes
        span_attrs = parse_otlp_attributes(span_data.get("attributes", []))
        gen_ai_attrs = extract_gen_ai_attributes(span_attrs)

        # Extract timing
        start_time_ns = int(span_data.get("startTimeUnixNano", 0))
        end_time_ns = int(span_data.get("endTimeUnixNano", 0))
        latency_ms = (end_time_ns - start_time_ns) / 1_000_000  # Convert ns to ms

        # Convert timestamps to Snowflake format
        start_time = datetime.fromtimestamp(start_time_ns / 1_000_000_000)
        end_time = datetime.fromtimestamp(end_time_ns / 1_000_000_000)

        # Extract status
        status = span_data.get("status", {})
        status_code = status.get("code", "UNSET")
        if isinstance(status_code, int):
            # Convert numeric status code to string
            status_mapping = {0: "UNSET", 1: "OK", 2: "ERROR"}
            status_code = status_mapping.get(status_code, str(status_code))
        status_message = status.get("message", "")

        # Trace/span IDs (convert from hex bytes to string)
        trace_id = span_data.get("traceId", "")
        if isinstance(trace_id, bytes):
            trace_id = trace_id.hex()

        span_id = span_data.get("spanId", "")
        if isinstance(span_id, bytes):
            span_id = span_id.hex()

        parent_span_id = span_data.get("parentSpanId", "")
        if isinstance(parent_span_id, bytes):
            parent_span_id = parent_span_id.hex()

        # Span kind (convert numeric to string)
        span_kind = span_data.get("kind", "")
        if isinstance(span_kind, int):
            kind_mapping = {
                0: "UNSPECIFIED",
                1: "INTERNAL",
                2: "SERVER",
                3: "CLIENT",
                4: "PRODUCER",
                5: "CONSUMER",
            }
            span_kind = kind_mapping.get(span_kind, str(span_kind))

        # Insert into Snowflake
        # Use INSERT INTO ... SELECT ... FROM VALUES pattern for VARIANT columns
        # This is required by Snowflake for parameterized queries with semi-structured data
        span_attrs_json = json.dumps(span_attrs)
        resource_attrs_json = json.dumps(resource_attrs)

        insert_sql = """
            INSERT INTO AGENT_TRACES (
                trace_id, span_id, parent_span_id, name, span_kind,
                start_time, end_time, latency_ms,
                status_code, status_message,
                input_text, output_text, model_name,
                token_count_input, token_count_output,
                conversation_id, triggered_by,
                service_name, service_version, deployment_environment,
                span_attributes, resource_attributes
            )
            SELECT
                column1, column2, column3, column4, column5,
                column6, column7, column8,
                column9, column10,
                column11, column12, column13,
                column14, column15,
                column16, column17,
                column18, column19, column20,
                PARSE_JSON(column21), PARSE_JSON(column22)
            FROM VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s, %s,
                %s, %s
            )
        """

        cursor.execute(
            insert_sql,
            (
                trace_id,
                span_id,
                parent_span_id or None,
                span_data.get("name", ""),
                span_kind,
                start_time,
                end_time,
                latency_ms,
                status_code,
                status_message,
                gen_ai_attrs.get("input_text"),
                gen_ai_attrs.get("output_text"),
                gen_ai_attrs.get("model_name"),
                gen_ai_attrs.get("token_count_input"),
                gen_ai_attrs.get("token_count_output"),
                span_attrs.get("conversation_id"),
                span_attrs.get("triggered_by"),
                resource_attrs.get("service.name"),
                resource_attrs.get("service.version"),
                resource_attrs.get("deployment.environment"),
                span_attrs_json,  # JSON string for PARSE_JSON in SELECT
                resource_attrs_json,  # JSON string for PARSE_JSON in SELECT
            ),
        )

        conn.commit()
        cursor.close()

    except Exception as e:
        logger.error(f"Failed to write span to Snowflake: {e}", exc_info=True)
        raise


@app.post("/v1/traces")
async def receive_traces(request: Request):
    """
    Receive OTLP traces over HTTP and write to Snowflake.

    This endpoint accepts OTLP/HTTP format traces from OpenTelemetry Collector.
    """
    try:
        # Parse OTLP payload
        payload = await request.json()

        spans_written = 0

        # OTLP format: resourceSpans[] -> scopeSpans[] -> spans[]
        for resource_span in payload.get("resourceSpans", []):
            resource_attrs = parse_otlp_attributes(
                resource_span.get("resource", {}).get("attributes", [])
            )

            for scope_span in resource_span.get("scopeSpans", []):
                for span in scope_span.get("spans", []):
                    write_span_to_snowflake(span, resource_attrs)
                    spans_written += 1

        logger.info(f"✓ Wrote {spans_written} spans to Snowflake")
        return {"status": "ok", "spans_written": spans_written}

    except Exception as e:
        logger.error(f"Error processing traces: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        conn = get_snowflake_connection()
        return {
            "status": "healthy",
            "snowflake_connected": not conn.is_closed(),
            "database": os.getenv("TRACES_DATABASE", "AI_FDE"),
            "schema": os.getenv("TRACES_SCHEMA", "CX360_DEMO"),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "snowflake_trace_writer:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
    )
