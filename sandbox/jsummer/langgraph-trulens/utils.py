import logging
import sys
from pathlib import Path
import os
from dotenv import load_dotenv

from snowflake.snowpark import Session
from snowflake.telemetry.logs import SnowflakeLogFormatter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry import trace
from snowflake.telemetry.trace import SnowflakeTraceIdGenerator

# Will be used for logging throughou the application for Snowflake event table tracking
application_name = "jsummer-langgraph"
logger = logging.getLogger(application_name)
handler = logging.StreamHandler(stream=sys.stderr)
handler.setFormatter(SnowflakeLogFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO) # INFO by default

# trulens.connectors.snowflake.SnowflakeConnector requires a DATABASE and SCHEMA to be explicitly set either directly or via snowpark session
DATABASE_NAME = "JSUMMER"
SCHEMA_NAME = "SANDBOX"
WAREHOUSE_NAME = "COMPUTE_WH" # Required for Snowpark Connector in TruLens 


def is_running_in_spcs_container() -> bool:
    """
    Check if the application is running inside a Snowflake SPCS (Snowpark Container Services) container.

    Returns
    -------
    bool
        True if running in a Snowflake SPCS container, False otherwise
    """
    token_path = Path("/snowflake/session/token")
    return token_path.exists() and token_path.is_file()


def get_spcs_container_token() -> str:
    """
    Read the OAuth token from the SPCS container environment.

    Returns
    -------
    str
        The OAuth token for SPCS container authentication

    Raises
    ------
    FileNotFoundError
        If the token file is not found
    """
    token_path = Path("/snowflake/session/token")
    try:
        with open(token_path, "r") as f:
            return f.read().strip()
    except Exception as e:
        raise


def get_connection_params() -> dict:
    """
    Get the connection parameters for the Snowflake connection.
    """
    try:
        # Check if running in SPCS container
        is_spcs_container = is_running_in_spcs_container()

        # Get connection parameters based on environment
        if is_spcs_container:
            connection_params = {
                "host": os.getenv("SNOWFLAKE_HOST"),
                "account": os.getenv("SNOWFLAKE_ACCOUNT"),
                "token": get_spcs_container_token(),
                "authenticator": "oauth",
                "database": DATABASE_NAME,
                "schema": SCHEMA_NAME,
                "warehouse": WAREHOUSE_NAME,
            }

        else:
            load_dotenv()
            connection_params = {
                "user": os.getenv("SNOWFLAKE_USER"),
                "password": os.getenv("SNOWFLAKE_PAT"),
                "account": os.getenv("SNOWFLAKE_ACCOUNT"),
                "database": DATABASE_NAME,
                "schema": SCHEMA_NAME,
                "warehouse": WAREHOUSE_NAME,
            }

        return connection_params
    except Exception as e:
        logger.error(f"Failed to get connection parameters: {str(e)}")
        raise


def get_snowpark_session() -> Session:
    """
    Get the Snowpark session.
    """
    try:
        return Session.builder.configs(get_connection_params()).create()
    except Exception as e:
        logger.error(f"Failed to get Snowpark session: {str(e)}")
        raise


def setup_tracing() -> trace.Tracer:
    """
    Initialize OpenTelemetry tracing for the application.
    
    Configures a TracerProvider with Snowflake-compatible trace ID generation.
    When running in SPCS with OTEL_EXPORTER_OTLP_ENDPOINT set, adds an OTLP
    exporter for sending traces to Snowflake's event table.
    
    Returns
    -------
    trace.Tracer
        A configured tracer instance for the application
        
    See Also
    --------
    https://docs.snowflake.com/en/developer-guide/snowpark-container-services/monitoring-services#publishing-and-accessing-application-metrics
    """
    trace_id_generator = SnowflakeTraceIdGenerator()
    tracer_provider = TracerProvider(
        resource=Resource.create({"service.name": application_name}),
        id_generator=trace_id_generator
    )

    # Configure OTLP exporter for Snowflake only when running in SPCS
    # SPCS automatically sets OTEL_EXPORTER_OTLP_TRACES_ENDPOINT which the SDK picks up
    # When not in SPCS, the endpoint is not available and would cause connection errors
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
    if is_running_in_spcs_container() and otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        span_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(span_processor)
        logger.info(f"OTLP exporter configured for SPCS with endpoint: {otlp_endpoint}")
    else:
        logger.info("OTLP exporter not configured - not running in SPCS or OTEL_EXPORTER_OTLP_TRACES_ENDPOINT not set")

    # Set the global tracer provider
    trace.set_tracer_provider(tracer_provider)

    return trace.get_tracer(application_name)


# Initialize tracing at module level so `tracer` is available for import
tracer = setup_tracing()
