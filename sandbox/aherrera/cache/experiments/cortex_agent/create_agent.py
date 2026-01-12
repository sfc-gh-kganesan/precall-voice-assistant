"""Create Cortex Agent using REST API."""
import json
import os
import requests
from shared.utils import get_snowpark_session

def get_rest_api_config():
    """Get Snowflake REST API configuration."""
    session = get_snowpark_session()

    # Get warehouse
    result = session.sql("SELECT CURRENT_WAREHOUSE()").collect()
    warehouse = result[0][0]

    # Get OAuth token - Cortex Agent requires OAuth (PAT)
    # Try SNOWFLAKE_PAT first (OAuth token), fallback to session token
    token = os.getenv("SNOWFLAKE_PAT")
    if not token:
        token = session.connection.rest.token
        print("Warning: Using session token - Cortex Agent may require SNOWFLAKE_PAT")

    # Use host directly from connection
    base_url = f"https://{session.connection.host}"

    return {
        "base_url": base_url,
        "token": token,
        "warehouse": warehouse
    }

def create_cortex_agent():
    """Create Cortex Agent with math SPROCs as tools."""
    config = get_rest_api_config()
    
    url = f"{config['base_url']}/api/v2/databases/AI_FDE/schemas/CACHE_EXPERIMENTS/agents"
    
    headers = {
        "Authorization": f'Bearer {config["token"]}',
        "Content-Type": "application/json"
    }
    
    # Agent specification
    agent_spec = {
        "name": "math_agent",
        "comment": "Math assistant agent for cache comparison experiments",
        "models": {
            "orchestration": "claude-3-5-sonnet"
        },
        "instructions": {
            "response": "You are a helpful math assistant. Use the provided tools to perform calculations and return the final answer clearly and concisely.",
            "system": "You have access to math tools: add, multiply, divide, subtract, and calculate_average. Always use these tools to perform calculations."
        },
        "tools": [
            {
                "tool_spec": {
                    "type": "generic",
                    "name": "add",
                    "description": "Add two numbers together",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "a": {"type": "number", "description": "First number"},
                            "b": {"type": "number", "description": "Second number"}
                        },
                        "required": ["a", "b"]
                    }
                }
            },
            {
                "tool_spec": {
                    "type": "generic",
                    "name": "multiply",
                    "description": "Multiply two numbers",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "a": {"type": "number", "description": "First number"},
                            "b": {"type": "number", "description": "Second number"}
                        },
                        "required": ["a", "b"]
                    }
                }
            },
            {
                "tool_spec": {
                    "type": "generic",
                    "name": "divide",
                    "description": "Divide two numbers",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "a": {"type": "number", "description": "Numerator"},
                            "b": {"type": "number", "description": "Denominator"}
                        },
                        "required": ["a", "b"]
                    }
                }
            },
            {
                "tool_spec": {
                    "type": "generic",
                    "name": "subtract",
                    "description": "Subtract second number from first",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "a": {"type": "number", "description": "First number"},
                            "b": {"type": "number", "description": "Second number"}
                        },
                        "required": ["a", "b"]
                    }
                }
            },
            {
                "tool_spec": {
                    "type": "generic",
                    "name": "calculate_average",
                    "description": "Calculate the average of a list of numbers",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "numbers": {
                                "type": "array",
                                "items": {"type": "number"},
                                "description": "Array of numbers to average"
                            }
                        },
                        "required": ["numbers"]
                    }
                }
            }
        ],
        "tool_resources": {
            "add": {
                "type": "function",
                "execution_environment": {
                    "type": "warehouse",
                    "warehouse": config['warehouse']
                },
                "identifier": "AI_FDE.CACHE_EXPERIMENTS.add"
            },
            "multiply": {
                "type": "function",
                "execution_environment": {
                    "type": "warehouse",
                    "warehouse": config['warehouse']
                },
                "identifier": "AI_FDE.CACHE_EXPERIMENTS.multiply"
            },
            "divide": {
                "type": "function",
                "execution_environment": {
                    "type": "warehouse",
                    "warehouse": config['warehouse']
                },
                "identifier": "AI_FDE.CACHE_EXPERIMENTS.divide"
            },
            "subtract": {
                "type": "function",
                "execution_environment": {
                    "type": "warehouse",
                    "warehouse": config['warehouse']
                },
                "identifier": "AI_FDE.CACHE_EXPERIMENTS.subtract"
            },
            "calculate_average": {
                "type": "function",
                "execution_environment": {
                    "type": "warehouse",
                    "warehouse": config['warehouse']
                },
                "identifier": "AI_FDE.CACHE_EXPERIMENTS.calculate_average"
            }
        }
    }
    
    # Add createMode parameter for OR REPLACE behavior
    params = {"createMode": "orReplace"}
    
    print("Creating Cortex Agent...")
    print(f"URL: {url}")
    print(f"Agent name: math_agent")
    print(f"Warehouse: {config['warehouse']}")
    
    response = requests.post(url, headers=headers, json=agent_spec, params=params)
    
    if response.status_code in [200, 201]:
        print("\n✓ Agent created successfully!")
        print(json.dumps(response.json(), indent=2))
        return True
    else:
        print(f"\n✗ Error creating agent: {response.status_code}")
        print(response.text)
        return False

if __name__ == "__main__":
    create_cortex_agent()
