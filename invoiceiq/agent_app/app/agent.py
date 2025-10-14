import os
import logging

from dotenv import load_dotenv
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI


from app.prompts import SYSTEM_MESSAGE
from app.utils import is_running_in_spcs_container, get_spcs_container_token
from app.tools import (
    # get_purchase_order_metadata, # Not implemented yet
    get_invoice_metadata, 
    return_final_result)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


load_dotenv()

class Agent:
    def __init__(self):
        """
        Initialize the Agent with LLM and Python connection.
        """

        self.system_message = SYSTEM_MESSAGE
        self._is_spcs_container = is_running_in_spcs_container()
        self.tools = self.get_tools()
        self.model = self.get_llm()

    def get_llm(self) -> ChatOpenAI:
        """Get the LLM chat object."""

        if self._is_spcs_container:
            snowflake_host = os.getenv('SNOWFLAKE_HOST')
            base_url = f'https://{snowflake_host}/api/v2/cortex/openai'
            api_key = get_spcs_container_token()
            
        else:
            api_key = os.getenv("SNOWFLAKE_PAT")
            # Example SNOWFLAKE_ACCOUNT: pm-fde
            base_url = f"https://{os.getenv("SNOWFLAKE_ACCOUNT")}.snowflakecomputing.com/api/v2/cortex/openai"

        try:
            model = ChatOpenAI(
                model="claude-3-5-sonnet", 
                base_url=base_url,
                temperature=0,
                api_key=api_key)
            
            # Bind tools to the model
            if self.tools:
                model = model.bind_tools(self.tools)
            
            return model
            
        except Exception as e:
            logger.error(f"Failed to get LLM: {str(e)}")
            raise ValueError(f"Failed to get LLM: {str(e)}")

    def get_tools(self) -> list[Tool]:
        """Get the tools."""

        tools = [
            get_invoice_metadata,
            # get_purchase_order_metadata, # Not implemented yet
            return_final_result,
            ]

        return tools