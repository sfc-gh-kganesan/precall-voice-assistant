"""Snowflake Cortex Search Service client for searching documentation."""

import logging

import httpx

logger = logging.getLogger(__name__)


class CortexSearchClient:
    """Client for Snowflake Cortex Search Service.

    Provides access to Snowflake documentation search via Cortex Search Service REST API.
    Uses same password-based authentication as Cortex LLM calls.
    """

    def __init__(
        self,
        account: str,
        password: str,
        service_name: str = "cke_snowflake_docs_service",
        database: str = "snowflake_docs_cke",
        schema: str = "shared",
        timeout: int = 30,
    ):
        """Initialize Cortex Search client.

        Args:
            account: Snowflake account identifier
            password: Snowflake password (used as bearer token)
            service_name: Cortex Search service name
            database: Database name
            schema: Schema name
            timeout: Request timeout in seconds
        """
        self.account = account
        self.password = password
        self.service_name = service_name
        self.database = database
        self.schema = schema
        self.timeout = timeout

        # Construct the full service URL
        self.service_url = (
            f"https://{account}.snowflakecomputing.com/api/v2/databases/{database}/schemas/{schema}"
            f"/cortex-search-services/{service_name}:query"
        )

        logger.info(f"Initialized Cortex Search client for service: {service_name}")

    async def search(
        self,
        query: str,
        columns: list[str] | None = None,
        limit: int = 10,
        weights: dict[str, float] | None = None,
    ) -> dict:
        """Search Snowflake documentation using Cortex Search Service.

        Args:
            query: Search query string
            columns: Columns to return (default: ["CHUNK", "DOCUMENT_TITLE", "SOURCE_URL"])
            limit: Maximum number of results (default: 10)
            weights: Scoring weights for texts/vectors/reranker

        Returns:
            Search results with relevant documentation chunks

        Raises:
            httpx.HTTPError: If the API request fails
        """
        if columns is None:
            columns = ["CHUNK", "DOCUMENT_TITLE", "SOURCE_URL"]

        if weights is None:
            weights = {
                "texts": 1,
                "vectors": 1,
                "reranker": 1,
            }

        payload = {
            "query": query,
            "columns": columns,
            "scoring_config": {
                "weights": weights,
            },
            "limit": limit,
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.password}",  # Snowflake Cortex Search API format
        }

        logger.debug(f"Searching Cortex Search with query: {query[:100]}...")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    self.service_url,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()

                results = response.json()
                result_count = len(results.get("results", []))
                logger.info(
                    f"Cortex Search returned {result_count} results for query: {query[:50]}..."
                )

                return results

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"Cortex Search API error: {e.response.status_code} - {e.response.text}"
                )
                raise
            except httpx.RequestError as e:
                logger.error(f"Cortex Search request failed: {e}")
                raise

    def format_results(self, results: dict) -> str:
        """Format search results into a readable string.

        Args:
            results: Raw results from Cortex Search API

        Returns:
            Formatted string with documentation chunks, titles, and URLs
        """
        if not results or "results" not in results:
            return "No results found."

        formatted = []
        for idx, result in enumerate(results["results"], 1):
            chunk = result.get("CHUNK", "")
            title = result.get("DOCUMENT_TITLE", "Untitled")
            url = result.get("SOURCE_URL", "")

            if chunk:
                result_text = f"[Result {idx}]"
                if title:
                    result_text += f"\nTitle: {title}"
                if url:
                    result_text += f"\nSource: {url}"
                result_text += f"\n\n{chunk}"
                formatted.append(result_text)

        if not formatted:
            return "No documentation chunks found."

        return "\n\n---\n\n".join(formatted)
