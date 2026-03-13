"""
P67 Workflow SDK Interface.

This is a stub file for IDE support only. It contains type signatures
and docstrings but no implementation. The actual implementation is
bundled at build time by 'p67 build'.
"""

from typing import Any, Dict, List, Optional, TypeVar

from p67_sdk.types import (
    QueryResult,
    HttpResponse,
    CortexAnalystResponse,
    CortexAgentResponse,
    CortexCodeOptions,
    CortexCodeResponse,
)

T = TypeVar('T')


class WorkflowSDK:
    """
    P67 Workflow SDK for Python workflows.

    Provides methods to interact with Snowflake, Cortex services,
    and external APIs.

    Example:
        ```python
        def main(sdk: WorkflowSDK) -> dict:
            # Query Snowflake
            result = sdk.execute_query_read_only("SELECT * FROM my_table LIMIT 10")

            # Use Cortex Analyst
            analysis = sdk.query_cortex_analyst(
                "What were total sales last month?",
                semantic_model="@my_db.my_schema.my_stage/model.yaml"
            )

            return {"rows": len(result.rows), "analysis": analysis.data}
        ```
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize the SDK with configuration from the manifest.

        Note: You don't need to call this directly. The SDK instance
        is created and passed to your main() function automatically.

        Args:
            config: Configuration dict containing snowflakeConfig and parameters
        """
        ...

    def get_parameter(self, name: str, config_name: Optional[str] = None) -> str:
        """
        Get a parameter value from the manifest configuration.

        Parameters are defined in manifest.yaml under the 'parameters' key.

        Args:
            name: The name of the parameter
            config_name: Optional name of the config to use (for multi-config setups)

        Returns:
            The parameter value as a string

        Raises:
            KeyError: If the parameter is not found

        Example:
            ```python
            api_key = sdk.get_parameter("API_KEY")
            threshold = int(sdk.get_parameter("THRESHOLD"))
            ```
        """
        ...

    def get_parameters(self, config_name: Optional[str] = None) -> Dict[str, str]:
        """
        Get all parameters from the manifest configuration.

        Args:
            config_name: Optional name of the config to use

        Returns:
            Dict mapping parameter names to values

        Example:
            ```python
            params = sdk.get_parameters()
            for key, value in params.items():
                print(f"{key}={value}")
            ```
        """
        ...

    def execute_query_read_only(
        self,
        sql_text: str,
        binds: Optional[List[Any]] = None,
        config_name: Optional[str] = None,
    ) -> QueryResult:
        """
        Execute a read-only SQL query against Snowflake.

        Only SELECT, WITH, SHOW, and DESCRIBE statements are allowed.
        DML (INSERT, UPDATE, DELETE) and DDL statements will raise an error.

        Args:
            sql_text: The SQL query to execute
            binds: Optional list of bind parameters for parameterized queries
            config_name: Optional name of the config to use

        Returns:
            QueryResult with:
                - statement: The cursor object
                - rows: List of result rows

        Raises:
            ValueError: If the query is not read-only or contains multiple statements

        Example:
            ```python
            # Simple query
            result = sdk.execute_query_read_only("SELECT * FROM users LIMIT 10")
            for row in result.rows:
                print(row)

            # Parameterized query
            result = sdk.execute_query_read_only(
                "SELECT * FROM orders WHERE customer_id = %s",
                binds=[customer_id]
            )
            ```
        """
        ...

    def query_cortex_analyst(
        self,
        question: str,
        semantic_model: Optional[str] = None,
        config_name: Optional[str] = None,
    ) -> CortexAnalystResponse:
        """
        Query Cortex Analyst with a natural language question.

        Cortex Analyst uses a semantic model to understand your data
        and generate SQL to answer questions.

        Args:
            question: Natural language question to ask
            semantic_model: Path to semantic model file (e.g., "@db.schema.stage/model.yaml")
            config_name: Optional name of the config to use

        Returns:
            CortexAnalystResponse with:
                - success: Whether the query succeeded
                - data: Response data including generated SQL and results
                - error: Error message if failed

        Example:
            ```python
            response = sdk.query_cortex_analyst(
                "What were total sales by region last quarter?",
                semantic_model="@analytics.models.stage/sales_model.yaml"
            )
            if response.success:
                print(response.data)
            else:
                print(f"Error: {response.error}")
            ```
        """
        ...

    def call_cortex_agent(
        self,
        question: str,
        options: Optional[Dict[str, Any]] = None,
        config_name: Optional[str] = None,
    ) -> CortexAgentResponse:
        """
        Call a Cortex Agent with a question.

        Cortex Agents are AI assistants that can answer questions,
        perform tasks, and interact with your data.

        Args:
            question: Question or message to send to the agent
            options: Configuration options:
                - agentDatabase: Database containing the agent
                - agentSchema: Schema containing the agent
                - agentName: Name of the agent
                - parentMessageId: For conversation continuity
            config_name: Optional name of the config to use

        Returns:
            CortexAgentResponse with:
                - success: Whether the call succeeded
                - status_code: HTTP status code
                - data: Response containing the agent's message
                - error: Error message if failed

        Example:
            ```python
            response = sdk.call_cortex_agent(
                "Summarize our Q4 performance",
                options={
                    "agentDatabase": "ANALYTICS",
                    "agentSchema": "AGENTS",
                    "agentName": "SALES_ASSISTANT"
                }
            )
            if response.success:
                print(response.data["message"]["content"])
            ```
        """
        ...

    def email(
        self,
        options: Dict[str, Any],
        config_name: Optional[str] = None,
    ) -> bool:
        """
        Send an email using Snowflake Email Integration.

        Requires a configured email integration in your Snowflake account.

        Args:
            options: Email options:
                - email_addresses: List of recipient addresses
                - subject: Email subject
                - body: Email body content
                - content_type: "text/plain" or "text/html" (default: "text/plain")
                - integration_name: Email integration name (optional if in config)
            config_name: Optional name of the config to use

        Returns:
            True if email was sent successfully, False otherwise

        Example:
            ```python
            success = sdk.email({
                "email_addresses": ["user@example.com"],
                "subject": "Workflow Report",
                "body": "Your daily report is ready.",
                "integration_name": "my_email_integration"
            })
            ```
        """
        ...

    def http_request(self, options: Dict[str, Any]) -> HttpResponse:
        """
        Make an HTTP request to an external service.

        Args:
            options: Request options:
                - url: The URL to request (required)
                - method: HTTP method (default: "GET")
                - headers: Dict of request headers
                - body: Request body (dict/list auto-encoded as JSON)
                - timeout: Timeout in milliseconds (default: 30000)

        Returns:
            HttpResponse with:
                - success: Whether request succeeded
                - status: HTTP status code
                - headers: Response headers
                - data: Response body (parsed as JSON if applicable)
                - error: Error message if failed

        Example:
            ```python
            response = sdk.http_request({
                "url": "https://api.example.com/data",
                "method": "POST",
                "headers": {"Authorization": "Bearer token"},
                "body": {"query": "test"}
            })
            if response.success:
                print(response.data)
            ```
        """
        ...

    def interrupt(
        self,
        payload: Any,
        options: Optional[Dict[str, Any]] = None,
    ) -> T:
        """
        Pause workflow execution and wait for human input.

        The workflow will pause and the payload will be surfaced to
        callers (e.g., a UI). Execution resumes when a response is
        provided via the API.

        Args:
            payload: JSON-serializable value to surface (question, form, etc.)
            options: Optional configuration:
                - timeout: Timeout in milliseconds (None = wait indefinitely)
                - nodeId: Optional node identifier

        Returns:
            The response provided by the human/caller

        Raises:
            TimeoutError: If timeout is reached

        Example:
            ```python
            # Ask for approval
            approved = sdk.interrupt({
                "type": "approval",
                "message": "Proceed with data export?",
                "options": ["yes", "no"]
            })

            if approved == "yes":
                # Continue with export
                pass
            ```
        """
        ...

    def cortex_code(
        self,
        options: CortexCodeOptions,
    ) -> CortexCodeResponse:
        """
        Invoke the Cortex Code CLI to perform agentic coding tasks.

        Runs the ``cortex`` CLI as a subprocess with the given prompt and
        returns the output. Cortex Code is an AI coding agent that can
        read/write files, run commands, search code, and interact with
        Snowflake.

        Args:
            options: CortexCodeOptions containing:
                - prompt: The prompt/instruction to send (required)
                - timeout: Timeout in seconds (default 900 = 15 min)
                - work_dir: Working directory for the process
                - model: Model to use (e.g., 'opus', 'sonnet')
                - allow_all_tool_calls: Skip tool-call confirmations (default False)

        Returns:
            CortexCodeResponse with:
                - success: Whether the invocation succeeded
                - output: Standard output from the cortex process
                - error: Error message if failed
                - exit_code: Process exit code

        Example:
            ```python
            from p67_sdk.types import CortexCodeOptions

            response = sdk.cortex_code(CortexCodeOptions(
                prompt='Read data.csv and summarize the contents.',
                timeout=300,
            ))
            if response.success:
                print(response.output)
            else:
                print(f"Error: {response.error}")
            ```
        """
        ...

    def close(self) -> None:
        """
        Close the Snowflake connection.

        Call this when done to properly release resources.
        Note: This is called automatically when the workflow completes.

        Example:
            ```python
            try:
                result = sdk.execute_query_read_only("SELECT 1")
            finally:
                sdk.close()
            ```
        """
        ...
