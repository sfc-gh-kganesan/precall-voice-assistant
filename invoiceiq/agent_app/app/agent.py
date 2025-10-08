import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from snowflake.connector import connect

from .prompts import SYSTEM_MESSAGE
from .utils import get_spcs_container_token, is_running_in_spcs_container


load_dotenv()

class Agent:
    def __init__(self):
        """
        Initialize the Agent with LLM and Python connection.
        """

        self.system_message = SYSTEM_MESSAGE
        self._is_spcs_container = is_running_in_spcs_container()
        self.model = self.get_llm()
        self.python_connection = self.get_persistent_connection()
        self.tools = self.get_tools()

    def get_llm(self):
        """Get the LLM."""


        if self._is_spcs_container:
            # api_key = get_spcs_container_token() # NOT CURRENTLY WORKING
            api_key = os.getenv("SNOWFLAKE_PAT")
            # Example SNOWFLAKE_HOST: "ssb77620.prod3.us-west-2.aws.snowflakecomputing.com"
            base_url = f"https://{os.getenv("SNOWFLAKE_HOST")}/api/v2/cortex/openai/chat/completions"

        else:
            api_key = os.getenv("SNOWFLAKE_PAT")
            # Example SNOWFLAKE_ACCOUNT: pm-fde
            base_url = f"https://{os.getenv("SNOWFLAKE_ACCOUNT")}.snowflakecomputing.com/api/v2/cortex/openai"

        if not api_key:
            raise ValueError("API key is not set")

        try:

            return ChatOpenAI(
                model="claude-3-5-sonnet", 
                base_url=base_url,
                temperature=0,
                api_key=api_key)
        except Exception as e:
            raise ValueError(f"Failed to get LLM: {str(e)}")

    def get_tools(self):
        """Get the tools."""

        tools = []
        return tools

    def get_persistent_connection(self):
        """
        Get a persistent Snowflake connection.

        This method creates a connection that will be kept alive and should be
        explicitly closed when no longer needed.

        Parameters
        ----------

        Returns
        -------
        connection
            A Snowflake connection object
        """
        try:

            # Get connection parameters based on environment
            if self._is_spcs_container:
                connection_params = {
                    "host": os.getenv("SNOWFLAKE_HOST"),
                    "account": os.getenv("SNOWFLAKE_ACCOUNT"),
                    "token": get_spcs_container_token(),
                    "authenticator": "oauth",
                }

            else:

                connection_params = {
                    "user": os.getenv("SNOWFLAKE_USER"),
                    "password": os.getenv("SNOWFLAKE_PAT"),
                    "account": os.getenv("SNOWFLAKE_ACCOUNT"),
                }

            connection = connect(
                **connection_params,
                # client_session_keep_alive=True,
            )

            return connection

        except Exception as e:
            raise