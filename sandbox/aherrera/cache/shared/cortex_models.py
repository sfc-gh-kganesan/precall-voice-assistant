"""Wrappers for Snowflake Cortex LLM, Agent, and Analyst APIs.

This module provides unified interfaces for:
- Cortex LLM: OpenAI-compatible API (based on jsummer pattern)
- Cortex Agent: REST API with planning and orchestration
- Cortex Analyst: Text-to-SQL with semantic models
"""
import os
import logging
import httpx
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from shared.utils import is_running_in_spcs_container, get_spcs_container_token, application_name

logger = logging.getLogger(application_name)
load_dotenv()


class CortexLLM:
    """Wrapper for Cortex LLM via OpenAI-compatible API.

    Based on jsummer/langgraph-trulens pattern.
    """

    def __init__(self, model_name: str = "claude-3-5-sonnet"):
        """Initialize Cortex LLM model.

        Args:
            model_name: Model to use (default: claude-3-5-sonnet)
        """
        self.model_name = model_name
        self._is_spcs_container = is_running_in_spcs_container()
        self.model = self.get_llm()

    def get_llm(self) -> ChatOpenAI:
        """Get the LLM chat object."""
        if self._is_spcs_container:
            snowflake_host = os.getenv('SNOWFLAKE_HOST')
            base_url = f'https://{snowflake_host}/api/v2/cortex/openai'
            api_key = get_spcs_container_token()
        else:
            api_key = os.getenv("SNOWFLAKE_PAT")
            base_url = f"https://{os.getenv('SNOWFLAKE_ACCOUNT')}.snowflakecomputing.com/api/v2/cortex/openai"

        try:
            model = ChatOpenAI(
                model=self.model_name,
                base_url=base_url,
                request_timeout=30,
                max_retries=4,
                temperature=0,
                api_key=api_key
            )
            logger.info(f"Cortex LLM initialized: {model.model_name}")
            return model
        except Exception as e:
            logger.error(f"Failed to initialize Cortex LLM: {str(e)}")
            raise ValueError(f"Failed to initialize Cortex LLM: {str(e)}")


class CortexAgent:
    """Wrapper for Cortex Agent REST API.

    Provides agent orchestration with planning, tools (Analyst, Search), and reflection.
    Docs: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents
    """

    def __init__(
        self,
        model_name: str = "auto",
        instructions: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None
    ):
        """Initialize Cortex Agent.

        Args:
            model_name: Model to use (default: 'auto' for best available)
            instructions: Agent system instructions
            tools: List of tool configurations (Analyst, Search, UDFs)
        """
        self.model_name = model_name
        self.instructions = instructions or "You are a helpful AI assistant."
        self.tools = tools or []
        self._is_spcs_container = is_running_in_spcs_container()
        self.base_url = self._get_base_url()
        self.headers = self._get_headers()

    def _get_base_url(self) -> str:
        """Get Cortex Agent API base URL."""
        if self._is_spcs_container:
            snowflake_host = os.getenv('SNOWFLAKE_HOST')
            return f'https://{snowflake_host}/api/v2/cortex'
        else:
            account = os.getenv('SNOWFLAKE_ACCOUNT')
            return f"https://{account}.snowflakecomputing.com/api/v2/cortex"

    def _get_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        if self._is_spcs_container:
            token = get_spcs_container_token()
        else:
            token = os.getenv("SNOWFLAKE_PAT")

        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def send_message(
        self,
        message: str,
        thread_id: Optional[str] = None,
        agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a message to Cortex Agent.

        Args:
            message: User message
            thread_id: Optional thread ID for multi-turn conversations
            agent_id: Optional agent ID (if using pre-configured agent)

        Returns:
            Agent response including planning, tool calls, and final answer
        """
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": message}]
                }
            ],
            "model": self.model_name
        }

        # Add agent configuration if not using pre-configured agent
        if not agent_id:
            payload["instructions"] = self.instructions
            if self.tools:
                payload["tools"] = self.tools

        # Add thread_id for multi-turn
        if thread_id:
            payload["thread_id"] = thread_id

        try:
            endpoint = f"{self.base_url}/agents/{agent_id}/messages" if agent_id else f"{self.base_url}/agents/messages"

            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    endpoint,
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()
                result = response.json()

                logger.info(f"Cortex Agent response received")
                return result

        except httpx.HTTPError as e:
            logger.error(f"Cortex Agent API error: {str(e)}")
            raise ValueError(f"Cortex Agent API error: {str(e)}")


class CortexAnalyst:
    """Wrapper for Cortex Analyst REST API.

    Provides text-to-SQL capabilities with semantic models.
    Docs: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst
    """

    def __init__(self, semantic_model_file: str):
        """Initialize Cortex Analyst.

        Args:
            semantic_model_file: Path to semantic model YAML (e.g., '@stage/model.yaml')
        """
        self.semantic_model_file = semantic_model_file
        self._is_spcs_container = is_running_in_spcs_container()
        self.base_url = self._get_base_url()
        self.headers = self._get_headers()

    def _get_base_url(self) -> str:
        """Get Cortex Analyst API base URL."""
        if self._is_spcs_container:
            snowflake_host = os.getenv('SNOWFLAKE_HOST')
            return f'https://{snowflake_host}/api/v2/cortex/analyst'
        else:
            account = os.getenv('SNOWFLAKE_ACCOUNT')
            return f"https://{account}.snowflakecomputing.com/api/v2/cortex/analyst"

    def _get_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        if self._is_spcs_container:
            token = get_spcs_container_token()
        else:
            token = os.getenv("SNOWFLAKE_PAT")

        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def query(
        self,
        question: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Ask a natural language question about structured data.

        Args:
            question: Natural language question
            conversation_history: Previous messages for multi-turn conversations

        Returns:
            Response with generated SQL, results, and interpretation
        """
        messages = conversation_history or []
        messages.append({
            "role": "user",
            "content": [{"type": "text", "text": question}]
        })

        payload = {
            "messages": messages,
            "semantic_model_file": self.semantic_model_file
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.base_url}/message",
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()
                result = response.json()

                logger.info(f"Cortex Analyst response received")
                return result

        except httpx.HTTPError as e:
            logger.error(f"Cortex Analyst API error: {str(e)}")
            raise ValueError(f"Cortex Analyst API error: {str(e)}")
