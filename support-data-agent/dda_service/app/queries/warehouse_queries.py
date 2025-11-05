"""
Warehouse-related SQL queries for warehouse details, charts, and history.

This module contains SQL queries ported from the original Streamlit application's
WarehouseView to support the Warehouse Service API endpoints.
"""

from app.core.table_mappings import Tables, get_table_name


class WarehouseViewQueries:
    """SQL queries for warehouse operations."""

    # Get current warehouse configuration
    get_warehouse_details_query = f"""
        SELECT
            ID,
            WAREHOUSE_NAME,
            CREATED_ON,
            LAST_PROVISIONED_ON,
            SIZE,
            MIN_CLUSTER_COUNT,
            MAX_CLUSTER_COUNT,
            decode(SCALING_POLICY,
                     'MAXIMIZED','ECONOMY',
                     'AUTO_SCALE','STANDARD',
                     'STANDARD','STANDARD',
                     'LEGACY','LEGACY',
                     'ECONOMY','ECONOMY',
                     'EXTREME','EXTREME'
                   ) AS SCALING_POLICY,
            AUTO_RESUME,
            ENABLE_QUERY_ACCELERATION,
            AUTOSUSPEND_SETTING,
            decode(WAREHOUSE_TYPE,
                     'STANDARD','STANDARD',
                     'HIGH_MEMORY','SNOWPARK_OPTIMIZED'
                   ) AS WAREHOUSE_TYPE,
            UPDATED_ON
        FROM {get_table_name("FDTN_WAREHOUSE_METADATA")}
        WHERE WAREHOUSE_NAME = %(warehouse_name)s
        AND ACCOUNT_ID = %(account_id)s
        AND DEPLOYMENT = %(dda_snwflk_deployment)s
        AND DELETED_ON IS NULL
        ORDER BY UPDATED_ON DESC
        LIMIT 1
    """

    # Get warehouse configuration at the time a specific query ran
    get_warehouse_details_at_query_run = f"""
        SELECT
            wh.ID,
            wh.WAREHOUSE_NAME,
            wh.CREATED_ON,
            wh.LAST_PROVISIONED_ON,
            wh.SIZE,
            wh.MIN_CLUSTER_COUNT,
            wh.MAX_CLUSTER_COUNT,
            decode(wh.SCALING_POLICY,
                     'MAXIMIZED','ECONOMY',
                     'AUTO_SCALE','STANDARD',
                     'STANDARD','STANDARD',
                     'LEGACY','LEGACY',
                     'ECONOMY','ECONOMY',
                     'EXTREME','EXTREME'
                   ) AS SCALING_POLICY,
            wh.AUTO_RESUME,
            wh.ENABLE_QUERY_ACCELERATION,
            wh.AUTOSUSPEND_SETTING,
            decode(wh.WAREHOUSE_TYPE,
                     'STANDARD','STANDARD',
                     'HIGH_MEMORY','SNOWPARK_OPTIMIZED'
                   ) AS WAREHOUSE_TYPE,
            wh.UPDATED_ON
        FROM {get_table_name("FDTN_WAREHOUSE_METADATA")} wh
        INNER JOIN {Tables.query_metadata()} qm
            ON qm.WAREHOUSE_ID = wh.ID
            AND qm.ACCOUNT_ID = wh.ACCOUNT_ID
            AND qm.DEPLOYMENT = wh.DEPLOYMENT
        WHERE qm.DDA_QUERY_UUID = %(query_uuid)s
          AND qm.DEPLOYMENT = %(dda_snwflk_deployment)s
          AND qm.ACCOUNT_ID = %(account_id)s
          AND wh.CREATED_ON <= qm.CLIENT_SEND_TIME
          AND (wh.DELETED_ON IS NULL OR wh.DELETED_ON > qm.CLIENT_SEND_TIME)
        ORDER BY wh.CREATED_ON DESC
        LIMIT 1
    """

    # Get start time for warehouse chart data availability
    get_warehouse_charts_start_time = f"""
        SELECT DISTINCT MIN(CUR_SEC_SLICE) as START_TIME
        FROM {get_table_name("DDA_REL_WH_LOAD_QUERY_SEC_SLICE")}
        WHERE deployment = %(dda_snwflk_deployment)s
          AND account_id = %(account_id)s
          AND warehouse_name = %(warehouse_name)s
          AND latest_cluster_number > -1
    """

    # Get end time for warehouse chart data availability
    get_warehouse_charts_end_time = f"""
        SELECT DISTINCT MAX(CUR_SEC_SLICE) as END_TIME
        FROM {get_table_name("DDA_REL_WH_LOAD_QUERY_SEC_SLICE")}
        WHERE deployment = %(dda_snwflk_deployment)s
          AND account_id = %(account_id)s
          AND warehouse_name = %(warehouse_name)s
          AND latest_cluster_number > -1
    """

    # Get warehouse change history (last 30 days)
    get_change_history_for_warehouse = f"""
        SELECT
            e.timestamp,
            m.size,
            m.max_cluster_count,
            m.min_cluster_count,
            m.autosuspend_setting,
            e.event_type_name,
            e.operation_reason,
            e.default_size,
            e.payload
        FROM {get_table_name("FDTN_WAREHOUSE_EVENTS_LAST_30")} e
            ASOF JOIN {get_table_name("FDTN_WAREHOUSE_METADATA")} m match_condition (e.timestamp >= m.updated_on)
            ON (m.deployment = e.deployment and m.account_id = e.account_id and m.warehouse_name = e.warehouse_name)
        WHERE
            e.account_id = %(account_id)s
            AND e.warehouse_name = %(warehouse_name)s
            AND e.deployment = %(dda_snwflk_deployment)s
        ORDER BY e.timestamp desc
    """

    # Get warehouse level event overlays for charts
    get_warehouse_level_overlays = f"""
        WITH params AS (
            SELECT
                %(dda_snwflk_deployment)s AS wh_deployment,
                %(account_id)s AS wh_account_id,
                %(warehouse_name)s AS wh_name,
                %(start_time)s::TIMESTAMP AS start_time,
                %(end_time)s::TIMESTAMP AS end_time
        ),
        range_calculations AS (
            SELECT
                TIMEDIFF(second, start_time, end_time) AS range_size,
                IFF(TIMEDIFF(second, start_time, end_time) < 200, TIMEDIFF(second, start_time, end_time), 200) AS min_slice_count,
                ROUND(TIMEDIFF(second, start_time, end_time) / IFF(TIMEDIFF(second, start_time, end_time) < 200, TIMEDIFF(second, start_time, end_time), 200), 0) AS slice_size
            FROM params
        )
        SELECT
            TIME_SLICE(TIMESTAMP, range_calculations.slice_size, 'second', 'start') AS time_block,
            event_type_name,
            COUNT(*) AS event_count,
            CASE
                WHEN event_type_name IN ('SPINDOWN_CLUSTER', 'SPINUP_CLUSTER', 'SUSPEND_CLUSTER', 'RESUME_CLUSTER', 'SUSPEND_WAREHOUSE', 'RESUME_WAREHOUSE', 'WAREHOUSE_CONSISTENT')
                    AND operation_reason IN ('WAREHOUSE_AUTOSUSPEND', 'WAREHOUSE_AUTORESUME', 'MULTICLUSTER_SPINDOWN', 'MULTICLUSTER_SPINUP', 'WAREHOUSE_DROP', 'WAREHOUSE_RESIZE', 'RESOURCE_MONITOR_SUSPEND', 'WAREHOUSE_SUSPEND', 'INVALID', 'WAREHOUSE_RESUME')
                    THEN 'Warehouse State Change'
                WHEN event_type_name IN ('CREATE_WAREHOUSE', 'ALTER_WAREHOUSE', 'DROP_WAREHOUSE', 'RESIZE_WAREHOUSE', 'SUSPEND_WAREHOUSE', 'RESUME_WAREHOUSE')
                    THEN 'Warehouse Modification'
                ELSE 'Other'
            END AS category,
            SUM(COUNT(*)) OVER (PARTITION BY time_block, category) AS category_count
        FROM {get_table_name("FDTN_WAREHOUSE_EVENTS_LAST_30")}
        CROSS JOIN params
        JOIN range_calculations ON 1=1
        WHERE account_id = params.wh_account_id
            AND warehouse_name = params.wh_name
            AND deployment = params.wh_deployment
            AND event_state_name = 'COMPLETED'
            AND event_type_name IS NOT NULL
            AND TIMESTAMP BETWEEN params.start_time AND params.end_time
        GROUP BY time_block, event_type_name, category
        ORDER BY time_block ASC
    """

    # Stored procedure calls for warehouse-level charts
    @staticmethod
    def get_warehouse_chart_sp_call(chart_type: str) -> str:
        """
        Get the stored procedure call for warehouse-level charts.

        Args:
            chart_type: Type of chart (EXECUTED_JOBS, ACTIVE_CLUSTERS, XP_RETRY_JOBS, SUCCESS_FAILURE_RATIO)

        Returns:
            SQL CALL statement for the stored procedure
        """
        sp_mapping = {
            "EXECUTED_JOBS": "CALL GET_TOTAL_EXECUTED_JOBS_FOR_CLUSTER_IN_WH_SP(%(deployment)s, %(account_id)s, %(warehouse_name)s, %(start_time)s, %(end_time)s)",
            "ACTIVE_CLUSTERS": "CALL GET_TOTAL_EXECUTED_JOBS_FOR_CLUSTER_IN_WH_SP(%(deployment)s, %(account_id)s, %(warehouse_name)s, %(start_time)s, %(end_time)s)",
            "XP_RETRY_JOBS": "CALL GET_JOB_RETRIES_COUNT_FOR_CLUSTERS_IN_WH_SP(%(deployment)s, %(account_id)s, %(warehouse_name)s, %(start_time)s, %(end_time)s)",
            "SUCCESS_FAILURE_RATIO": "CALL GET_JOB_SUCCESS_FAILURE_RATIO_FOR_CLUSTER_IN_WH_SP(%(deployment)s, %(account_id)s, %(warehouse_name)s, %(start_time)s, %(end_time)s)",
        }

        if chart_type not in sp_mapping:
            raise ValueError(f"Unknown warehouse chart type: {chart_type}")

        return sp_mapping[chart_type]

    # Stored procedure calls for cluster-level charts
    @staticmethod
    def get_cluster_chart_sp_call(chart_type: str) -> str:
        """
        Get the stored procedure call for cluster-level charts.

        Args:
            chart_type: Type of chart (JOB_QUEUE_TRANSITION, JOB_BLOCKED_TRANSITION, QUEUE_TOTAL_TIME, BLOCKED_TOTAL_TIME)

        Returns:
            SQL CALL statement for the stored procedure
        """
        sp_mapping = {
            "JOB_QUEUE_TRANSITION": "CALL GET_QUEUE_JOBS_FOR_CLUSTER_IN_WH_SP(%(deployment)s, %(account_id)s, %(warehouse_name)s, %(cluster_num)s, %(start_time)s, %(end_time)s)",
            "JOB_BLOCKED_TRANSITION": "CALL GET_TOTAL_JOBS_FOR_CLUSTER_IN_WH_SP(%(deployment)s, %(account_id)s, %(warehouse_name)s, %(cluster_num)s, %(start_time)s, %(end_time)s)",
            "QUEUE_TOTAL_TIME": "CALL GET_TOTAL_QUEUE_TIME_FOR_CLUSTER_IN_WH_SP(%(deployment)s, %(account_id)s, %(warehouse_name)s, %(cluster_num)s, %(start_time)s, %(end_time)s)",
            "BLOCKED_TOTAL_TIME": "CALL GET_LOCKED_TIME_FOR_A_CLUSTER_IN_WH_SP(%(deployment)s, %(account_id)s, %(warehouse_name)s, %(cluster_num)s, %(start_time)s, %(end_time)s)",
        }

        if chart_type not in sp_mapping:
            raise ValueError(f"Unknown cluster chart type: {chart_type}")

        return sp_mapping[chart_type]
