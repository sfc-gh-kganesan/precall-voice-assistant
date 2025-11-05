"""
Snowflake database connection management.
Provides connection pooling and query execution for all database operations.
"""

import snowflake.connector
import logging
from typing import Optional, Dict, Any
import pandas as pd

from app.config import settings

logger = logging.getLogger(__name__)


class SnowflakeConnectionManager:
    """
    Manages Snowflake connections for read and write operations.
    Implements connection pooling and provides query execution utilities.
    """

    def __init__(self):
        """Initialize connection manager with configuration from settings"""
        self._read_conn: Optional[snowflake.connector.SnowflakeConnection] = None
        self._write_conn: Optional[snowflake.connector.SnowflakeConnection] = None
        self._query_catalog_conn: Optional[snowflake.connector.SnowflakeConnection] = (
            None
        )

    def _create_connection(
        self, warehouse: str, schema: str, role: str
    ) -> snowflake.connector.SnowflakeConnection:
        """
        Create a Snowflake connection with specified parameters.

        Args:
            warehouse: Snowflake warehouse name
            schema: Snowflake schema name
            role: Snowflake role name

        Returns:
            SnowflakeConnection: Active Snowflake connection
        """
        try:
            conn = snowflake.connector.connect(
                user=settings.SNOWFLAKE_USER,
                password=settings.SNOWFLAKE_PASSWORD,
                account=settings.SNOWFLAKE_ACCOUNT,
                warehouse=warehouse,
                database=settings.SNOWFLAKE_DATABASE,
                schema=schema,
                role=role,
                protocol="https",
                client_session_keep_alive=True,
            )

            # Explicitly activate warehouse, database, and schema context
            # Even though these are passed to connect(), Snowflake doesn't always activate them
            try:
                cursor = conn.cursor()
                cursor.execute(f"USE WAREHOUSE {warehouse}")
                cursor.execute(f"USE DATABASE {settings.SNOWFLAKE_DATABASE}")
                cursor.execute(f"USE SCHEMA {schema}")
                cursor.close()
                logger.info(
                    f"Activated context: warehouse={warehouse}, "
                    f"database={settings.SNOWFLAKE_DATABASE}, schema={schema}"
                )
            except Exception as ctx_error:
                logger.warning(f"Could not activate context: {ctx_error}")
                # Continue anyway - the params in connect() might have worked

            logger.info(
                f"Created Snowflake connection: warehouse={warehouse}, "
                f"schema={schema}, role={role}"
            )
            return conn
        except Exception as e:
            logger.error(f"Failed to create Snowflake connection: {e}")
            raise

    def get_read_connection(self) -> snowflake.connector.SnowflakeConnection:
        """
        Get or create read-only connection.
        Used for all SELECT queries.

        Returns:
            SnowflakeConnection: Read connection with CXE schema access
        """
        if self._read_conn is None or self._read_conn.is_closed():
            self._read_conn = self._create_connection(
                warehouse=settings.SNOWFLAKE_WAREHOUSE,
                schema="CXE",
                role=settings.SNOWFLAKE_ROLE,
            )
        return self._read_conn

    def get_write_connection(self) -> snowflake.connector.SnowflakeConnection:
        """
        Get or create write connection.
        Used for INSERT, UPDATE, DELETE operations (e.g., analytics tracking).

        Returns:
            SnowflakeConnection: Write connection with CXE_META schema access
        """
        if self._write_conn is None or self._write_conn.is_closed():
            self._write_conn = self._create_connection(
                warehouse=settings.SNOWFLAKE_WAREHOUSE,
                schema="CXE_META",
                role=settings.SNOWFLAKE_ROLE,
            )
        return self._write_conn

    def get_query_catalog_connection(self) -> snowflake.connector.SnowflakeConnection:
        """
        Get or create query catalog connection.
        Used for stored procedure calls and query catalog operations.

        Returns:
            SnowflakeConnection: Query catalog connection
        """
        if self._query_catalog_conn is None or self._query_catalog_conn.is_closed():
            self._query_catalog_conn = self._create_connection(
                warehouse=settings.SNOWFLAKE_WAREHOUSE,
                schema="CXE",
                role=settings.SNOWFLAKE_ROLE,
            )
        return self._query_catalog_conn

    def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        connection_type: str = "READ",
    ) -> pd.DataFrame:
        """
        Execute a query and return results as a DataFrame.

        Args:
            query: SQL query string with %(param)s placeholders
            params: Dictionary of parameter values
            connection_type: "READ", "WRITE", or "QUERY_CATALOG"

        Returns:
            DataFrame: Query results

        Raises:
            Exception: If query execution fails
        """
        if connection_type == "READ":
            conn = self.get_read_connection()
        elif connection_type == "WRITE":
            conn = self.get_write_connection()
        elif connection_type == "QUERY_CATALOG":
            conn = self.get_query_catalog_connection()
        else:
            raise ValueError(f"Invalid connection_type: {connection_type}")

        try:
            cursor = conn.cursor()
            cursor.execute(query, params=params)

            # For query catalog calls, manually construct DataFrame
            if connection_type == "QUERY_CATALOG":
                result = cursor.fetchall()
                columns = [metadata[0] for metadata in cursor.description]
                df = pd.DataFrame(result, columns=columns)
            else:
                df = cursor.fetch_pandas_all()

            logger.debug(f"Executed query, returned {len(df)} rows")
            return df

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            logger.error(f"Query: {query[:200]}...")  # Log first 200 chars
            raise

    def execute_query_async(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        connection_type: str = "READ",
    ) -> str:
        """
        Execute a query asynchronously and return query ID.
        Use get_async_results() to retrieve results later.

        Args:
            query: SQL query string
            params: Dictionary of parameter values
            connection_type: "READ" or "WRITE"

        Returns:
            str: Snowflake query ID (sfqid)
        """
        if connection_type == "READ":
            conn = self.get_read_connection()
        elif connection_type == "WRITE":
            conn = self.get_write_connection()
        else:
            raise ValueError(f"Invalid connection_type: {connection_type}")

        try:
            cursor = conn.cursor()
            cursor.execute_async(query, params=params)
            query_id = cursor.sfqid
            logger.info(f"Started async query: {query_id}")
            return query_id

        except Exception as e:
            logger.error(f"Async query execution failed: {e}")
            raise

    def get_async_results(self, query_id: str) -> pd.DataFrame:
        """
        Get results from an async query by query ID.

        Args:
            query_id: Snowflake query ID from execute_query_async()

        Returns:
            DataFrame: Query results
        """
        conn = self.get_read_connection()
        cursor = conn.cursor()

        try:
            # Create cursor from query ID
            cursor.get_results_from_sfqid(query_id)
            df = cursor.fetch_pandas_all()
            logger.info(f"Retrieved async query results: {query_id}")
            return df

        except Exception as e:
            logger.error(f"Failed to get async results for {query_id}: {e}")
            raise

    def close_all_connections(self):
        """Close all active connections"""
        for conn in [self._read_conn, self._write_conn, self._query_catalog_conn]:
            if conn is not None:
                try:
                    conn.close()
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")

        self._read_conn = None
        self._write_conn = None
        self._query_catalog_conn = None
        logger.info("Closed all Snowflake connections")


# Global connection manager instance
_connection_manager: Optional[SnowflakeConnectionManager] = None


def get_connection_manager() -> SnowflakeConnectionManager:
    """
    Get or create the global connection manager instance.

    Returns:
        SnowflakeConnectionManager: Global connection manager
    """
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = SnowflakeConnectionManager()
    return _connection_manager


# Convenience functions for direct use
def execute_query(query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """Execute a read query and return DataFrame"""
    return get_connection_manager().execute_query(query, params, "READ")


def execute_write_query(
    query: str, params: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """Execute a write query and return DataFrame"""
    return get_connection_manager().execute_query(query, params, "WRITE")


def execute_query_async(query: str, params: Optional[Dict[str, Any]] = None) -> str:
    """Execute an async query and return query ID"""
    return get_connection_manager().execute_query_async(query, params, "READ")


def get_async_results(query_id: str) -> pd.DataFrame:
    """Get results from async query"""
    return get_connection_manager().get_async_results(query_id)
