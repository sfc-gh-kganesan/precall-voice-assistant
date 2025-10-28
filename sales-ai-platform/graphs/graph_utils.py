import os
from langchain_openai import ChatOpenAI

def get_llm():
    """
    Get LLM configured for either Snowflake Cortex or OpenAI.
    
    When SNOWFLAKE_HOST is set, uses Cortex inference.
    Otherwise, uses OpenAI (requires OPENAI_API_KEY).
    
    Note: For Cortex, token is read fresh each call to handle rotation.
    """
    snowflake_host = os.getenv('SNOWFLAKE_HOST')
    
    if snowflake_host:
        # Use Snowflake Cortex inference - read token fresh each time
        from utils import get_snowflake_token
        
        base_url = f'https://{snowflake_host}/api/v2/cortex/openai'
        api_key = get_snowflake_token()  # Fresh token on each call
        
        llm = ChatOpenAI(
            # model="claude-3-5-sonnet",
            # model="claude-3-7-sonnet",
            model="openai-gpt-4.1",
            base_url=base_url,
            api_key=api_key,
            temperature=0,
            max_retries=5,
            request_timeout=20
        )
    else:
        # Use OpenAI directly
        print("Using OpenAI")
        llm = ChatOpenAI(
            # model="gpt-5",
            model="gpt-4",
            temperature=0,
            max_retries=5,
            request_timeout=20
        )
    
    return llm