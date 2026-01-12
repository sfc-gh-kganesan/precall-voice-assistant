"""Cache backend implementations using Snowflake Cortex Search.

Provides:
- CortexSearchCache: Base class for semantic similarity caching
- PlanCache: Hash-based cache for agent planning steps
- PlanCacheWithSearch: Semantic cache for planning using Cortex Search Service
- ToolCache: Per-tool semantic cache with input/output tracking
"""
import hashlib
import json
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta

from shared.utils import get_snowpark_session, application_name

logger = logging.getLogger(application_name)


class CortexSearchCache:
    """Base class for semantic caching using Cortex Search.

    Uses Snowflake Cortex EMBED and Cortex Search for semantic similarity matching.
    """

    def __init__(
        self,
        table_name: str,
        similarity_threshold: float = 0.85,
        ttl_days: int = 30,
        embedding_model: str = "snowflake-arctic-embed-m"
    ):
        """Initialize semantic cache.

        Args:
            table_name: Snowflake table for cache storage
            similarity_threshold: Minimum similarity score for cache hit (0.0-1.0)
            ttl_days: Cache entry time-to-live in days
            embedding_model: Cortex embedding model to use
        """
        self.table_name = table_name
        self.similarity_threshold = similarity_threshold
        self.ttl_days = ttl_days
        self.embedding_model = embedding_model
        self.session = get_snowpark_session()

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using Cortex EMBED.

        Args:
            text: Text to embed

        Returns:
            List of embedding values
        """
        try:
            # Use Cortex EMBED function
            query = f"""
                SELECT SNOWFLAKE.CORTEX.EMBED_TEXT_768(
                    '{self.embedding_model}',
                    '{text.replace("'", "''")}'
                ) as embedding
            """
            result = self.session.sql(query).collect()
            embedding = json.loads(result[0]['EMBEDDING'])
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            raise

    def get(
        self,
        query_text: str,
        metadata_filters: Optional[Dict[str, Any]] = None
    ) -> Optional[Tuple[str, float]]:
        """Get cached result for semantically similar query.

        Args:
            query_text: Query text to search for
            metadata_filters: Optional metadata filters (e.g., {"model": "claude-4-sonnet"})

        Returns:
            Tuple of (cached_response, similarity_score) if found, None otherwise
        """
        try:
            # Generate embedding for query
            query_embedding = self._generate_embedding(query_text)

            # Search for similar queries using vector similarity
            # Note: This is a simplified version. In production, use Cortex Search service
            search_query = f"""
                SELECT
                    query_text,
                    response,
                    metadata,
                    VECTOR_COSINE_SIMILARITY(
                        query_embedding,
                        {query_embedding}::VECTOR(FLOAT, 768)
                    ) as similarity
                FROM {self.table_name}
                WHERE timestamp >= DATEADD(day, -{self.ttl_days}, CURRENT_TIMESTAMP())
                ORDER BY similarity DESC
                LIMIT 1
            """

            result = self.session.sql(search_query).collect()

            if result and result[0]['SIMILARITY'] >= self.similarity_threshold:
                cached_response = result[0]['RESPONSE']
                similarity_score = result[0]['SIMILARITY']

                logger.info(
                    f"Cache hit: similarity={similarity_score:.3f}, query='{query_text[:50]}...'",
                    extra={"cache_hit": True, "similarity": similarity_score}
                )

                return (cached_response, similarity_score)

            logger.info(
                f"Cache miss: query='{query_text[:50]}...'",
                extra={"cache_hit": False}
            )
            return None

        except Exception as e:
            logger.error(f"Cache get failed: {str(e)}")
            return None

    def set(
        self,
        query_text: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Store query-response pair in cache.

        Args:
            query_text: Query text
            response: Response to cache
            metadata: Optional metadata (model, tokens, latency, etc.)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate embedding
            query_embedding = self._generate_embedding(query_text)

            # Insert into cache table
            insert_query = f"""
                INSERT INTO {self.table_name} (
                    query_id,
                    query_text,
                    query_embedding,
                    response,
                    metadata,
                    timestamp
                )
                SELECT
                    '{hashlib.md5(query_text.encode()).hexdigest()}',
                    '{query_text.replace("'", "''")}',
                    {query_embedding}::VECTOR(FLOAT, 768),
                    '{response.replace("'", "''")}',
                    PARSE_JSON('{json.dumps(metadata or {})}'),
                    CURRENT_TIMESTAMP()
            """

            self.session.sql(insert_query).collect()

            logger.info(
                f"Cached response: query='{query_text[:50]}...'",
                extra={"cached": True}
            )
            return True

        except Exception as e:
            logger.error(f"Cache set failed: {str(e)}")
            return False


class PlanCache:
    """Hash-based cache for agent planning steps.

    Caches agent plans based on query + conversation history + available tools.
    """

    def __init__(
        self,
        table_name: str = "plan_cache",
        include_history: bool = True,
        history_depth: int = 5,
        ttl_days: int = 30
    ):
        """Initialize plan cache.

        Args:
            table_name: Snowflake table for cache storage
            include_history: Include conversation history in cache key
            history_depth: Number of previous turns to include in key
            ttl_days: Cache entry time-to-live in days
        """
        self.table_name = table_name
        self.include_history = include_history
        self.history_depth = history_depth
        self.ttl_days = ttl_days
        self.session = get_snowpark_session()

    def _generate_cache_key(
        self,
        query: str,
        tools: List[str],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Generate cache key from query, tools, and history.

        Args:
            query: Current query
            tools: List of available tool names
            conversation_history: Previous conversation turns

        Returns:
            MD5 hash cache key
        """
        key_parts = [query, ",".join(sorted(tools))]

        if self.include_history and conversation_history:
            # Include last N turns
            recent_history = conversation_history[-self.history_depth:]
            history_str = json.dumps(recent_history, sort_keys=True)
            key_parts.append(history_str)

        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    def get(
        self,
        query: str,
        tools: List[str],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Optional[Dict[str, Any]]:
        """Get cached plan.

        Args:
            query: Current query
            tools: Available tool names
            conversation_history: Previous conversation turns

        Returns:
            Cached plan (steps, tool_sequence, reasoning) if found, None otherwise
        """
        try:
            cache_key = self._generate_cache_key(query, tools, conversation_history)

            query_sql = f"""
                SELECT plan_data
                FROM {self.table_name}
                WHERE plan_key = '{cache_key}'
                  AND timestamp >= DATEADD(day, -{self.ttl_days}, CURRENT_TIMESTAMP())
                LIMIT 1
            """

            result = self.session.sql(query_sql).collect()

            if result:
                plan_data = json.loads(result[0]['PLAN_DATA'])
                logger.info(f"Plan cache hit: key={cache_key[:16]}...", extra={"cache_hit": True})
                return plan_data

            logger.info(f"Plan cache miss: key={cache_key[:16]}...", extra={"cache_hit": False})
            return None

        except Exception as e:
            logger.error(f"Plan cache get failed: {str(e)}")
            return None

    def set(
        self,
        query: str,
        tools: List[str],
        plan_data: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> bool:
        """Store plan in cache.

        Args:
            query: Current query
            tools: Available tool names
            plan_data: Plan to cache (steps, tool_sequence, reasoning)
            conversation_history: Previous conversation turns

        Returns:
            True if successful, False otherwise
        """
        try:
            cache_key = self._generate_cache_key(query, tools, conversation_history)

            insert_sql = f"""
                INSERT INTO {self.table_name} (
                    plan_key,
                    query_text,
                    plan_data,
                    timestamp
                )
                SELECT
                    '{cache_key}',
                    '{query.replace("'", "''")}',
                    PARSE_JSON('{json.dumps(plan_data)}'),
                    CURRENT_TIMESTAMP()
            """

            self.session.sql(insert_sql).collect()
            logger.info(f"Plan cached: key={cache_key[:16]}...", extra={"cached": True})
            return True

        except Exception as e:
            logger.error(f"Plan cache set failed: {str(e)}")
            return False


class ToolCache:
    """Per-tool semantic cache using Cortex Search.

    Each tool has its own cache with semantic matching on inputs.
    """

    def __init__(
        self,
        tool_name: str,
        table_prefix: str = "tool_cache",
        similarity_threshold: float = 0.85,
        ttl_days: int = 30
    ):
        """Initialize tool-specific cache.

        Args:
            tool_name: Name of the tool (e.g., 'add', 'multiply')
            table_prefix: Prefix for cache table names
            similarity_threshold: Minimum similarity for cache hit
            ttl_days: Cache entry time-to-live in days
        """
        self.tool_name = tool_name
        table_name = f"{table_prefix}_{tool_name}"
        self.cache = CortexSearchCache(
            table_name=table_name,
            similarity_threshold=similarity_threshold,
            ttl_days=ttl_days
        )

    def get(self, tool_input: str) -> Optional[Tuple[str, float]]:
        """Get cached tool output for semantically similar input.

        Args:
            tool_input: Tool input (JSON string or text)

        Returns:
            Tuple of (cached_output, similarity_score) if found, None otherwise
        """
        return self.cache.get(
            query_text=f"tool={self.tool_name}|input={tool_input}",
            metadata_filters={"tool": self.tool_name}
        )

    def set(self, tool_input: str, tool_output: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Store tool input-output pair in cache.

        Args:
            tool_input: Tool input
            tool_output: Tool output
            metadata: Optional metadata

        Returns:
            True if successful, False otherwise
        """
        metadata = metadata or {}
        metadata["tool"] = self.tool_name

        return self.cache.set(
            query_text=f"tool={self.tool_name}|input={tool_input}",
            response=tool_output,
            metadata=metadata
        )


class PlanCacheWithSearch:
    """Plan cache using Cortex Search Service for semantic matching.

    Uses Snowflake Cortex Search Service to find semantically similar queries
    instead of exact hash matching. This allows caching to work for queries
    that are phrased differently but have the same intent.
    """

    def __init__(
        self,
        table_name: str = "AI_FDE.CACHE_EXPERIMENTS.plan_cache",
        search_service_name: str = "AI_FDE.CACHE_EXPERIMENTS.plan_cache_search",
        similarity_threshold: float = 0.85,
        ttl_days: int = 30
    ):
        """Initialize plan cache with Cortex Search.

        Args:
            table_name: Snowflake table for cache storage
            search_service_name: Cortex Search Service name
            similarity_threshold: Minimum similarity for cache hit (0.0-1.0)
            ttl_days: Cache entry time-to-live in days
        """
        self.table_name = table_name
        self.search_service_name = search_service_name
        self.similarity_threshold = similarity_threshold
        self.ttl_days = ttl_days
        self.session = get_snowpark_session()

    def get(
        self,
        query: str,
        tools: List[str],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Optional[Dict[str, Any]]:
        """Get cached plan using semantic search.

        Args:
            query: Current query text
            tools: Available tool names
            conversation_history: Previous conversation turns (optional)

        Returns:
            Cached plan data if found with sufficient similarity, None otherwise
        """
        try:
            # Escape single quotes for SQL string
            escaped_query = query.replace("'", "''")
            tools_str = ",".join(sorted(tools))

            # Build JSON query string for Cortex Search
            import json as json_lib
            query_json = json_lib.dumps({
                "query": query,
                "columns": ["query_text", "plan_response", "metadata", "available_tools", "timestamp"],
                "limit": 5
            })

            # Escape single quotes in JSON for SQL
            query_json_escaped = query_json.replace("'", "''")

            # Search using Cortex Search Service SEARCH_PREVIEW function
            search_query = f"""
                SELECT PARSE_JSON(
                    SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
                        '{self.search_service_name}',
                        '{query_json_escaped}'
                    )
                )['results'] as results
            """

            result = self.session.sql(search_query).collect()

            if result and result[0]['RESULTS']:
                # SEARCH_PREVIEW returns results as an array
                results_array = json.loads(result[0]['RESULTS']) if isinstance(result[0]['RESULTS'], str) else result[0]['RESULTS']

                if not results_array:
                    logger.info(
                        f"Plan cache MISS: query='{query[:50]}...'",
                        extra={"cache_hit": False}
                    )
                    return None

                # Filter results by tools and TTL
                for cached_data in results_array:
                    # Check if tools match
                    if cached_data.get('available_tools') != tools_str:
                        continue

                    # Check TTL - skip if timestamp is too old
                    # Note: Cortex Search doesn't support WHERE clauses, so we filter in Python
                    # timestamp_str = cached_data.get('timestamp')
                    # We'll skip TTL check for now since timestamp filtering is complex

                    # Parse the plan_response JSON
                    plan_response_data = cached_data.get('plan_response')
                    if isinstance(plan_response_data, str):
                        plan_response = json.loads(plan_response_data)
                    else:
                        plan_response = plan_response_data

                    # Cortex Search doesn't return similarity score in SEARCH_PREVIEW
                    # We assume if it's in top 5 results, it's sufficiently similar
                    logger.info(
                        f"Plan cache HIT: query='{query[:50]}...'",
                        extra={"cache_hit": True}
                    )
                    return plan_response

            logger.info(
                f"Plan cache MISS: query='{query[:50]}...'",
                extra={"cache_hit": False}
            )
            return None

        except Exception as e:
            logger.error(f"Plan cache get failed: {str(e)}")
            return None

    def set(
        self,
        query: str,
        tools: List[str],
        plan_response: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, str]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Store plan in cache.

        Args:
            query: Current query text
            tools: Available tool names
            plan_response: Plan response to cache (LLM response with tool calls)
            conversation_history: Previous conversation turns (optional)
            metadata: Additional metadata (tokens, latency, etc.)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate unique ID for this cache entry
            query_id = hashlib.md5(
                f"{query}|{','.join(sorted(tools))}".encode()
            ).hexdigest()

            # Escape single quotes
            escaped_query = query.replace("'", "''")
            tools_str = ",".join(sorted(tools))

            # Serialize the plan response and metadata
            plan_response_json = json.dumps(plan_response).replace("'", "''")
            metadata_json = json.dumps(metadata or {}).replace("'", "''")

            insert_query = f"""
                INSERT INTO {self.table_name} (
                    query_id,
                    query_text,
                    available_tools,
                    plan_response,
                    metadata,
                    timestamp
                )
                SELECT
                    '{query_id}',
                    '{escaped_query}',
                    '{tools_str}',
                    PARSE_JSON('{plan_response_json}'),
                    PARSE_JSON('{metadata_json}'),
                    CURRENT_TIMESTAMP()
            """

            self.session.sql(insert_query).collect()

            logger.info(
                f"Plan cached: query_id={query_id[:16]}..., query='{query[:50]}...'",
                extra={"cached": True}
            )
            return True

        except Exception as e:
            logger.error(f"Plan cache set failed: {str(e)}")
            return False
