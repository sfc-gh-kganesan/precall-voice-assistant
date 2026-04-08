"""
P67 Workflow SDK Implementation.

Provides the WorkflowSDK class that workflows use to interact with
Snowflake and external services.
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import tempfile
import urllib.request
import urllib.error
from typing import Any, Dict, Iterator, List, Optional, TypeVar
from urllib.parse import quote

from p67_sdk.types import (
    QueryResult,
    HttpResponse,
    CortexAnalystResponse,
    CortexAgentResponse,
    EmailOptions,
    CortexCompleteOptions,
    CortexCompleteResponse,
    CortexCompleteRequestInfo,
    CortexChoice,
    CortexChoiceMessage,
    CortexTokenUsage,
    CortexToolCall,
    CortexToolCallFunction,
    CortexStreamChunk,
    CortexStreamChoice,
    CortexStreamDelta,
    CortexStreamDeltaToolCall,
    CortexStreamDeltaToolCallFunction,
    SubworkflowOptions,
    SubworkflowResponse,
    CortexCodeOptions,
    CortexCodeResponse,
)
from p67_sdk.ipc import send_interrupt, wait_for_resume

T = TypeVar('T')


def _to_camel_case(s: str) -> str:
    parts = s.split('_')
    return parts[0] + ''.join(p.title() for p in parts[1:])


def _camel_case_dict(obj: Any) -> Any:
    """Recursively convert snake_case dict keys to camelCase, dropping None values."""
    if isinstance(obj, dict):
        return {_to_camel_case(k): _camel_case_dict(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_camel_case_dict(item) for item in obj]
    return obj


def _serialize_notify(notify: Any) -> Optional[Dict[str, Any]]:
    """Convert a SlackNotifyConfig dataclass or dict to a camelCase dict for IPC."""
    if notify is None:
        return None
    if isinstance(notify, dict):
        return notify  # assume caller already used camelCase keys
    import dataclasses
    if dataclasses.is_dataclass(notify) and not isinstance(notify, type):
        return _camel_case_dict(dataclasses.asdict(notify))
    return notify


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
    
    def _is_connection_healthy(self) -> bool:
        """Check if the cached connection is healthy by running SELECT 1."""
        if self._connection is None:
            return False
        try:
            cursor = self._connection.cursor()
            cursor.execute('SELECT 1')
            cursor.close()
            return True
        except Exception:
            self._connection = None
            return False

    def _get_connection(self, config_name: Optional[str] = None) -> Any:
        """
        Get or create a Snowflake connection.
        
        Args:
            config_name: Optional name of the config to use
            
        Returns:
            Snowflake connection object
        """
        if self._connection is not None and self._is_connection_healthy():
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
    
    def execute_query(
        self,
        sql_text: str,
        binds: Optional[List[Any]] = None,
        config_name: Optional[str] = None,
    ) -> QueryResult:
        """
        Execute a SQL query against Snowflake.
        
        Executes any SQL statement including DML (INSERT, UPDATE, DELETE) and DDL (CREATE, ALTER, DROP).
        For read-only queries, prefer using `execute_query_read_only` which validates the query type.
        
        Args:
            sql_text: The SQL query to execute
            binds: Optional list of bind parameters
            config_name: Optional name of the config to use
            
        Returns:
            QueryResult with statement and rows
        """
        conn = self._get_connection(config_name)
        cursor = conn.cursor()
        try:
            cursor.execute(sql_text, binds or [])
            rows = cursor.fetchall()
            return QueryResult(statement=cursor, rows=list(rows))
        finally:
            cursor.close()
    
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
        # Remove single-line comments and /* */ block comments
        without_comments = re.sub(r'--[^\n]*', '', stripped)
        without_comments = re.sub(r'/\*[\s\S]*?\*/', '', without_comments).strip()
        
        first_word = without_comments.split()[0].upper() if without_comments.split() else ''
        if first_word not in ('SELECT', 'WITH', 'SHOW', 'DESCRIBE', 'DESC'):
            raise ValueError(
                "Only SELECT queries are allowed. "
                "DML and DDL statements are not permitted."
            )
        
        if ';' in without_comments:
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
            model = semantic_model or os.environ.get('CORTEX_ANALYST_SEMANTIC_MODEL')
            if not model:
                raise ValueError(
                    "CORTEX_ANALYST_SEMANTIC_MODEL environment variable is required or semantic model must be provided"
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
                
                # Parse SSE events to find the final response.
                # Track both event: and data: lines per the SSE spec.
                final_content = None
                current_event_name = None
                for line in response_text.split('\n'):
                    if line.startswith('event: '):
                        current_event_name = line[7:].strip()
                    elif line.startswith('data: ') and line != 'data: [DONE]':
                        try:
                            event_data = json.loads(line[6:])
                            if current_event_name == 'response' and event_data.get('content'):
                                final_content = event_data.get('content')
                        except json.JSONDecodeError:
                            pass
                
                sanitized_headers = {
                    'Content-Type': headers['Content-Type'],
                    'Accept': headers['Accept'],
                }
                
                if final_content is None:
                    return CortexAgentResponse(
                        success=False,
                        status_code=200,
                        error='No complete message received from agent',
                        request={'url': url, 'method': 'POST'},
                    )
                
                return CortexAgentResponse(
                    success=True,
                    status_code=200,
                    data={"message": {"role": "agent", "content": final_content}},
                    request={'url': url, 'method': 'POST'},
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
        url = getattr(options, 'url', None)
        if not url:
            return HttpResponse(
                success=False,
                status=0,
                headers={},
                error="url is required",
            )
        
        method = getattr(options, 'method', 'GET') or 'GET'
        headers = getattr(options, 'headers', {}) or {}
        body = getattr(options, 'body', None)
        timeout = (getattr(options, 'timeout', 30000) or 30000) / 1000  # Convert ms to seconds
        oauth_ref = getattr(options, 'oauth_ref', None) or getattr(options, 'oauthRef', None)

        if oauth_ref:
            from p67_sdk.ipc import request_oauth_token
            try:
                access_token = request_oauth_token(oauth_ref)
                headers = dict(headers)  # copy before mutating
                headers['Authorization'] = f'Bearer {access_token}'
            except Exception as e:
                return HttpResponse(
                    success=False,
                    status=0,
                    headers={},
                    error=f'Failed to resolve OAuth token "{oauth_ref}": {str(e)}',
                )

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

        notify_dict = _serialize_notify(options.get('notify'))

        # Send interrupt and get ID
        interrupt_id = send_interrupt(payload, node_id=node_id, notify=notify_dict)
        
        # Wait for resume with optional timeout
        timeout_sec = timeout_ms / 1000 if timeout_ms else None
        response = wait_for_resume(interrupt_id, timeout_sec)
        
        return response  # type: ignore
    
    def _get_region_header(self, region: Optional[str]) -> Optional[str]:
        """
        Maps region option to the appropriate header value for cross-region inference.
        
        Args:
            region: Region option string
            
        Returns:
            Header value or None if auto/not specified
        """
        if not region or region == 'auto':
            return None
        
        region_map = {
            'cross-cloud-any': 'cross-cloud',
            'aws-global': 'aws',
            'aws-us': 'aws-us',
            'aws-eu': 'aws-eu',
            'aws-apj': 'aws-apj',
            'azure-global': 'azure',
            'azure-us': 'azure-us',
            'azure-eu': 'azure-eu',
        }
        
        return region_map.get(region)
    
    def _normalize_messages(self, messages: Any) -> List[Dict[str, Any]]:
        """
        Normalizes messages input to list format.
        
        Args:
            messages: String or list of message dicts
            
        Returns:
            List of message dicts
        """
        if isinstance(messages, str):
            return [{'role': 'user', 'content': messages}]
        return list(messages)
    
    def _build_cortex_complete_payload(
        self,
        options: CortexCompleteOptions,
        stream: bool,
    ) -> Dict[str, Any]:
        """
        Builds the request payload for Cortex Complete API.
        
        Args:
            options: Complete options
            stream: Whether to enable streaming
            
        Returns:
            Request payload dict
        """
        messages = self._normalize_messages(options.messages)
        
        # Convert messages to API format
        api_messages = []
        for msg in messages:
            api_msg: Dict[str, Any] = {'role': msg.get('role', 'user')}
            
            content = msg.get('content')
            if isinstance(content, str):
                api_msg['content'] = content
            else:
                api_msg['content'] = content
            
            if msg.get('tool_call_id'):
                api_msg['tool_call_id'] = msg['tool_call_id']
            
            api_messages.append(api_msg)
        
        payload: Dict[str, Any] = {
            'model': options.model,
            'messages': api_messages,
        }
        
        # Add optional parameters
        if options.temperature is not None:
            payload['temperature'] = options.temperature
        if options.top_p is not None:
            payload['top_p'] = options.top_p
        if options.max_tokens is not None:
            payload['max_tokens'] = options.max_tokens
        
        # Add tools if provided
        if options.tools:
            payload['tools'] = [
                {
                    'type': tool.type,
                    'function': {
                        'name': tool.function.name,
                        'description': tool.function.description,
                        'parameters': {
                            'type': tool.function.parameters.type,
                            'properties': tool.function.parameters.properties,
                            'required': tool.function.parameters.required,
                        } if tool.function.parameters.required else {
                            'type': tool.function.parameters.type,
                            'properties': tool.function.parameters.properties,
                        },
                    },
                }
                for tool in options.tools
            ]
        
        # Add tool_choice if provided
        if options.tool_choice is not None:
            if isinstance(options.tool_choice, str):
                payload['tool_choice'] = options.tool_choice
            else:
                payload['tool_choice'] = {
                    'type': options.tool_choice.type,
                    'function': {'name': options.tool_choice.function.name},
                }
        
        # Add guardrails if provided
        if options.guardrails:
            guardrails_payload: Dict[str, Any] = {
                'enabled': options.guardrails.enabled,
            }
            if options.guardrails.response_when_unsafe:
                guardrails_payload['response_when_unsafe'] = options.guardrails.response_when_unsafe
            payload['guardrails'] = guardrails_payload
        
        # Add stream flag - must explicitly set false for non-streaming
        payload['stream'] = stream
        if stream:
            payload['stream_options'] = {'include_usage': True}
        
        return payload
    
    def _create_request_info(
        self,
        url: str,
        headers: Dict[str, str],
        payload: Any,
    ) -> CortexCompleteRequestInfo:
        """
        Creates sanitized request info for debugging.
        
        Args:
            url: Request URL
            headers: Request headers
            payload: Request payload
            
        Returns:
            Request info with auth header removed
        """
        sanitized_headers = {k: v for k, v in headers.items() if k != 'Authorization'}
        return CortexCompleteRequestInfo(
            url=url,
            headers=sanitized_headers,
            payload=payload,
        )
    
    def _parse_usage(self, api_usage: Optional[Dict[str, Any]]) -> Optional[CortexTokenUsage]:
        """
        Parses token usage from API response.
        
        Args:
            api_usage: Usage dict from API
            
        Returns:
            CortexTokenUsage or None
        """
        if not api_usage:
            return None
        
        return CortexTokenUsage(
            prompt_tokens=api_usage.get('prompt_tokens', 0),
            completion_tokens=api_usage.get('completion_tokens', 0),
            total_tokens=api_usage.get('total_tokens', 0),
            prompt_tokens_cached=api_usage.get('prompt_tokens_cached'),
        )
    
    def _parse_choices(self, api_choices: List[Dict[str, Any]]) -> List[CortexChoice]:
        """
        Parses choices from API response.
        
        Args:
            api_choices: Choices list from API
            
        Returns:
            List of CortexChoice
        """
        choices = []
        for choice in api_choices:
            message = choice.get('message', {})
            
            # Parse tool calls if present
            tool_calls = None
            if message.get('tool_calls'):
                tool_calls = [
                    CortexToolCall(
                        id=tc.get('id', ''),
                        type='function',
                        function=CortexToolCallFunction(
                            name=tc.get('function', {}).get('name', ''),
                            arguments=tc.get('function', {}).get('arguments', ''),
                        ),
                    )
                    for tc in message['tool_calls']
                ]
            
            choice_message = CortexChoiceMessage(
                role='assistant',
                content=message.get('content'),
                tool_calls=tool_calls,
            )
            
            choices.append(CortexChoice(
                index=choice.get('index', 0),
                message=choice_message,
                finish_reason=choice.get('finish_reason', 'stop'),
            ))
        
        return choices
    
    def cortex_complete(
        self,
        options: CortexCompleteOptions,
        config_name: Optional[str] = None,
    ) -> CortexCompleteResponse:
        """
        Generate text completion using Snowflake Cortex LLM.
        
        Args:
            options: Completion configuration
            config_name: Optional Snowflake config name
            
        Returns:
            CortexCompleteResponse with choices, usage, or error.
            Never raises - errors returned in response object.
            
        Example:
            response = sdk.cortex_complete(CortexCompleteOptions(
                model='claude-3-5-sonnet',
                messages='Explain quantum computing.'
            ))
            if response.success:
                print(response.choices[0].message.content)
        """
        cfg = self._get_config(config_name)
        
        token = cfg.get('token')
        access_url = self._normalize_access_url(cfg.get('accessUrl'))
        
        if not token or not access_url:
            return CortexCompleteResponse(
                success=False,
                error="token and accessUrl are required in config",
                status_code=0,
            )
        
        url = f"{access_url}/api/v2/cortex/inference:complete"
        payload = self._build_cortex_complete_payload(options, stream=False)
        timeout = (options.timeout or 120000) / 1000  # Convert ms to seconds
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        
        # Add region header if specified
        region_header = self._get_region_header(options.region)
        if region_header:
            headers['X-Snowflake-Cortex-Region'] = region_header
        
        request_info = self._create_request_info(url, headers, payload)
        
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers, method='POST')
            
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                response_data = json.loads(resp.read().decode('utf-8'))
                
                return CortexCompleteResponse(
                    success=True,
                    id=response_data.get('id'),
                    model=response_data.get('model'),
                    choices=self._parse_choices(response_data.get('choices', [])),
                    usage=self._parse_usage(response_data.get('usage')),
                    status_code=resp.status,
                    request=request_info,
                )
                
        except urllib.error.HTTPError as e:
            error_body = None
            try:
                error_body = e.read().decode('utf-8')
            except Exception:
                pass
            return CortexCompleteResponse(
                success=False,
                error=f"HTTP {e.code}: {error_body or str(e)}",
                status_code=e.code,
                request=request_info,
            )
        except Exception as e:
            error_msg = str(e)
            if 'timed out' in error_msg.lower() or 'timeout' in error_msg.lower():
                return CortexCompleteResponse(
                    success=False,
                    error=f"Request timeout after {int(timeout * 1000)}ms",
                    status_code=0,
                    request=request_info,
                )
            return CortexCompleteResponse(
                success=False,
                error=f"Request failed: {error_msg}",
                status_code=0,
                request=request_info,
            )
    
    def cortex_complete_stream(
        self,
        options: CortexCompleteOptions,
        config_name: Optional[str] = None,
    ) -> Iterator[CortexStreamChunk]:
        """
        Generate streaming text completion using Snowflake Cortex LLM.
        
        Returns an iterator that yields chunks as they arrive.
        
        Args:
            options: Completion configuration
            config_name: Optional Snowflake config name
            
        Yields:
            CortexStreamChunk objects as they arrive
            
        Raises:
            Exception: If request fails to initiate
            
        Example:
            stream = sdk.cortex_complete_stream(CortexCompleteOptions(
                model='claude-3-5-sonnet',
                messages='Write a haiku.'
            ))
            
            full_content = ''
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    print(delta, end='', flush=True)
                    full_content += delta
        """
        cfg = self._get_config(config_name)
        
        token = cfg.get('token')
        access_url = self._normalize_access_url(cfg.get('accessUrl'))
        
        if not token or not access_url:
            raise ValueError("token and accessUrl are required in config")
        
        url = f"{access_url}/api/v2/cortex/inference:complete"
        payload = self._build_cortex_complete_payload(options, stream=True)
        timeout = (options.timeout or 120000) / 1000  # Convert ms to seconds
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
        }
        
        # Add region header if specified
        region_header = self._get_region_header(options.region)
        if region_header:
            headers['X-Snowflake-Cortex-Region'] = region_header
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            buffer = ''
            
            while True:
                chunk_bytes = resp.read(4096)
                if not chunk_bytes:
                    break
                
                buffer += chunk_bytes.decode('utf-8')
                lines = buffer.split('\n')
                buffer = lines.pop()  # Keep incomplete line in buffer
                
                for line in lines:
                    if not line.strip():
                        continue
                    
                    if line.startswith('data: '):
                        data_str = line[6:].strip()
                        
                        if data_str == '[DONE]':
                            return
                        
                        try:
                            event_data = json.loads(data_str)
                            yield self._parse_stream_chunk(event_data)
                        except json.JSONDecodeError:
                            # Skip malformed JSON
                            pass
            
            # Process remaining buffer
            if buffer.strip():
                if buffer.startswith('data: '):
                    data_str = buffer[6:].strip()
                    if data_str and data_str != '[DONE]':
                        try:
                            event_data = json.loads(data_str)
                            yield self._parse_stream_chunk(event_data)
                        except json.JSONDecodeError:
                            pass
    
    def _parse_stream_chunk(self, data: Dict[str, Any]) -> CortexStreamChunk:
        """
        Parses a streaming chunk from the API response.
        
        Args:
            data: Chunk data dict
            
        Returns:
            CortexStreamChunk
        """
        choices = data.get('choices', [])
        
        parsed_choices = []
        for choice in choices:
            delta = choice.get('delta', {})
            
            # Parse tool calls delta
            tool_calls = None
            if delta.get('tool_calls'):
                tool_calls = []
                for tc in delta['tool_calls']:
                    fn = tc.get('function', {})
                    tool_call = CortexStreamDeltaToolCall(
                        index=tc.get('index', 0),
                        id=tc.get('id'),
                        type=tc.get('type'),
                        function=CortexStreamDeltaToolCallFunction(
                            name=fn.get('name'),
                            arguments=fn.get('arguments'),
                        ) if fn else None,
                    )
                    tool_calls.append(tool_call)
            
            parsed_delta = CortexStreamDelta(
                role=delta.get('role'),
                content=delta.get('content'),
                tool_calls=tool_calls,
            )
            
            parsed_choices.append(CortexStreamChoice(
                index=choice.get('index', 0),
                delta=parsed_delta,
                finish_reason=choice.get('finish_reason'),
            ))
        
        import time
        return CortexStreamChunk(
            id=data.get('id', ''),
            object='chat.completion.chunk',
            created=data.get('created', int(time.time())),
            model=data.get('model', ''),
            choices=parsed_choices,
            usage=self._parse_usage(data.get('usage')),
        )
    
    def execute_subworkflow(
        self,
        options: SubworkflowOptions,
        config_name: Optional[str] = None,
    ) -> SubworkflowResponse:
        """
        Execute another workflow as a subworkflow.
        
        Runs a workflow by ID or by name, optionally passing runtime parameters.
        When running by name, the latest version of the workflow is used.
        
        Args:
            options: SubworkflowOptions containing:
                - workflow_id: Run by ID (mutually exclusive with workflow_name)
                - workflow_name: Run by name, uses latest version (mutually exclusive with workflow_id)
                - params: Optional dict of parameter overrides
                - timeout: Timeout in milliseconds (default 300000 = 5 min)
            config_name: Optional name of the config to use for authentication
            
        Returns:
            SubworkflowResponse with success status, stdout, stderr, exit_code, etc.
            
        Example:
            # Run by name with parameters
            result = sdk.execute_subworkflow(SubworkflowOptions(
                workflow_name='data-pipeline',
                params={'env': 'prod', 'batch_size': '100'}
            ))
            
            if result.success:
                print(f"Completed with exit code: {result.exit_code}")
            else:
                print(f"Failed: {result.error}")
        """
        cfg = self._get_config(config_name)
        
        token = cfg.get('token')

        # In SPCS, the runner job container is separate from controld — use the
        # controld internal DNS passed via P67_CONTROLD_URL. In local/Docker mode,
        # the workflow is a child process of controld so localhost works.
        controld_url = os.environ.get('P67_CONTROLD_URL')
        port = os.environ.get('PORT', '3002')
        access_url = controld_url or f"http://localhost:{port}"
        
        if not token:
            return SubworkflowResponse(
                success=False,
                error="token is required in config for subworkflow execution",
            )
        
        # Build URL based on whether we're using ID or name.
        # Always append sync=true so controld waits for the subworkflow to complete.
        if options.workflow_id is not None:
            url = f"{access_url}/api/workflow/{quote(options.workflow_id, safe='')}/run?sync=true"
        else:
            url = f"{access_url}/api/workflow/name/{quote(options.workflow_name, safe='')}/run?sync=true"
        
        # Build request body with params
        payload = {}
        if options.params:
            payload['params'] = options.params
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # SPCS ingress injects sf-context-current-user for external requests;
        # for internal service-to-service calls we must set it ourselves so
        # controld's user plugin can resolve the user.
        username = cfg.get('username')
        if username:
            headers['sf-context-current-user'] = username
        
        timeout_sec = options.timeout / 1000  # Convert ms to seconds
        
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers, method='POST')
            
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                response_data = json.loads(resp.read().decode('utf-8'))
                
                return SubworkflowResponse(
                    success=response_data.get('success', False),
                    exit_code=response_data.get('exitCode'),
                    stdout=response_data.get('stdout'),
                    stderr=response_data.get('stderr'),
                    status=response_data.get('status'),
                    run_id=response_data.get('runId'),
                    result=response_data.get('result'),
                )
                
        except urllib.error.HTTPError as e:
            error_body = None
            try:
                error_body = e.read().decode('utf-8')
                error_json = json.loads(error_body)
                error_msg = error_json.get('message') or error_json.get('error') or error_body
            except Exception:
                error_msg = error_body or str(e)
            
            return SubworkflowResponse(
                success=False,
                error=f"HTTP {e.code}: {error_msg}",
            )
        except socket.timeout:
            return SubworkflowResponse(
                success=False,
                error=f"Request timed out after {timeout_sec}s",
            )
        except Exception as e:
            return SubworkflowResponse(
                success=False,
                error=str(e),
            )
    
    def cortex_code(
        self,
        options: CortexCodeOptions,
    ) -> CortexCodeResponse:
        """
        Invoke the Cortex Code CLI to perform agentic coding tasks.
        
        Runs the ``cortex`` CLI as a subprocess with the given prompt and
        returns the output.
        
        Args:
            options: CortexCodeOptions containing:
                - prompt: The prompt/instruction to send (required)
                - timeout: Timeout in seconds (default 900 = 15 min)
                - work_dir: Working directory for the process
                - model: Model to use (e.g., 'opus', 'sonnet')
                - allow_all_tool_calls: Skip tool-call confirmations (default False)
            
        Returns:
            CortexCodeResponse with success status, output, and optional error.
            Never raises - errors are returned in the response object.
            
        Example:
            response = sdk.cortex_code(CortexCodeOptions(
                prompt='Read the file data.csv and summarize the contents.',
                timeout=300,
            ))
            if response.success:
                print(response.output)
            else:
                print(f"Error: {response.error}")
        """
        if not options.prompt:
            return CortexCodeResponse(
                success=False,
                output='',
                error='prompt is required',
            )
        
        args = ['cortex', '-p', options.prompt, '--bypass']
        
        if options.model:
            args.extend(['--model', options.model])
        
        if options.allow_all_tool_calls:
            args.append('--dangerously-allow-all-tool-calls')
        
        if options.profile:
            args.extend(['--profile', options.profile])
        
        # Write a temporary config.toml so the cortex CLI can authenticate.
        # Mirrors the TypeScript sdk-impl.ts cortexCode() approach.
        snowflake_home = None
        try:
            cfg = self._get_config()
        except ValueError:
            cfg = {}
        
        account = cfg.get('account')
        token = cfg.get('token')
        password = cfg.get('password')
        
        if account and (token or password):
            snowflake_home = tempfile.mkdtemp(prefix='p67-cortex-')
            lines = [
                'default_connection_name = "default"',
                '',
                '[connections.default]',
                f'account = "{account}"',
            ]
            username = cfg.get('username')
            if username:
                lines.append(f'user = "{username}"')
            if token:
                lines.append('authenticator = "programmatic_access_token"')
                lines.append(f'token = "{token}"')
            elif password:
                lines.append(f'password = "{password}"')
            access_url = cfg.get('accessUrl')
            if access_url:
                host = access_url
                if host.startswith('https://'):
                    host = host[8:]
                elif host.startswith('http://'):
                    host = host[7:]
                lines.append(f'host = "{host}"')
            for key in ('warehouse', 'database', 'schema'):
                val = cfg.get(key)
                if val:
                    lines.append(f'{key} = "{val}"')
            
            # Write config.toml (used by cortex -p for LLM calls)
            config_path = os.path.join(snowflake_home, 'config.toml')
            with open(config_path, 'w') as f:
                f.write('\n'.join(lines) + '\n')
            os.chmod(config_path, 0o600)
            
            # Write connections.toml (used by cortex profile add for SQL ops)
            conn_lines = ['[default]']
            if account:
                conn_lines.append(f'account = "{account}"')
            if username:
                conn_lines.append(f'user = "{username}"')
            if token:
                conn_lines.append('authenticator = "programmatic_access_token"')
                conn_lines.append(f'token = "{token}"')
            elif password:
                conn_lines.append(f'password = "{password}"')
            if access_url:
                h = access_url
                if h.startswith('https://'):
                    h = h[8:]
                elif h.startswith('http://'):
                    h = h[7:]
                conn_lines.append(f'host = "{h}"')
            for key in ('warehouse', 'database', 'schema'):
                val = cfg.get(key)
                if val:
                    conn_lines.append(f'{key} = "{val}"')
            conn_path = os.path.join(snowflake_home, 'connections.toml')
            with open(conn_path, 'w') as f:
                f.write('\n'.join(conn_lines) + '\n')
            os.chmod(conn_path, 0o600)
        
        env = {**os.environ}
        if snowflake_home:
            env['SNOWFLAKE_HOME'] = snowflake_home
        
        # Pre-fetch the profile from the account's registry if requested.
        if options.profile and snowflake_home:
            # Attempt 1: cortex profile add -c default
            profile_fetched = False
            try:
                subprocess.run(
                    ['cortex', 'profile', 'add', options.profile, '--force', '-c', 'default'],
                    capture_output=True, text=True, timeout=30, env=env,
                )
                print(f'[SDK] Profile "{options.profile}" fetched via cortex profile add')
                profile_fetched = True
            except Exception as e:
                print(f'[SDK] cortex profile add failed (will try direct SQL): {e}')
            
            # Attempt 2: Direct SQL query
            if not profile_fetched:
                try:
                    result = self.execute_query(
                        "SELECT CONFIG_NAME, DESCRIPTION, OWNER_TEAM, SKILL_REPOS, MCP_SERVERS, "
                        "COMMAND_REPOS, ENV_VARS, SETTINGS_OVERRIDES, VERSION, "
                        "SYSTEM_PROMPT_REPO, HOOKS, PLUGINS "
                        "FROM CORTEX_CODE.CONFIG.PROFILE_REGISTRY "
                        "WHERE CONFIG_NAME = %s AND ACTIVE = TRUE",
                        [options.profile],
                    )
                    if result.rows and len(result.rows) > 0:
                        row = result.rows[0]
                        import json as _json
                        profile_json = {
                            "name": row[0],
                            "description": row[1] or "",
                            "ownerTeam": row[2] or "",
                            "skillRepos": [],
                            "mcpServers": _json.loads(row[4]) if isinstance(row[4], str) else (row[4] or {}),
                            "commandRepos": _json.loads(row[5]) if isinstance(row[5], str) else (row[5] or []),
                            "envVars": _json.loads(row[6]) if isinstance(row[6], str) else (row[6] or {}),
                            "settingsOverrides": _json.loads(row[7]) if isinstance(row[7], str) else (row[7] or {}),
                            "version": row[8] or "1.0",
                            "systemPromptRepo": _json.loads(row[9]) if isinstance(row[9], str) else row[9],
                            "hooks": _json.loads(row[10]) if isinstance(row[10], str) else row[10],
                            "plugins": _json.loads(row[11]) if isinstance(row[11], str) else (row[11] or []),
                        }
                        profiles_dir = os.path.join(snowflake_home, 'cortex', 'profiles')
                        os.makedirs(profiles_dir, exist_ok=True)
                        profile_path = os.path.join(profiles_dir, f'{options.profile}.json')
                        with open(profile_path, 'w') as f:
                            _json.dump(profile_json, f, indent=2)
                        print(f'[SDK] Profile "{options.profile}" fetched from registry and written to {profiles_dir}')
                    else:
                        print(f'[SDK] Warning: profile "{options.profile}" not found in registry')
                except Exception as e:
                    print(f'[SDK] Warning: failed to fetch profile "{options.profile}" from registry: {e}')
            
            # Download skills from stage (profile's skillRepos) or copy bundled skills
            import json as _json
            coco_skills_dir = os.path.join(snowflake_home, 'cortex', 'skills')
            os.makedirs(coco_skills_dir, exist_ok=True)
            skills_found = False

            # Attempt 1: Download skills from stage via skillRepos in profile registry
            if options.profile:
                try:
                    repo_result = self.execute_query(
                        "SELECT SKILL_REPOS FROM CORTEX_CODE.CONFIG.PROFILE_REGISTRY "
                        "WHERE CONFIG_NAME = %s AND ACTIVE = TRUE",
                        [options.profile],
                    )
                    skill_repos = []
                    if repo_result.rows and len(repo_result.rows) > 0:
                        raw = repo_result.rows[0][0]
                        if raw:
                            skill_repos = _json.loads(raw) if isinstance(raw, str) else raw

                    for repo in skill_repos:
                        stage_path = repo.get('snowflake_stage') if isinstance(repo, dict) else None
                        if not stage_path:
                            continue

                        # Extract database.schema from stage path (e.g. @DB.SCHEMA.STAGE/...)
                        stage_ref = stage_path.lstrip('@').split('/')[0]
                        stage_parts = stage_ref.split('.')
                        if len(stage_parts) >= 2:
                            qualified_schema = f"{stage_parts[0]}.{stage_parts[1]}"
                            self.execute_query(f"USE SCHEMA {qualified_schema}")

                        self.execute_query(
                            "CREATE TEMPORARY FILE FORMAT IF NOT EXISTS p67_raw_text "
                            "TYPE='CSV' FIELD_DELIMITER='NONE' RECORD_DELIMITER='NONE'"
                        )

                        list_result = self.execute_query(f"LIST {stage_path}")
                        # Group files by skill directory
                        skill_files: Dict[str, List[str]] = {}
                        for row in (list_result.rows or []):
                            name = str(row[0]) if row[0] else ''
                            parts = name.split('/')
                            try:
                                skills_idx = parts.index('skills')
                            except ValueError:
                                continue
                            if skills_idx + 1 < len(parts):
                                skill_name = parts[skills_idx + 1]
                                file_name = '/'.join(parts[skills_idx + 2:])
                                if skill_name and file_name:
                                    skill_files.setdefault(skill_name, []).append(file_name)

                        for skill_name, files in skill_files.items():
                            skill_dir = os.path.join(coco_skills_dir, skill_name)
                            os.makedirs(skill_dir, exist_ok=True)
                            for file in files:
                                file_stage = f"{stage_path}{skill_name}/{file}"
                                try:
                                    content_result = self.execute_query(
                                        f"SELECT $1::VARCHAR AS content FROM {file_stage} "
                                        f"(FILE_FORMAT => p67_raw_text)"
                                    )
                                    if content_result.rows and len(content_result.rows) > 0:
                                        content = str(content_result.rows[0][0] or '')
                                        file_path = os.path.join(skill_dir, file)
                                        file_dir = os.path.dirname(file_path)
                                        if file_dir != skill_dir:
                                            os.makedirs(file_dir, exist_ok=True)
                                        with open(file_path, 'w') as f:
                                            f.write(content)
                                except Exception as file_err:
                                    print(f'[SDK] Warning: failed to download {file_stage}: {file_err}')
                            print(f'[SDK] Downloaded skill "{skill_name}" from stage ({len(files)} file(s))')
                            skills_found = True
                except Exception as e:
                    print(f'[SDK] Warning: failed to download skills from stage: {e}')

            # Attempt 2: Copy bundled skills as fallback
            if not skills_found:
                skills_dir = None
                if options.work_dir:
                    candidate = os.path.join(options.work_dir, 'skills')
                    if os.path.isdir(candidate):
                        skills_dir = candidate
                else:
                    spcs_skills = '/workflow/skills'
                    if os.path.isdir(spcs_skills):
                        skills_dir = spcs_skills
                if skills_dir:
                    try:
                        import shutil
                        for entry in os.scandir(skills_dir):
                            if entry.is_dir():
                                dest = os.path.join(coco_skills_dir, entry.name)
                                shutil.copytree(entry.path, dest, dirs_exist_ok=True)
                                print(f'[SDK] Copied bundled skill "{entry.name}" to {dest}')
                                skills_found = True
                    except Exception as e:
                        print(f'[SDK] Warning: failed to copy bundled skills: {e}')

            # Write skills.json and pass --skills flag if any skills were found
            if skills_found:
                try:
                    skills_json_path = os.path.join(snowflake_home, 'cortex', 'skills.json')
                    with open(skills_json_path, 'w') as f:
                        _json.dump({'paths': [coco_skills_dir]}, f, indent=2)
                    args.extend(['--skills', skills_json_path])
                    print(f'[SDK] Wrote skills.json pointing to {coco_skills_dir}, passing --skills flag')
                except Exception as e:
                    print(f'[SDK] Warning: failed to write skills.json: {e}')
        
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=options.timeout,
                cwd=options.work_dir,
                env=env,
            )
            
            if result.returncode != 0:
                error_msg = (
                    result.stderr.strip()
                    if result.stderr
                    else result.stdout.strip()
                    if result.stdout
                    else f"cortex exited with code {result.returncode}"
                )
                return CortexCodeResponse(
                    success=False,
                    output=result.stdout or '',
                    error=error_msg,
                    exit_code=result.returncode,
                )
            
            return CortexCodeResponse(
                success=True,
                output=result.stdout or '',
                exit_code=0,
            )
        
        except subprocess.TimeoutExpired:
            return CortexCodeResponse(
                success=False,
                output='',
                error=f"Cortex Code timed out after {options.timeout} seconds",
            )
        except FileNotFoundError:
            return CortexCodeResponse(
                success=False,
                output='',
                error="The cortex CLI is not installed or not in PATH.",
            )
        except Exception as e:
            return CortexCodeResponse(
                success=False,
                output='',
                error=f"Unexpected error: {str(e)}",
            )
        finally:
            if snowflake_home:
                import shutil
                shutil.rmtree(snowflake_home, ignore_errors=True)
    
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
