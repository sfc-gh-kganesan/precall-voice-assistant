"""
Warehouse Service - Business logic for warehouse operations.

This service handles all warehouse-related operations including warehouse details,
chart data, change history, and event overlays.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from app.queries.warehouse_queries import WarehouseViewQueries
from app.services.base import BaseService

logger = logging.getLogger(__name__)


class WarehouseService(BaseService):
    """Service for warehouse operations."""

    def __init__(self):
        super().__init__()
        self.queries = WarehouseViewQueries()

    def get_warehouse_details(
        self, deployment: str, account_id: int, warehouse_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get current warehouse configuration.

        Returns detailed information including:
        - Warehouse size, type, cluster configuration
        - Auto-suspend/resume settings
        - Scaling policy
        - Created/updated timestamps

        Args:
            deployment: Snowflake deployment
            account_id: Account ID
            warehouse_name: Warehouse name

        Returns:
            Dictionary with warehouse details, or None if not found
        """
        logger.info(
            f"Fetching warehouse details for: {warehouse_name} (account_id: {account_id})"
        )

        params = {
            "account_id": account_id,
            "dda_snwflk_deployment": deployment,
            "warehouse_name": warehouse_name,
        }

        result_df = self.execute_query(
            self.queries.get_warehouse_details_query, params, use_cache=True
        )

        if result_df.empty:
            logger.warning(
                f"No warehouse found: {warehouse_name} in account {account_id}"
            )
            return None

        # Convert first row to dictionary
        details = result_df.iloc[0].to_dict()

        # Convert timestamps to ISO format if present
        for date_field in [
            "CREATED_ON",
            "UPDATED_ON",
            "DELETED_ON",
            "LAST_PROVISIONED_ON",
        ]:
            if date_field in details and details[date_field] is not None:
                details[date_field] = details[date_field].isoformat()

        return details

    def get_warehouse_details_at_query_time(
        self, deployment: str, account_id: int, query_uuid: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get warehouse configuration at the time a specific query ran.

        Args:
            deployment: Snowflake deployment
            account_id: Account ID
            query_uuid: Query UUID

        Returns:
            Dictionary with warehouse details at query time, or None if not found
        """
        logger.info(
            f"Fetching warehouse details at query time for query_uuid: {query_uuid}"
        )

        params = {
            "account_id": account_id,
            "dda_snwflk_deployment": deployment,
            "query_uuid": query_uuid,
        }

        result_df = self.execute_query(
            self.queries.get_warehouse_details_at_query_run, params, use_cache=True
        )

        if result_df.empty:
            logger.warning(
                f"No warehouse configuration found for query_uuid: {query_uuid}"
            )
            return None

        # Convert first row to dictionary
        details = result_df.iloc[0].to_dict()
        return details

    def get_chart_time_range(
        self, deployment: str, account_id: int, warehouse_name: str
    ) -> Dict[str, Optional[str]]:
        """
        Get start and end timestamps for available chart data.

        Args:
            deployment: Snowflake deployment
            account_id: Account ID
            warehouse_name: Warehouse name

        Returns:
            Dictionary with start_time and end_time (ISO format)
        """
        logger.info(f"Fetching chart time range for warehouse: {warehouse_name}")

        params = {
            "account_id": account_id,
            "dda_snwflk_deployment": deployment,
            "warehouse_name": warehouse_name,
        }

        # Get start time
        start_df = self.execute_query(
            self.queries.get_warehouse_charts_start_time, params, use_cache=True
        )
        start_time = None
        if not start_df.empty and start_df.iloc[0]["START_TIME"] is not None:
            start_time = start_df.iloc[0]["START_TIME"].isoformat()

        # Get end time
        end_df = self.execute_query(
            self.queries.get_warehouse_charts_end_time, params, use_cache=True
        )
        end_time = None
        if not end_df.empty and end_df.iloc[0]["END_TIME"] is not None:
            end_time = end_df.iloc[0]["END_TIME"].isoformat()

        return {"start_time": start_time, "end_time": end_time}

    def get_change_history(
        self, deployment: str, account_id: int, warehouse_name: str
    ) -> List[Dict[str, Any]]:
        """
        Get warehouse change history (last 30 days).

        Args:
            deployment: Snowflake deployment
            account_id: Account ID
            warehouse_name: Warehouse name

        Returns:
            List of warehouse changes with timestamp, event type, old/new values
        """
        logger.info(f"Fetching change history for warehouse: {warehouse_name}")

        params = {
            "account_id": account_id,
            "dda_snwflk_deployment": deployment,
            "warehouse_name": warehouse_name,
        }

        result_df = self.execute_query(
            self.queries.get_change_history_for_warehouse, params, use_cache=True
        )

        if result_df.empty:
            logger.info(f"No change history found for warehouse: {warehouse_name}")
            return []

        # Replace NaN values with None for JSON serialization (efficient DataFrame operation)
        result_df = result_df.where(pd.notnull(result_df), None)

        # Convert to dict and format timestamps
        changes = result_df.to_dict(orient="records")
        for change in changes:
            if "timestamp" in change and change["timestamp"] is not None:
                change["timestamp"] = change["timestamp"].isoformat()

        logger.info(f"Found {len(changes)} warehouse changes")
        return changes

    def get_warehouse_chart_data(
        self,
        deployment: str,
        account_id: int,
        warehouse_name: str,
        chart_type: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Get warehouse-level chart data.

        Args:
            deployment: Snowflake deployment
            account_id: Account ID
            warehouse_name: Warehouse name
            chart_type: Chart type (EXECUTED_JOBS, ACTIVE_CLUSTERS, XP_RETRY_JOBS, SUCCESS_FAILURE_RATIO)
            start_time: Start timestamp
            end_time: End timestamp

        Returns:
            List of chart data points
        """
        logger.info(f"Fetching warehouse chart data: {chart_type} for {warehouse_name}")

        try:
            sp_call = self.queries.get_warehouse_chart_sp_call(chart_type)
        except ValueError as e:
            logger.error(f"Invalid chart type: {e}")
            raise

        params = {
            "deployment": deployment,
            "account_id": account_id,
            "warehouse_name": warehouse_name,
            "start_time": start_time,
            "end_time": end_time,
        }

        result_df = self.execute_query(sp_call, params, use_cache=False)

        if result_df.empty:
            logger.info(f"No chart data found for {chart_type}")
            return []

        # Convert to list of dicts
        chart_data = result_df.to_dict(orient="records")

        # Convert any timestamp columns to ISO format
        for row in chart_data:
            for key, value in row.items():
                if isinstance(value, datetime):
                    row[key] = value.isoformat()

        logger.info(f"Found {len(chart_data)} data points for {chart_type}")
        return chart_data

    def get_cluster_chart_data(
        self,
        deployment: str,
        account_id: int,
        warehouse_name: str,
        cluster_num: int,
        chart_type: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Get cluster-level chart data.

        Args:
            deployment: Snowflake deployment
            account_id: Account ID
            warehouse_name: Warehouse name
            cluster_num: Cluster number (1-based)
            chart_type: Chart type (JOB_QUEUE_TRANSITION, JOB_BLOCKED_TRANSITION, QUEUE_TOTAL_TIME, BLOCKED_TOTAL_TIME)
            start_time: Start timestamp
            end_time: End timestamp

        Returns:
            List of chart data points
        """
        logger.info(
            f"Fetching cluster chart data: {chart_type} for {warehouse_name} cluster {cluster_num}"
        )

        try:
            sp_call = self.queries.get_cluster_chart_sp_call(chart_type)
        except ValueError as e:
            logger.error(f"Invalid chart type: {e}")
            raise

        params = {
            "deployment": deployment,
            "account_id": account_id,
            "warehouse_name": warehouse_name,
            "cluster_num": cluster_num,
            "start_time": start_time,
            "end_time": end_time,
        }

        result_df = self.execute_query(sp_call, params, use_cache=False)

        if result_df.empty:
            logger.info(f"No chart data found for {chart_type}")
            return []

        # Convert to list of dicts
        chart_data = result_df.to_dict(orient="records")

        # Convert any timestamp columns to ISO format
        for row in chart_data:
            for key, value in row.items():
                if isinstance(value, datetime):
                    row[key] = value.isoformat()

        logger.info(f"Found {len(chart_data)} data points for {chart_type}")
        return chart_data

    def get_event_overlays(
        self,
        deployment: str,
        account_id: int,
        warehouse_name: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Get warehouse events for chart overlays.

        Args:
            deployment: Snowflake deployment
            account_id: Account ID
            warehouse_name: Warehouse name
            start_time: Start timestamp
            end_time: End timestamp

        Returns:
            List of events with timestamp, type, and description
        """
        logger.info(f"Fetching event overlays for warehouse: {warehouse_name}")

        params = {
            "account_id": account_id,
            "dda_snwflk_deployment": deployment,
            "warehouse_name": warehouse_name,
            "start_time": start_time,
            "end_time": end_time,
        }

        result_df = self.execute_query(
            self.queries.get_warehouse_level_overlays, params, use_cache=True
        )

        if result_df.empty:
            logger.info(f"No events found for warehouse: {warehouse_name}")
            return []

        # Convert timestamps
        events = result_df.to_dict(orient="records")
        for event in events:
            if "EVENT_TIMESTAMP" in event and event["EVENT_TIMESTAMP"] is not None:
                event["EVENT_TIMESTAMP"] = event["EVENT_TIMESTAMP"].isoformat()

        logger.info(f"Found {len(events)} events")
        return events
