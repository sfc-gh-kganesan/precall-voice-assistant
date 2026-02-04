"""
P67 Workflow SDK Implementation.

Provides the WorkflowSDK class that workflows use to interact with
Snowflake and external services.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional, TypeVar

from p67_sdk.types import (
    QueryResult,
    HttpResponse,
    CortexAnalystResponse,
    CortexAgentResponse,
    EmailOptions,
)
from p67_sdk.ipc import send_interrupt, wait_for_resume

T = TypeVar('T')


class WorkflowSDK:
    """
    P67 Workflow SDK for Python workflows.
    
    Provides methods to interact with Snowflake, Cortex services,
    and external APIs.
    """
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize the SDK with configuration from the manifest.
        
        Args:
            config: Configuration dict containing snowflakeConfig and parameters
        """
        self._config = config
        self._snowflake_config: Dict[str, Dict[str, Any]] = config.get('snowflakeConfig', {})
        self._parameters: Dict[str, str] = config.get('parameters', {})
        self._connection: Any = None  # Snowflake connection
    
    def _get_config(self, config_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a specific config by name or the only one if not specified.
        
        Args:
            config_name: Optional name of the config to retrieve
            
        Returns:
            The configuration dict
            
        Raises:
            ValueError: If config not found or ambiguous
        """
        if config_name:
            if config_name not in self._snowflake_config:
                raise ValueError(f"Config '{config_name}' not found")
            return self._snowflake_config[config_name]
        
        if len(self._snowflake_config) == 0:
            raise ValueError("No Snowflake configurations available")
        if len(self._snowflake_config) == 1:
            return next(iter(self._snowflake_config.values()))
        raise ValueError(
            "Multiple Snowflake configs found but no config_name provided"
        )
    
    def _normalize_access_url(self, access_url: Optional[str]) -> Optional[str]:
        """
        Normalize accessUrl to ensure it has the https:// protocol.
        
        Args:
            access_url: The raw access URL
            
        Returns:
            URL with https:// protocol prefix
        """
        if not access_url:
            return None
        if access_url.startswith('https://') or access_url.startswith('http://'):
            return access_url
        return f"https://{access_url}"
    
    def _get_connection(self, config_name: Optional[str] = None) -> Any:
        """
        Get or create a Snowflake connection.
        
        Args:
            config_name: Optional name of the config to use
            
        Returns:
            Snowflake connection object
        """
        if self._connection is not None:
            return self._connection
        
        try:
            import snowflake.connector
        except ImportError:
            raise ImportError(
                "snowflake-connector-python is required. "
                "Install with: pip install snowflake-connector-python"
            )
        
        cfg = self._get_config(config_name)
        
        connect_params: Dict[str, Any] = {
            'account': cfg.get('account'),
            'user': cfg.get('username'),
            'warehouse': cfg.get('warehouse'),
            'database': cfg.get('database'),
            'schema': cfg.get('schema'),
        }
        
        # Use accessUrl to set the host if provided
        # The Python connector needs the host parameter for custom hostnames
        access_url = cfg.get('accessUrl')
        if access_url:
            # Strip protocol if present
            if access_url.startswith('https://'):
                access_url = access_url[8:]
            elif access_url.startswith('http://'):
                access_url = access_url[7:]
            connect_params['host'] = access_url
        
        # Handle authentication
        if cfg.get('token'):
            connect_params['token'] = cfg.get('token')
            connect_params['authenticator'] = 'oauth'
        elif cfg.get('password'):
            connect_params['password'] = cfg.get('password')
        
        if cfg.get('authenticator'):
            connect_params['authenticator'] = cfg.get('authenticator')
        
        self._connection = snowflake.connector.connect(**connect_params)
        return self._connection
    
    def get_parameter(self, name: str, config_name: Optional[str] = None) -> str:
        """
        Get a parameter value from the manifest configuration.
        
        Args:
            name: The name of the parameter
            config_name: Optional name of the config to use
            
        Returns:
            The parameter value
            
        Raises:
            KeyError: If the parameter is not found
        """
        # First check the global parameters from the runner
        if name in self._parameters:
            return self._parameters[name]
        
        # Then check config-specific parameters
        cfg = self._get_config(config_name)
        params = cfg.get('parameters', {})
        if name not in params:
            raise KeyError(f"Parameter '{name}' not found")
        return params[name]
    
    def get_parameters(self, config_name: Optional[str] = None) -> Dict[str, str]:
        """
        Get all parameters from the manifest configuration.
        
        Args:
            config_name: Optional name of the config to use
            
        Returns:
            Dict of parameter name to value
        """
        cfg = self._get_config(config_name)
        result = dict(cfg.get('parameters', {}))
        # Merge with global parameters (global takes precedence)
        result.update(self._parameters)
        return result
    
    def execute_query_read_only(
        self,
        sql_text: str,
        binds: Optional[List[Any]] = None,
        config_name: Optional[str] = None,
    ) -> QueryResult:
        """
        Execute a read-only SQL query against Snowflake.
        
        Only SELECT, WITH, SHOW, and DESCRIBE statements are allowed.
        
        Args:
            sql_text: The SQL query to execute
            binds: Optional list of bind parameters
            config_name: Optional name of the config to use
            
        Returns:
            QueryResult with statement and rows
            
        Raises:
            ValueError: If the query is not read-only
        """
        # Validate query is read-only
        stripped = sql_text.strip()
        # Remove comments
        lines = [l for l in stripped.split('\n') if not l.strip().startswith('--')]
        cleaned = ' '.join(lines)
        
        first_word = cleaned.split()[0].upper() if cleaned.split() else ''
        if first_word not in ('SELECT', 'WITH', 'SHOW', 'DESCRIBE', 'DESC'):
            raise ValueError(
                "Only SELECT queries are allowed. "
                "DML and DDL statements are not permitted."
            )
        
        if ';' in cleaned:
            raise ValueError(
                "Multiple statements are not allowed. "
                "Only single SELECT queries are permitted."
            )
        
        conn = self._get_connection(config_name)
        cursor = conn.cursor()
        try:
            cursor.execute(sql_text, binds or [])
            rows = cursor.fetchall()
            return QueryResult(statement=cursor, rows=list(rows))
        finally:
            cursor.close()
    
    def query_cortex_analyst(
        self,
        question: str,
        semantic_model: Optional[str] = None,
        config_name: Optional[str] = None,
    ) -> CortexAnalystResponse:
        """
        Query Cortex Analyst with a natural language question.
        
        Args:
            question: Natural language question to ask
            semantic_model: Path to semantic model file
            config_name: Optional name of the config to use
            
        Returns:
            CortexAnalystResponse with success status and data or error
        """
        cfg = self._get_config(config_name)
        
        try:
            model = semantic_model
            if not model:
                raise ValueError(
                    "semantic_model is required for Cortex Analyst queries"
                )
            
            token = cfg.get('token')
            access_url = self._normalize_access_url(cfg.get('accessUrl'))
            
            if not token or not access_url:
                raise ValueError(
                    "token and accessUrl are required in config for Cortex Analyst"
                )
            
            url = f"{access_url}/api/v2/cortex/analyst/message"
            
            payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": question}],
                    }
                ],
                "semantic_model_file": model,
            }
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers, method='POST')
            
            with urllib.request.urlopen(req, timeout=180) as resp:
                response_data = json.loads(resp.read().decode('utf-8'))
                return CortexAnalystResponse(success=True, data=response_data)
                
        except Exception as e:
            return CortexAnalystResponse(success=False, error=str(e))
    
    def call_cortex_agent(
        self,
        question: str,
        options: Optional[Dict[str, Any]] = None,
        config_name: Optional[str] = None,
    ) -> CortexAgentResponse:
        """
        Call a Cortex Agent with a question.
        
        Args:
            question: Question or message to send to the agent
            options: Configuration options (agentDatabase, agentSchema, agentName, etc.)
            config_name: Optional name of the config to use
            
        Returns:
            CortexAgentResponse with success status and data or error
        """
        cfg = self._get_config(config_name)
        options = options or {}
        
        try:
            database = options.get('agentDatabase') or cfg.get('database')
            schema = options.get('agentSchema') or cfg.get('schema')
            name = options.get('agentName')
            parent_message_id = options.get('parentMessageId', '0')
            
            if not all([database, schema, name]):
                raise ValueError(
                    "agentDatabase, agentSchema, and agentName are required"
                )
            
            token = cfg.get('token')
            access_url = self._normalize_access_url(cfg.get('accessUrl'))
            
            if not token or not access_url:
                raise ValueError(
                    "token and accessUrl are required in config for Cortex Agent"
                )
            
            url = f"{access_url}/api/v2/databases/{database}/schemas/{schema}/agents/{name}:run"
            
            payload = {
                "parent_message_id": parent_message_id,
                "messages": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": question}],
                    }
                ],
            }
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers, method='POST')
            
            with urllib.request.urlopen(req, timeout=120) as resp:
                # Handle streaming response (simplified - just get final result)
                response_text = resp.read().decode('utf-8')
                
                # Parse SSE events to find the final response
                final_content = None
                for line in response_text.split('\n'):
                    if line.startswith('data: ') and line != 'data: [DONE]':
                        try:
                            event_data = json.loads(line[6:])
                            if event_data.get('content'):
                                final_content = event_data.get('content')
                        except json.JSONDecodeError:
                            pass
                
                return CortexAgentResponse(
                    success=True,
                    status_code=200,
                    data={"message": {"role": "agent", "content": final_content}},
                )
                
        except urllib.error.HTTPError as e:
            return CortexAgentResponse(
                success=False,
                status_code=e.code,
                error=str(e),
            )
        except Exception as e:
            return CortexAgentResponse(
                success=False,
                status_code=0,
                error=str(e),
            )
    
    def email(
        self,
        options: Dict[str, Any],
        config_name: Optional[str] = None,
    ) -> bool:
        """
        Send an email using Snowflake Email Integration.
        
        Args:
            options: Email options (email_addresses, subject, body, etc.)
            config_name: Optional name of the config to use
            
        Returns:
            True if email was sent successfully
        """
        cfg = self._get_config(config_name)
        
        integration_name = options.get('integration_name')
        if not integration_name:
            integration_name = cfg.get('email_integration')
        
        if not integration_name:
            raise ValueError(
                "integration_name is required in options or config"
            )
        
        conn = self._get_connection(config_name)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "CALL SYSTEM$SEND_EMAIL(?, ?, ?, ?, ?)",
                [
                    integration_name,
                    ','.join(options.get('email_addresses', [])),
                    options.get('subject', ''),
                    options.get('body', ''),
                    options.get('content_type', 'text/plain'),
                ]
            )
            return True
        except Exception:
            return False
        finally:
            cursor.close()
    
    def http_request(self, options: Dict[str, Any]) -> HttpResponse:
        """
        Make an HTTP request to an external service.
        
        Args:
            options: Request options (url, method, headers, body, timeout)
            
        Returns:
            HttpResponse with success status, status code, headers, and data
        """
        url = options.get('url')
        if not url:
            return HttpResponse(
                success=False,
                status=0,
                headers={},
                error="url is required",
            )
        
        method = options.get('method', 'GET')
        headers = options.get('headers', {})
        body = options.get('body')
        timeout = options.get('timeout', 30000) / 1000  # Convert ms to seconds
        
        # Prepare request data
        data = None
        if body is not None:
            if isinstance(body, (dict, list)):
                data = json.dumps(body).encode('utf-8')
                if 'Content-Type' not in headers:
                    headers['Content-Type'] = 'application/json'
            elif isinstance(body, str):
                data = body.encode('utf-8')
            elif isinstance(body, bytes):
                data = body
        
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                response_data = resp.read().decode('utf-8')
                
                # Try to parse as JSON
                try:
                    response_data = json.loads(response_data)
                except json.JSONDecodeError:
                    pass
                
                return HttpResponse(
                    success=True,
                    status=resp.status,
                    headers=dict(resp.headers),
                    data=response_data,
                )
        except urllib.error.HTTPError as e:
            error_body = None
            try:
                error_body = e.read().decode('utf-8')
            except Exception:
                pass
            return HttpResponse(
                success=False,
                status=e.code,
                headers=dict(e.headers) if e.headers else {},
                error=error_body or str(e),
            )
        except Exception as e:
            return HttpResponse(
                success=False,
                status=0,
                headers={},
                error=str(e),
            )
    
    def interrupt(
        self,
        payload: Any,
        options: Optional[Dict[str, Any]] = None,
    ) -> T:
        """
        Pause workflow execution and wait for human input.
        
        The payload is surfaced to callers who can then provide a response
        via the controld API. Execution resumes when a response is provided.
        
        Args:
            payload: JSON-serializable value to surface (question, form data, etc.)
            options: Optional configuration (timeout in ms, nodeId)
            
        Returns:
            The response provided by the human
            
        Raises:
            TimeoutError: If timeout is reached (when specified)
        """
        options = options or {}
        node_id = options.get('nodeId')
        timeout_ms = options.get('timeout')
        
        # Send interrupt and get ID
        interrupt_id = send_interrupt(payload, node_id)
        
        # Wait for resume with optional timeout
        timeout_sec = timeout_ms / 1000 if timeout_ms else None
        response = wait_for_resume(interrupt_id, timeout_sec)
        
        return response  # type: ignore
    
    def close(self) -> None:
        """
        Close the Snowflake connection.
        
        Call this when done to properly release resources.
        """
        if self._connection is not None:
            try:
                self._connection.close()
            except Exception:
                pass
            self._connection = None
