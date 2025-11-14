import os
import logging

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from app.utils import is_running_in_spcs_container, get_spcs_container_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


class CortexModel:
    def __init__(
        self,
        model_name: str = "claude-3-5-sonnet",
        temperature: float = 0.0,
        max_tokens: int = 2000,
    ):
        """
        Initialize Cortex Model through OpenAI-API.

        Args:
            model_name: Model to use (default: claude-3-5-sonnet)
            temperature: Temperature for generation (0.0-0.2 for extraction, default: 0.0)
            max_tokens: Maximum output tokens (default: 2000 for structured extraction)
        """

        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._is_spcs_container = is_running_in_spcs_container()
        self.model = self.get_llm()

    def get_llm(self) -> ChatOpenAI:
        """Get the LLM chat object."""

        if self._is_spcs_container:
            snowflake_host = os.getenv("SNOWFLAKE_HOST")
            base_url = f"https://{snowflake_host}/api/v2/cortex/openai"
            api_key = get_spcs_container_token()

        else:
            api_key = os.getenv("SNOWFLAKE_PAT")
            # Example SNOWFLAKE_ACCOUNT: pm-fde
            base_url = f"https://{os.getenv('SNOWFLAKE_ACCOUNT')}.snowflakecomputing.com/api/v2/cortex/openai"

        try:
            model = ChatOpenAI(
                model=self.model_name,
                base_url=base_url,
                request_timeout=30,
                max_retries=4,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                # Note: JSON enforcement removed from base model
                # Will be added via structured_output when needed
                # include_response_headers = True, # Allows us to capture the Snowflake request ID for debugging
                api_key=api_key,
            )

            return model

        except Exception as e:
            logger.error(f"Failed to get LLM: {str(e)}")
            raise ValueError(f"Failed to get LLM: {str(e)}")
