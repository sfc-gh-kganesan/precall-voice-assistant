"""
LLM Model wrapper for invoice extraction.
Connects to Snowflake Cortex LLM via OpenAI-compatible API.
"""
import logging
import os
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()
logger = logging.getLogger(__name__)


def is_running_in_spcs_container() -> bool:
    """
    Check if the application is running inside a Snowflake SPCS container.

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
    except Exception:
        raise


class TrackedChatOpenAI(ChatOpenAI):
    """ChatOpenAI subclass that logs token usage and latency."""

    def invoke(self, *args, **kwargs):
        start = time.perf_counter()
        response = super().invoke(*args, **kwargs)
        latency = time.perf_counter() - start
        self._log_usage(response, latency)
        return response

    def _log_usage(self, response, latency_seconds: float) -> None:
        usage = getattr(response, "usage_metadata", None) or {}
        if not usage:
            usage = getattr(response, "response_metadata", {}).get("token_usage", {})
        
        prompt_tokens = (
            usage.get("input_tokens")
            or usage.get("prompt_tokens")
            or 0
        )
        completion_tokens = (
            usage.get("output_tokens")
            or usage.get("completion_tokens")
            or 0
        )
        
        logger.debug(
            f"LLM call: {prompt_tokens} prompt + {completion_tokens} completion tokens, "
            f"{latency_seconds:.2f}s latency"
        )


class CortexModel:
    """
    Snowflake Cortex LLM model for invoice extraction.
    
    Uses Snowflake's Cortex OpenAI-compatible API endpoint.
    
    Environment variables:
    - SNOWFLAKE_PAT: Personal Access Token for authentication (local dev)
    - SNOWFLAKE_ACCOUNT: Snowflake account identifier (e.g., pm-fde)
    - SNOWFLAKE_HOST: Host for SPCS container (auto-detected)
    
    For SPCS container deployment, uses OAuth token from /snowflake/session/token.
    """
    
    DEFAULT_MODEL = "claude-4-sonnet"
    
    def __init__(
        self,
        model_name: str = None,
        temperature: float = 0.0,
        max_tokens: int = 4000,
        json_mode: bool = False,
    ):
        """
        Initialize Cortex Model through OpenAI-compatible API.

        Args:
            model_name: Model to use (default: claude-4-sonnet)
            temperature: Temperature for generation (0.0 for extraction)
            max_tokens: Maximum output tokens
            json_mode: Force JSON-only responses
        """
        self.model_name = model_name or self.DEFAULT_MODEL
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.json_mode = json_mode
        self._is_spcs_container = is_running_in_spcs_container()
        self.model = self._create_model()
    
    def _create_model(self) -> TrackedChatOpenAI:
        """Create the LangChain chat model connected to Cortex."""
        
        if self._is_spcs_container:
            # Running in SPCS container - use OAuth token
            snowflake_host = os.getenv("SNOWFLAKE_HOST")
            if not snowflake_host:
                raise ValueError(
                    "SNOWFLAKE_HOST environment variable required in SPCS container"
                )
            base_url = f"https://{snowflake_host}/api/v2/cortex/openai"
            api_key = get_spcs_container_token()
            logger.info(f"Using SPCS container auth, host: {snowflake_host}")
        else:
            # Local development - use PAT
            api_key = os.getenv("SNOWFLAKE_PAT")
            account = os.getenv("SNOWFLAKE_ACCOUNT")
            
            if not api_key:
                raise ValueError(
                    "SNOWFLAKE_PAT environment variable required. "
                    "Create a PAT in Snowflake: User Menu > Settings > Personal Access Tokens"
                )
            if not account:
                raise ValueError(
                    "SNOWFLAKE_ACCOUNT environment variable required. "
                    "Example: pm-fde"
                )
            
            base_url = f"https://{account}.snowflakecomputing.com/api/v2/cortex/openai"
            logger.info(f"Using Cortex endpoint: {base_url}")
        
        model_kwargs = {}
        if self.json_mode:
            model_kwargs["response_format"] = {"type": "json_object"}
        
        try:
            model = TrackedChatOpenAI(
                model=self.model_name,
                base_url=base_url,
                api_key=api_key,
                request_timeout=180,  # 3 min timeout for large documents
                max_retries=4,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                model_kwargs=model_kwargs,
            )
            
            logger.info(f"Initialized Cortex model: {self.model_name}")
            return model
            
        except Exception as e:
            logger.error(f"Failed to initialize Cortex model: {str(e)}")
            raise ValueError(f"Failed to initialize Cortex model: {str(e)}")
    
    def with_structured_output(self, schema):
        """Get model with structured output for a given schema."""
        return self.model.with_structured_output(schema)


# Alias for backwards compatibility
ExtractionModel = CortexModel
