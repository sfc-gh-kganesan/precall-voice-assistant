# P67 Workflow SDK for Python

Build workflows that interact with Snowflake and Cortex services.

## Installation

```bash
pip install p67-workflow-sdk
```

## Usage

```python
from p67_sdk import WorkflowSDK

def main(sdk: WorkflowSDK):
    # Execute a read-only SQL query
    result = sdk.execute_query_read_only("SELECT * FROM my_table LIMIT 10")
    print(f"Got {len(result.rows)} rows")
    
    # Get a parameter from the manifest
    api_key = sdk.get_parameter("api_key")
    
    # Make an HTTP request
    response = sdk.http_request({
        "url": "https://api.example.com/data",
        "method": "GET",
    })
    
    # Pause for human input
    approval = sdk.interrupt({
        "question": "Approve this action?",
        "details": {"amount": 500}
    })
    
    return {"status": "completed", "approved": approval}
```

## API Reference

### WorkflowSDK

- `get_parameter(name, config_name=None)` - Get a parameter value
- `get_parameters(config_name=None)` - Get all parameters
- `execute_query_read_only(sql_text, binds=None, config_name=None)` - Execute a read-only SQL query
- `query_cortex_analyst(question, semantic_model=None, config_name=None)` - Query Cortex Analyst
- `call_cortex_agent(question, options=None, config_name=None)` - Call a Cortex Agent
- `email(options, config_name=None)` - Send an email
- `http_request(options)` - Make an HTTP request
- `interrupt(payload, options=None)` - Pause for human input
- `close()` - Close connections

## License

MIT
