import os

from langchain_openai import ChatOpenAI

from utils import get_snowflake_token


def get_llm(cortex_model_selection: str = "openai-gpt-4.1"):
    """
    Get LLM configured for either Snowflake Cortex or OpenAI.
    Note: For Cortex, token is read fresh each call to handle rotation.
    """
    llm_provider = os.getenv("LLM_PROVIDER")
    if llm_provider == "openai":
        if os.getenv("OPENAI_API_KEY") is None:
            raise Exception("OPENAI_API_KEY is not set")
        print("get_llm: using OpenAI")
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_retries=5, request_timeout=20)
        return llm
    else:
        snowflake_host = os.getenv("SNOWFLAKE_HOST")
        if snowflake_host is None:
            raise Exception("SNOWFLAKE_HOST is not set")
        print("get_llm: using Snowflake Cortex")
        base_url = f"https://{snowflake_host}/api/v2/cortex/openai"
        api_key = get_snowflake_token()  # Fresh token on each call
        llm = ChatOpenAI(
            model=cortex_model_selection,
            base_url=base_url,
            api_key=api_key,
            temperature=0,
            max_retries=5,
            request_timeout=20,
        )
        return llm
