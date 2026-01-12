"""Cortex Agent experiment runner using REST API.

Uses Snowflake Cortex Agent REST API with streaming responses
to run test queries and measure performance.
"""
import logging
import time
import json
import os
import requests
from typing import Dict, Any, List
from shared.utils import get_snowpark_session, application_name

logger = logging.getLogger(application_name)

class CortexAgentRunner:
    """Run experiments with Snowflake Cortex Agent via REST API."""
    
    def __init__(self, agent_name: str = "math_agent"):
        self.agent_name = agent_name
        self.session = get_snowpark_session()
        self.config = self._get_rest_api_config()
        
    def _get_rest_api_config(self) -> Dict[str, str]:
        """Get Snowflake REST API configuration."""
        # Get OAuth token - Cortex Agent requires OAuth (PAT)
        # Try SNOWFLAKE_PAT first (OAuth token), fallback to session token
        token = os.getenv("SNOWFLAKE_PAT")
        if not token:
            # Fallback to session token (though this may not work for agent:run)
            token = self.session.connection.rest.token
            logger.warning("Using session token - Cortex Agent may require SNOWFLAKE_PAT")

        # Use host directly from connection
        base_url = f"https://{self.session.connection.host}"

        return {
            "base_url": base_url,
            "token": token
        }
    
    def run_query(self, query: str) -> Dict[str, Any]:
        """Run a query through Cortex Agent with streaming.

        Args:
            query: Natural language query

        Returns:
            Dict with response and metadata
        """
        start_time = time.time()

        # Get fresh config with current token for each request
        config = self._get_rest_api_config()

        url = f"{config['base_url']}/api/v2/databases/AI_FDE/schemas/CACHE_EXPERIMENTS/agents/{self.agent_name}:run"

        headers = {
            "Authorization": f'Bearer {config["token"]}',
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }

        # Don't specify thread_id - let Snowflake auto-create a new thread
        body = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": query
                        }
                    ]
                }
            ]
        }
        
        # Stream response
        response_text = ""
        final_response = None
        
        try:
            response = requests.post(url, headers=headers, json=body, stream=True)

            # Get detailed error info before raising
            if response.status_code == 401:
                logger.error(f"401 Unauthorized - Response body: {response.text}")
                logger.error(f"Request URL: {url}")
                logger.error(f"Request headers: {headers}")

            response.raise_for_status()
            
            # Parse SSE stream
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    
                    # SSE format: "data: <json>"
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]  # Remove 'data: ' prefix
                        try:
                            data = json.loads(data_str)
                            
                            # Look for final 'response' event with role=assistant
                            if isinstance(data, dict) and data.get('role') == 'assistant':
                                final_response = data
                                
                                # Extract text from content
                                for content_item in data.get('content', []):
                                    if content_item.get('type') == 'text':
                                        response_text = content_item.get('text', '')
                        except json.JSONDecodeError:
                            pass
            
            latency_ms = (time.time() - start_time) * 1000
            
            return {
                "query": query,
                "response": response_text,
                "latency_ms": latency_ms,
                "metadata": final_response
            }
            
        except Exception as e:
            logger.error(f"Error running query: {e}")
            latency_ms = (time.time() - start_time) * 1000
            return {
                "query": query,
                "response": f"Error: {str(e)}",
                "latency_ms": latency_ms,
                "metadata": {"error": str(e)}
            }
    
    def run_dataset(self, dataset_path: str) -> Dict[str, Any]:
        """Run all queries from dataset.
        
        Args:
            dataset_path: Path to test dataset JSON
            
        Returns:
            Results dict with metrics
        """
        with open(dataset_path, 'r') as f:
            data = json.load(f)
        test_cases = data['test_cases']
        
        results = []
        total_latency = 0
        
        logger.info(f"Running {len(test_cases)} queries through Cortex Agent...")
        
        for i, tc in enumerate(test_cases, 1):
            logger.info(f"  [{i}/{len(test_cases)}] {tc['query']}")
            result = self.run_query(tc['query'])
            results.append(result)
            total_latency += result['latency_ms']
            logger.info(f"    Response: {result['response'][:100]}...")
            logger.info(f"    Latency: {result['latency_ms']:.0f}ms")
        
        avg_latency = total_latency / len(test_cases) if test_cases else 0
        
        return {
            "experiment": "cortex_agent",
            "total_queries": len(test_cases),
            "total_latency_ms": total_latency,
            "avg_latency_ms": avg_latency,
            "results": results
        }


def main():
    """Test Cortex Agent runner."""
    logging.basicConfig(level=logging.INFO)
    
    runner = CortexAgentRunner()
    results = runner.run_dataset("datasets/math_operations.json")
    
    print("=" * 80)
    print("CORTEX AGENT RESULTS")
    print("=" * 80)
    print(f"Total queries: {results['total_queries']}")
    print(f"Total latency: {results['total_latency_ms']:.0f}ms")
    print(f"Avg latency: {results['avg_latency_ms']:.0f}ms")
    print("=" * 80)


if __name__ == "__main__":
    main()
