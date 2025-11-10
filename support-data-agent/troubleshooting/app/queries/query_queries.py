"""
Query SQL definitions for all query-related operations.
Migrated from Views/QueryView/QueryQueries.py
"""

import math

# Constants
CRASH_MANAGER_INCIDENTS_URL = "https://crashmanager.ordevmisc1.us-west-2.aws-dev.app.snowflake.com/v2/incident_status"
RELATED_QUERIES_LIMIT = 1000
MB = math.pow(1024, 2)


class QueryViewQueries:
    # USED FOR THE HISTORICAL RUNS GRAPH
    def __init__(self, log_limit=1000):
        get_historical_runs_stats_base_query = f"""
            select
                other_queryid as query_id,
                error_message,
                job_created_on,
                duration_sec,
                version,
                sql_plan_hash,
                (
                    zeroifnull(dur_compiling) +
                    zeroifnull(dur_worker_group_wait) +
                    zeroifnull(dur_receive_query) +
                    zeroifnull(dur_wait_compilation_gateway) +
                    zeroifnull(dur_wait_show_command_gateway) +
                    zeroifnull(dur_scheduling) +
                    zeroifnull(dur_file_set_initialization)
                ) as compilation_ms,
                dur_queued_load as queued_overload_ms,
                dur_queued_resuming as queued_provisioning_ms,
                (
                    zeroifnull(dur_queued_repair) + 
                    zeroifnull(dur_queued_download_binary)
                ) as queued_repair_ms,
                (
                    dur_gs_executing +
                    dur_xp_executing +
                    zeroifnull(dur_aborting) +
                    zeroifnull(dur_failed_execution) +
                    zeroifnull(dur_wait_file_deletion_gateway) + 
                    zeroifnull(dur_wait_dposcan_gateway) +
                    zeroifnull(dur_gs_postexecuting) +
                    zeroifnull(dur_job_retry_handling)
                ) as execution_ms,
                (
                    zeroifnull(dur_list_external_files) + zeroifnull(dur_wait_file_listing_gateway)
                ) as listing_ms,
                zeroifnull(dur_txn_lock) as txn_lock_ms,
                (
                    compilation_ms + queued_overload_ms + queued_provisioning_ms + queued_repair_ms + execution_ms + listing_ms + txn_lock_ms
                ) as total_stages_duration_ms,
                zeroifnull(duration_sec) * 1000 as total_duration_ms,
                total_duration_ms - total_stages_duration_ms as miscellaneous_ms,
                zeroifnull(local_read_mb) * {MB} AS local_read_bytes,
                zeroifnull(local_write_mb) * {MB} AS local_write_bytes,
                oomkillcount as oom_kill_count,
                zeroifnull(remote_read_mb) * {MB} AS remote_read_bytes,
                zeroifnull(remote_write_mb) * {MB} AS remote_write_bytes,
                retrycount as retry_count,
                zeroifnull(scanned_mb) * {MB} AS scanned_bytes,
                zeroifnull(source_rows) as source_rows
            from table(%(historical_run_view_or_table)s)
        """
        self.log_limit = log_limit

        self.get_query_process_status = """
            select queryid_source as source,
                pipeline_runner,
                error_msg,
                state,
                _ingestion_timestamp
            from DDA_QUERY_PROCESSING_STATUS
            where query_id = %(query_id)s
                --  filter out certain pipeline runners since we don't show them in the ui
                and pipeline_runner not in
                    (
                        'QueryFilterTablePipelineRunner',
                        'DdaNewQuerySetTablePipelineRunner',
                        'DdaIncidentsTablePipelineRunner' -- todo(bhay): remove this after we fix the incidents pipeline tracking logic
                    )
            -- need to qualify here because we have many duplicates
            qualify row_number() over (
                partition by pipeline_runner, state, error_msg
                order by _ingestion_timestamp
            ) = 1
            order by _ingestion_timestamp
        """

        self.get_last_successful_query_id = """
            -- queryid of the most recent successful run
            SELECT TOP 1 MD.QUERYID AS "COMPARE_QUERY_ID"
            FROM table(%(query_metadata_view_or_table)s) MD
            WHERE MD.SQL_TEXT_HASH = %(sql_text_hash)s
                AND MD.ERROR_MESSAGE IS NULL
                AND MD.CLIENT_SEND_TIME < %(query_send_time)s
            ORDER BY MD.CLIENT_SEND_TIME DESC
        """

        self.historical_runs_query_count = """
            SELECT COUNT 
            FROM DDA_REL_QUERY_ID_STATS 
            WHERE QUERY_ID = %(query_id)s 
            AND TABLE_NAME = 'DDA_QUERY_HISTORICAL_RUN_STATS' 
            ORDER BY _INGESTION_TIMESTAMP DESC 
            LIMIT 1;
        """

        self.query_tables = """
            -- try to extract and parse the nested json in the gs logs message. if it's malformed then this will return 0 rows.
            with parsed_json as (
                SELECT distinct md.queryid as query_id,
                    t.value : name::varchar as name
                    , t.value : id as id
                    , t.value : version as version
                    , t.value : files::int as partitions
                    , t.value : rows::int as total_rows
                    , t.value : isDmlTarget::boolean as is_dml_target
                    , t.value : isExternal::boolean as is_external
                    , t.value : isHybrid::boolean as is_hybrid
                    , t.value : isMV::boolean as is_materialized_view
                    , t.value : isTemp::boolean as is_temporary,
                FROM table(%(query_metadata_view_or_table)s) md
                LEFT JOIN table(%(rel_query_id_gs_logs_view_or_table)s) gl ON (
                            md.queryid = gl.job_uuid
                        AND md.account_id = gl.account_id
                        AND md.deployment = gl.deployment
                        AND md.gs_cluster_name = gl.gs_cluster
                        AND md.gs_inst_id = gl.gs_id
                ),
                LATERAL flatten (
                    try_parse_json(
                        replace(
                            MESSAGE, 'Table and column accesses: '
                        )
                    ): tables
                ) t
                WHERE md.QUERYID in (%(query_ids)s)
                    AND gl.CLASS = 'com.snowflake.services.usagetracking.TableColumnInfoTracker'
            )
            -- select all the parsed json and include a boolean to indicate if the json is valid
            select pj.*, CHECK_JSON(
                replace(gl.message, 'Table and column accesses: ')
            ) as check_json_error_message
            FROM table(%(query_metadata_view_or_table)s) md
            LEFT JOIN table(%(rel_query_id_gs_logs_view_or_table)s) gl ON (
                    md.queryid = gl.job_uuid
                AND md.account_id = gl.account_id
                AND md.deployment = gl.deployment
                AND md.gs_cluster_name = gl.gs_cluster
                AND md.gs_inst_id = gl.gs_id
            )
            LEFT JOIN parsed_json pj on pj.query_id = md.queryid
            WHERE md.QUERYID in (%(query_ids)s)
                AND gl.CLASS = 'com.snowflake.services.usagetracking.TableColumnInfoTracker';
        """

        self.historical_runs_query_count_fallback = f"""
           -- Streamlit_historical_runs_query_count_queryview
            SELECT COUNT(1) AS "COUNT"
            FROM (
                (
                    SELECT OTHER_QUERYID
                    from table(%(historical_run_view_or_table)s)
                    WHERE CURRENT_QUERYID = %(query_id)s
                    LIMIT {RELATED_QUERIES_LIMIT}
                )
                UNION
                (   -- gets the target query in case it was run greater than 30 days ago or
                    -- it was otherwise not in the 1,000 rows from the first subquery
                    SELECT OTHER_QUERYID
                    from table(%(historical_run_view_or_table)s)
                    WHERE CURRENT_QUERYID = %(query_id)s
                        AND OTHER_QUERYID = %(query_id)s
                )
            );
        """
        # USED FOR THE HISTORICAL RUNS GRAPH
        self.get_historical_runs_stats = f"""
        {get_historical_runs_stats_base_query}
        where current_queryid = %(query_id)s
        and sqltext_hash <> 0
        order by job_created_on desc
        limit {RELATED_QUERIES_LIMIT}
        """  # Latest 750 attempts of the target query within last 30 days

        # we issue this query in combination with get_historical_runs_stats in case the target query isn't included in that query
        self.get_historical_run_stats_for_query = f"""
            {get_historical_runs_stats_base_query}
            where other_queryid = %(query_id)s
            order by job_created_on
            limit 1;
            """
        # adding limit 1 because this query may have been a historical run for another query, meaning we would get duplicate rows, but the data would be the same for every row
        # USED FOR THE HISTORICAL RUNS TABLE
        self.get_historical_runs = f"""
            select
                other_queryid as query_id,
                version as release_version,
                error_message,
                job_created_on,
                zeroifnull(dur_compiling) as dur_compiling,
                zeroifnull(dur_worker_group_wait) as dur_worker_group_wait,
                zeroifnull(dur_receive_query) as dur_receive_query,
                zeroifnull(dur_wait_compilation_gateway) as dur_wait_compilation_gateway,
                zeroifnull(dur_wait_show_command_gateway) as dur_wait_show_command_gateway,
                zeroifnull(dur_scheduling) as dur_scheduling,
                zeroifnull(dur_file_set_initialization) as dur_file_set_initialization,
                zeroifnull(dur_queued_load) as dur_queued_load,
                zeroifnull(dur_queued_resuming) as dur_queued_resuming,
                zeroifnull(dur_queued_repair) as dur_queued_repair,
                zeroifnull(dur_queued_download_binary) as dur_queued_download_binary,
                zeroifnull(dur_gs_executing) as dur_gs_executing,
                zeroifnull(dur_xp_executing) as dur_xp_executing,
                zeroifnull(dur_aborting) as dur_aborting,
                zeroifnull(dur_failed_execution) as dur_failed_execution,
                zeroifnull(dur_wait_file_deletion_gateway) as dur_wait_file_deletion_gateway,
                zeroifnull(dur_wait_dposcan_gateway) as dur_wait_dposcan_gateway,
                zeroifnull(dur_gs_postexecuting) as dur_gs_postexecuting,
                zeroifnull(dur_job_retry_handling) as dur_job_retry_handling,
                zeroifnull(dur_list_external_files) as dur_list_external_files,
                zeroifnull(dur_wait_file_listing_gateway) as dur_wait_file_listing_gateway,
                zeroifnull(dur_txn_lock) as dur_txn_lock,
                zeroifnull(duration_sec) * 1000 as total_duration,
                zeroifnull(local_read_mb) * {MB} AS local_read_bytes,
                zeroifnull(local_write_mb) * {MB} AS local_write_bytes,
                oomkillcount as oom_kill_count,
                zeroifnull(remote_read_mb) * {MB} AS remote_read_bytes,
                zeroifnull(remote_write_mb) * {MB} AS remote_write_bytes,
                retrycount as retry_count,
                zeroifnull(scanned_mb) * {MB} AS scanned_bytes,
                -- missing server_memory_used,
                zeroifnull(source_rows) as source_rows,
                -- missing total_memory
                (f.queryuuid is not null) as is_fully_processed
            from table(%(historical_run_view_or_table)s) h
            left join dda_query_filter f on f.queryuuid = h.other_queryid
            where current_queryid = %(query_id)s
            order by job_created_on desc
            limit {RELATED_QUERIES_LIMIT}
        """

        self.query_prior_runs_average = f"""
            select avg(zeroifnull(local_read_mb)) * {MB} AS local_read_bytes,
                avg(zeroifnull(local_write_mb)) * {MB} AS local_write_bytes,
                avg(zeroifnull(remote_read_mb)) * {MB} as remote_read_bytes,
                avg(zeroifnull(remote_write_mb)) * {MB} as remote_write_bytes,
                avg(zeroifnull(scanned_mb)) * {MB} as scanned_bytes,
                avg(zeroifnull(scanned_partitions)) as scanned_partitions,
                avg(zeroifnull(source_rows)) as source_rows,
                avg(zeroifnull(total_memory)) as total_memory,
                avg(zeroifnull(max_memory)) as max_memory,
                avg(zeroifnull(server_memory_used)) as server_memory_used
            from table(%(historical_run_view_or_table)s)
            where current_queryid = %(query_id)s
            limit {RELATED_QUERIES_LIMIT};
        """

        self.get_parent_child_tree = """
            -- there are many duplicate rows and we only care about the latest one
            with LATEST_QUERY_GRAPH as (
                select query_id,
                    max(_ingestion_timestamp) as _ingestion_timestamp
                from DDA_REL_QUERY_ID_GRAPH_JSON
                -- get the current query's subtree and all of it's parents
                where query_id = %(query_id)s or root_sub_tree like %(query_id_with_wildcard)s
                group by query_id
            )
            select lg.query_id,
                json.root_sub_tree,
                lg._ingestion_timestamp,
                mdt.sql_text,
                mdt.error_code,
                mdt.error_message,
                mdt.client_send_time,
                mdt.parent_job_id,
                mdt.end_time
            from LATEST_QUERY_GRAPH lg
            join DDA_REL_QUERY_ID_GRAPH_JSON json on json.query_id = lg.query_id
                and json._ingestion_timestamp = lg._ingestion_timestamp
            join table(%(query_metadata_view_or_table)s) mdt on mdt.queryid = json.query_id
        """

        self.query_metadata = f"""
            -- get incident data to show on query metadata page
            WITH INCIDENT_DATA AS (
                SELECT QUERYID,
                    ANY_VALUE(INTERNAL_MESSAGE) AS INTERNAL_MESSAGE
                FROM DDA_QUERY_INCIDENT_MAPPING
                WHERE QUERYID = %(query_id)s
                GROUP BY QUERYID
            )
            SELECT distinct md.QUERYID as QUERY_ID,
                md.ACCOUNT_NAME,
                md.WAREHOUSE_NAME,
                md.WAREHOUSE_SIZE,
                md.DEPLOYMENT,
                md.ACCOUNT_ID,
                md.CLIENT_ENVIRONMENT,
                md.QUERY_DIRECT_URL,
                md.SQL_TEXT,
                md.SQL_TEXT_HASH::varchar AS SQL_TEXT_HASH,
                md.CLIENT_SEND_TIME,
                md.END_TIME,
                md.SESSION_ID::varchar AS SESSION_ID,
                md.USER_NAME,
                md.CLIENT_APP_ID,
                md.AUTHN_METHOD AS AUTHENTICATION_METHOD,
                md.ERROR_MESSAGE,
                md.ERROR_CODE,
                id.INTERNAL_MESSAGE,
                md.GS_CLUSTER_NAME,
                md.GS_INST_ID,
                md.LATEST_CLUSTER_NUMBER,-- (Do not add + 1 here to derive the PROD cluster number , as the downstream logic is already performing that operation). 
                md.CASENUMBER,
                md.BINDINGS,
                md.QUERY_TAG,
                md.ROLE_NAME,
                hr.VERSION,
                md._INGESTION_TIMESTAMP,
                w.OOMKILLCOUNT as OOM_KILL_COUNT,
                w.RETRYCOUNT as RETRY_COUNT,
                zeroifnull(w.RUN_TIME) as TOTAL_DURATION,
                zeroifnull(hr.DUR_COMPILING) as DUR_COMPILING,
                zeroifnull(hr.DUR_TXN_LOCK) as DUR_TXN_LOCK,
                zeroifnull(hr.DUR_GS_EXECUTING) as DUR_GS_EXECUTING,
                zeroifnull(hr.DUR_QUEUED_LOAD) as DUR_QUEUED_LOAD,
                zeroifnull(hr.DUR_QUEUED_RESUMING) as DUR_QUEUED_RESUMING,
                zeroifnull(hr.DUR_QUEUED_REPAIR) as DUR_QUEUED_REPAIR,
                zeroifnull(hr.DUR_WORKER_GROUP_WAIT) as DUR_WORKER_GROUP_WAIT,
                zeroifnull(hr.DUR_XP_EXECUTING) as DUR_XP_EXECUTING,
                zeroifnull(hr.DUR_ABORTING) as DUR_ABORTING,
                zeroifnull(w.DUR_QUEUED_DOWNLOAD_BINARY) as DUR_QUEUED_DOWNLOAD_BINARY,
                zeroifnull(hr.DUR_LIST_EXTERNAL_FILES) as DUR_LIST_EXTERNAL_FILES,
                zeroifnull(hr.DUR_FAILED_EXECUTION) as DUR_FAILED_EXECUTION,
                zeroifnull(hr.DUR_RECEIVE_QUERY) as DUR_RECEIVE_QUERY,
                zeroifnull(hr.DUR_WAIT_COMPILATION_GATEWAY) as DUR_WAIT_COMPILATION_GATEWAY,
                zeroifnull(hr.DUR_WAIT_FILE_LISTING_GATEWAY) as DUR_WAIT_FILE_LISTING_GATEWAY,
                zeroifnull(hr.DUR_WAIT_FILE_DELETION_GATEWAY) as DUR_WAIT_FILE_DELETION_GATEWAY,
                zeroifnull(hr.DUR_WAIT_SHOW_COMMAND_GATEWAY) as DUR_WAIT_SHOW_COMMAND_GATEWAY,
                zeroifnull(hr.DUR_WAIT_DPOSCAN_GATEWAY) as DUR_WAIT_DPOSCAN_GATEWAY,
                zeroifnull(hr.DUR_GS_POSTEXECUTING) as DUR_GS_POSTEXECUTING,
                zeroifnull(hr.DUR_SCHEDULING) as DUR_SCHEDULING,
                zeroifnull(hr.DUR_JOB_RETRY_HANDLING) as DUR_JOB_RETRY_HANDLING,
                zeroifnull(hr.DUR_FILE_SET_INITIALIZATION) as DUR_FILE_SET_INITIALIZATION,
                zeroifnull(hr.source_rows) as source_rows,
                zeroifnull(hr.scanned_partitions) as scanned_partitions,
                zeroifnull(w.total_memory) as total_memory,
                zeroifnull(w.max_memory) as max_memory,
                zeroifnull(w.server_memory_used) as server_memory_used,
                zeroifnull(w.local_read_mb) * {MB} AS local_read_bytes,
                zeroifnull(w.local_write_mb) * {MB} AS local_write_bytes,
                zeroifnull(w.remote_read_mb) * {MB} AS remote_read_bytes,
                zeroifnull(w.remote_write_mb) * {MB} AS remote_write_bytes,
                zeroifnull(w.scanned_mb) * {MB} AS scanned_bytes,
                zeroifnull(hr.duration_sec) * 1000 as historical_run_total_duration_ms
            from table(%(query_metadata_view_or_table)s) md
            left join INCIDENT_DATA id on id.QUERYID = md.QUERYID
            left join table(%(dda_historical_run_stats)s) hr on hr.OTHER_QUERYID = md.QUERYID
            left join table(%(dda_query_warehouse_stats)s) w on w.CONCURRENT_QUERYID = md.QUERYID
            where md.QUERYID = %(query_id)s
        """

        self.get_incidents = f"""
            -- Streamlit_incidentdata_queryview
            SELECT
            A.QUERYID,
            A.EXPORT_TIME,
            A.INCIDENT_ID,
            A.INTERNAL_MESSAGE,
            A.JIRA_AREA_NAME,
            A.JIRA_COMPONENT_NAME,
            A.XP_STACK_TRACE,
            A._INGESTION_TIMESTAMP,
            '{CRASH_MANAGER_INCIDENTS_URL}' || A.INCIDENT_ID || '&deployment=' || B.DEPLOYMENT || '&submit=Search' AS CRASH_MANAGER_LINK
            FROM DDA_QUERY_INCIDENT_MAPPING A 
            join table(%(query_metadata_view_or_table)s) B 
            ON A.QUERYID = B.QUERYID
            WHERE A.QUERYID = %(query_id)s
            ORDER BY A._INGESTION_TIMESTAMP DESC
            LIMIT 5;
        """

        self.get_case_numbers_for_query = """
            select distinct (case_number)
            from (
                select md.casenumber as case_number
                from table(%(query_metadata_view_or_table)s) md
                where md.queryid = %(query_id)s
                union
                select ce.case_number
                from FDTN_REL_CASE_QUERY_ID_V ce
                where ce.query_id = %(query_id)s
            );
        """

        self.get_queries_in_case = """
            select md.queryid as query_id,
                md.client_send_time,
                md.error_message,
                md.error_code,
                md.sql_text_hash::varchar as sql_text_hash,
                md.casenumber as case_number,
                md.deployment,
                a.replication_group,
                a.name as account_name
            from table(%(query_metadata_view_or_table)s) md
            join table(%(fdtn_snwflk_account)s) a on a.snowflake_account_id = md.account_id
                and a.snowflake_deployment = md.deployment
            where md.casenumber in (%(case_numbers)s)
        """

        self.concurrent_queries_in_cluster_count = """
            -- Streamlit_concurrent_queries_in_warehouse_count_queryview
            SELECT COUNT 
            FROM DDA_REL_QUERY_ID_STATS 
            WHERE QUERY_ID = %(query_id)s 
            AND TABLE_NAME = 'DDA_QUERY_WAREHOUSE_STATS' 
            ORDER BY _INGESTION_TIMESTAMP DESC 
            LIMIT 1;
        """

        self.concurrent_queries_in_cluster_count_fallback = """
            -- Streamlit_concurrent_queries_in_warehouse_count_queryview
            SELECT COUNT(*) AS "COUNT"
            from table(%(warehouse_stats_view_or_table)s)
            WHERE CURRENT_QUERYID = %(query_id)s AND LATEST_CLUSTER_NUMBER = %(latest_cluster_number)s;
        """

        self.get_concurrent_queries = f"""
            select
                distinct
                concurrent_queryid as query_id,
                version as release_version,
                error_message,
                job_created_on,
                zeroifnull(dur_compiling) as dur_compiling,
                zeroifnull(dur_worker_group_wait) as dur_worker_group_wait,
                zeroifnull(dur_receive_query) as dur_receive_query,
                zeroifnull(dur_wait_compilation_gateway) as dur_wait_compilation_gateway,
                zeroifnull(dur_wait_show_command_gateway) as dur_wait_show_command_gateway,
                zeroifnull(dur_scheduling) as dur_scheduling,
                zeroifnull(dur_file_set_initialization) as dur_file_set_initialization,
                zeroifnull(dur_queued_load) as dur_queued_load,
                zeroifnull(dur_queued_resuming) as dur_queued_resuming,
                zeroifnull(dur_queued_repair) as dur_queued_repair,
                zeroifnull(dur_queued_download_binary) as dur_queued_download_binary,
                zeroifnull(dur_gs_executing) as dur_gs_executing,
                zeroifnull(dur_xp_executing) as dur_xp_executing,
                zeroifnull(dur_aborting) as dur_aborting,
                zeroifnull(dur_failed_execution) as dur_failed_execution,
                zeroifnull(dur_wait_file_deletion_gateway) as dur_wait_file_deletion_gateway, 
                zeroifnull(dur_wait_dposcan_gateway) as dur_wait_dposcan_gateway,
                zeroifnull(dur_gs_postexecuting) as dur_gs_postexecuting,
                zeroifnull(dur_job_retry_handling) as dur_job_retry_handling,
                zeroifnull(dur_list_external_files) as dur_list_external_files,
                zeroifnull(dur_wait_file_listing_gateway) as dur_wait_file_listing_gateway,
                zeroifnull(dur_lock) as dur_txn_lock,
                zeroifnull(run_time) as total_duration,
                zeroifnull(local_read_mb) * {MB} AS local_read_bytes,
                zeroifnull(local_write_mb) * {MB} AS local_write_bytes,
                zeroifnull(number_of_files_scanned) as number_of_files_scanned,
                zeroifnull(remote_read_mb) * {MB} AS remote_read_bytes,
                zeroifnull(remote_write_mb) * {MB} AS remote_write_bytes,
                oomkillcount as oom_kill_count,
                retrycount as retry_count,
                zeroifnull(scanned_mb) * {MB} AS scanned_bytes,
                server_memory_used,
                zeroifnull(source_rows) as source_rows,
                total_memory,
                (f.queryuuid is not null) as is_fully_processed
            from table(%(warehouse_stats_view_or_table)s) ws
            left join dda_query_filter f on f.queryuuid = ws.concurrent_queryid
            where current_queryid = %(query_id)s
                and latest_cluster_number = %(latest_cluster_number)s
            order by job_created_on
            limit {RELATED_QUERIES_LIMIT}
        """

        self.cluster_number_of_concurrent_query = """
            -- Zooming into the exact cluster  on which the query ran, this will be used later in the visualisations
            SELECT (LATEST_CLUSTER_NUMBER+1) AS CLUSTER_NUMBER
            from table(%(warehouse_stats_view_or_table)s)
            WHERE CURRENT_QUERYID = %(query_id)s AND
            CONCURRENT_QUERYID = %(query_id)s
            ;
        """

        self.concurrent_queries_stats = f"""
            select
                ws.concurrent_queryid as query_id,
                ws.job_created_on,
                ws.end_time,
                (
                    zeroifnull(ws.dur_compiling) +
                    zeroifnull(ws.dur_worker_group_wait) +
                    zeroifnull(ws.dur_receive_query) +
                    zeroifnull(ws.dur_wait_compilation_gateway) +
                    zeroifnull(ws.dur_wait_show_command_gateway) +
                    zeroifnull(ws.dur_scheduling) +
                    zeroifnull(ws.dur_file_set_initialization)
                ) as compilation_ms,
                ws.dur_queued_load as queued_overload_ms,
                ws.dur_queued_resuming as queued_provisioning_ms,
                (
                    ws.dur_queued_repair + ws.dur_queued_download_binary
                ) as queued_repair_ms,
                zeroifnull(ws.dur_lock) as txn_lock_ms,
                (
                    zeroifnull(ws.dur_list_external_files) + zeroifnull(ws.dur_wait_file_listing_gateway)
                ) as listing_ms,
                (
                    ws.dur_gs_executing +
                    ws.dur_xp_executing +
                    zeroifnull(ws.dur_aborting) +
                    zeroifnull(ws.dur_failed_execution) +
                    zeroifnull(ws.dur_wait_file_deletion_gateway) + 
                    zeroifnull(ws.dur_wait_dposcan_gateway) +
                    zeroifnull(ws.dur_gs_postexecuting) +
                    zeroifnull(ws.dur_job_retry_handling)
                ) as execution_ms,
                (
                    compilation_ms + queued_overload_ms + queued_provisioning_ms + queued_repair_ms + execution_ms + listing_ms + txn_lock_ms
                ) as total_stages_duration_ms,
                zeroifnull(run_time) as total_duration_ms,
                total_duration_ms - total_stages_duration_ms as miscellaneous_ms,
                dateadd('milliseconds', compilation_ms, ws.job_created_on) as compilation_end_time,
                dateadd('milliseconds', miscellaneous_ms, compilation_end_time) as miscellaneous_end_time,
                dateadd('milliseconds', queued_overload_ms, miscellaneous_end_time) as queued_overload_end_time,
                dateadd('milliseconds', queued_provisioning_ms, queued_overload_end_time) as queued_provisioning_end_time,
                dateadd('milliseconds', queued_repair_ms, queued_provisioning_end_time) as queued_repair_end_time,
                dateadd('milliseconds', txn_lock_ms, queued_repair_end_time) as txn_lock_end_time,
                dateadd('milliseconds', listing_ms, txn_lock_end_time) as listing_end_time,
                dateadd('milliseconds', execution_ms, listing_end_time) as execution_end_time,
                zeroifnull(ws.local_read_mb) * {MB} AS local_read_bytes,
                zeroifnull(ws.local_write_mb) * {MB} AS local_write_bytes,
                zeroifnull(ws.max_memory) as max_memory,
                zeroifnull(ws.number_of_files_scanned) as number_of_files_scanned,
                zeroifnull(ws.oomkillcount) as oom_kill_count,
                zeroifnull(ws.remote_read_mb) * {MB} AS remote_read_bytes,
                zeroifnull(ws.remote_write_mb) * {MB} AS remote_write_bytes,
                zeroifnull(ws.retrycount) as retry_count,
                zeroifnull(ws.scanned_mb) * {MB} AS scanned_bytes,
                zeroifnull(ws.server_memory_used) as server_memory_used,
                zeroifnull(ws.source_rows) as source_rows,
                zeroifnull(ws.total_memory) as total_memory,
                ws.error_message,
                ws.version
            from table(%(warehouse_stats_view_or_table)s) ws
            where ws.current_queryid = %(query_id)s
                and ws.latest_cluster_number = %(latest_cluster_number)s
            order by job_created_on
            limit {RELATED_QUERIES_LIMIT}
        """

        self.max_run_time = """
            -- Streamlit_type_and_count_queryview
            SELECT
                UPPER(
                    REGEXP_REPLACE(
                        REGEXP_SUBSTR(
                            TRIM(SQL_TEXT, ' \r\n\t'),
                            '^[\\\w\\\(]+', 1, 1, 'mc'
                        ),
                        '\\\W+',''
                    )
                ) AS QUERY_TYPE,
                MAX(RUN_TIME / 1000) AS RUN_TIME_S,
                MAX(DUR_GS_EXECUTING / 1000) AS DUR_GS_EXECUTING_S,
                MAX(DUR_XP_EXECUTING / 1000) AS DUR_XP_EXECUTING_S,
                COUNT(QUERY_TYPE) AS COUNT_OF_QUERY_TYPE
            from table(%(warehouse_stats_view_or_table)s)
            WHERE CURRENT_QUERYID = %(query_id)s
                AND LATEST_CLUSTER_NUMBER IN (
                    SELECT LATEST_CLUSTER_NUMBER
                    from table(%(warehouse_stats_view_or_table)s)
                    WHERE CURRENT_QUERYID = %(query_id)s
                        AND CONCURRENT_QUERYID = %(query_id)s
                )
                AND LATEST_CLUSTER_NUMBER IS NOT NULL
                AND QUERY_TYPE != ''
            GROUP BY QUERY_TYPE
            ORDER BY COUNT_OF_QUERY_TYPE DESC;
        """

        self.gs_log_sharable_view_name = """
            -- Streamlit_gs_log_sharable_view_name_queryview
            SELECT REPLACE(CONCAT_WS('', 'TEMP.TRIAGE_SQL.GS_LOGS_V_', TO_VARCHAR(
                    SELECT CURRENT_QUERYID FROM TEMP.TRIAGE_SQL.DDA_GS_LOGS
                    WHERE CURRENT_QUERYID= %(query_id)s LIMIT 1
                )
            ),'-','_') AS VIEW_NAME;
        """

        self.xp_sharable_view = """
            -- Streamlit_xp_sharable_view_queryview
            SELECT REPLACE(CONCAT_WS('', 'TEMP.TRIAGE_SQL.XP_LOGS_V_', TO_VARCHAR(
                    SELECT CURRENT_QUERYID FROM TEMP.TRIAGE_SQL.DDA_XP_LOGS
                    WHERE CURRENT_QUERYID= %(query_id)s LIMIT 1
                )
            ),'-','_') AS VIEW_NAME;
        """

        self.get_parameters = """
            SELECT DISTINCT PARAMETER_ID AS ID,
                QUERY_PARAMETER_NAME AS NAME,
                QUERY_PARAMETER_VALUE AS VALUE,
                QUERY_PARAMETER_DOMAIN AS LEVEL,
                DESCRIPTION,
                COMPONENT,
                PUBLIC_LEVELS
            from table(%(rel_non_default_parameter_query_id_view_or_table)s)
            WHERE QUERY_ID = %(query_id)s;
        """

        self.gs_logs_count = """
            -- Streamlit_gs_logs_count_queryview
            SELECT COUNT 
            FROM DDA_REL_QUERY_ID_STATS 
            WHERE QUERY_ID = %(query_id)s 
            AND TABLE_NAME = 'DDA_REL_QUERY_ID_GS_LOGS' 
            ORDER BY _INGESTION_TIMESTAMP DESC
            LIMIT 1;
        """

        self.xp_logs_count = """
            -- Streamlit_xp_logs_queryview
            SELECT COUNT 
            FROM DDA_REL_QUERY_ID_STATS 
            WHERE QUERY_ID = %(query_id)s
            AND TABLE_NAME = 'DDA_REL_QUERY_ID_XP_LOGS' 
            ORDER BY _INGESTION_TIMESTAMP DESC 
            LIMIT 1; 
        """

        self.gs_logs_count_fallback = """
            -- Streamlit_gs_logs_count_queryview
            SELECT COUNT(*) AS "COUNT"
            from table(%(rel_query_id_gs_logs_view_or_table)s)
            WHERE JOB_UUID = %(query_id)s
                AND DEPLOYMENT = CAST(%(deployment)s AS VARCHAR(16777216))
                AND GS_CLUSTER = CAST(%(gs_cluster_name)s AS VARCHAR(16777216))
                AND GS_ID = %(gs_inst_id)s
                AND CLASS IS NOT NULL
            ORDER BY TIMESTAMP DESC;
        """

        self.xp_logs_count_fallback = """
            -- Streamlit_xp_logs_queryview
            SELECT COUNT(*) AS "COUNT"
            from table(%(rel_query_id_xp_logs_view_or_table)s)
            WHERE QUERY_ID = %(query_id)s
                AND DEPLOYMENT_NAME = %(deployment)s
                AND ACCOUNT_NAME = %(account_name)s
                AND JOB_ID IS NOT NULL;
        """

        self.get_deployment_cloud_provider = """
            select dm.cloud
            from CXE_DEPLOYMENT_MAPPING_V dm
            where dm.deployment = %(deployment)s
        """

        self.get_query_sessions_data = """
            -- Show session details in timestamp order
            select distinct
                query_id,
                job_created_on,
                end_time,
                zeroifnull(dur_compiling) as dur_compiling,
                zeroifnull(dur_worker_group_wait) as dur_worker_group_wait,
                zeroifnull(dur_receive_query) as dur_receive_query,
                zeroifnull(dur_wait_compilation_gateway) as dur_wait_compilation_gateway,
                zeroifnull(dur_wait_show_command_gateway) as dur_wait_show_command_gateway,
                zeroifnull(dur_scheduling) as dur_scheduling,
                zeroifnull(dur_file_set_initialization) as dur_file_set_initialization,
                zeroifnull(queued_overload_ms) as dur_queued_load,
                zeroifnull(queued_provisioning_ms) as dur_queued_resuming,
                zeroifnull(queued_repair_ms) as dur_queued_repair,
                zeroifnull(dur_queued_download_binary) as dur_queued_download_binary,
                zeroifnull(dur_gs_executing) as dur_gs_executing,
                zeroifnull(dur_xp_executing) as dur_xp_executing,
                zeroifnull(dur_aborting) as dur_aborting,
                zeroifnull(dur_failed_execution) as dur_failed_execution,
                zeroifnull(dur_wait_file_deletion_gateway) as dur_wait_file_deletion_gateway,
                zeroifnull(dur_wait_dposcan_gateway) as dur_wait_dposcan_gateway,
                zeroifnull(dur_gs_postexecuting) as dur_gs_postexecuting,
                zeroifnull(dur_job_retry_handling) as dur_job_retry_handling,
                zeroifnull(dur_list_external_files) as dur_list_external_files,
                zeroifnull(dur_wait_file_listing_gateway) as dur_wait_file_listing_gateway,
                zeroifnull(txn_lock_ms) as dur_txn_lock,
                zeroifnull(total_duration_ms) as total_duration,
                error_message,
                sql_text,
                warehouse_name,
                (latest_cluster_number + 1) as latest_cluster_number,
            from DDA_RELATED_QUERIES_V
            where session_id = %(session_id)s
            order by job_created_on, end_time;
        """

        self.get_account_details = """
            select snowflake_account_id
            from table(%(fdtn_snwflk_account)s)
            where name = %(account)s
                and snowflake_deployment = %(deployment)s 
                and deleted_on is NULL 
        """

        self.get_query_console_link = """
            SELECT DEPLOYMENT_URL || '/console#/monitoring/queries' AS "Query History"
            FROM CXE_DEPLOYMENT_MAPPING_V
            WHERE DEPLOYMENT = %(dda_snwflk_deployment)s;
        """

        self.get_major_incidents_historical_overlay = """
            select distinct
                JIRA_ISSUE_KEY,
                INCIDENT_NUMBER,
                INCIDENT_TYPE,
                INCIDENT_SUMMARY,
                CURRENT_STATUS,
                CUSTOMER_IMPACT,
                COMPONENTS_AFFECTED_ARRAY,
                IMPACT_START_AT,
                IMPACT_END_AT,
                SLACK_LINK,
                STATUS_PAGE_LINK,
                COLLAB_SME,
                d2.value::varchar as DEPLOYMENT
            from DDA_REL_MAJOR_INCIDENT_CASE_V,
            lateral flatten(input => service_region_deployment_construct) d1,
            lateral flatten(input => d1.value:deployment) d2
            where d2.value::varchar = %(dda_snwflk_deployment)s
            and IMPACT_START_AT <= %(query_end_time)s
            and (IMPACT_END_AT is null or IMPACT_END_AT >= %(query_start_time)s)
            and CLOSURE_TYPE not in ('closed_no_incident', 'canceled')
            order by IMPACT_START_AT desc;
        """

    def get_gs_logs(self):
        return f"""
        -- Streamlit_gs_logs_queryview
        SELECT TIMESTAMP, CLASS, THREAD, THREAD_CLASS, MESSAGE, EXCEPTION_STACK, EXCEPTION_MESSAGE, EXCEPTION_CLASS,
            GS_CLUSTER, GS_ID, HOST, DATABASE_ID, OBJECT_ID, LOG_PARAMS
        from table(%(rel_query_id_gs_logs_view_or_table)s)
        WHERE JOB_UUID = %(query_id)s
            AND DEPLOYMENT = CAST(%(deployment)s AS VARCHAR(16777216))
            AND CLASS IS NOT NULL
        ORDER BY TIMESTAMP DESC
        {f"LIMIT {self.log_limit}" if self.log_limit else ""};
    """

    def get_xp_logs(self):
        return f"""
        -- Streamlit_xp_logs_queryview
        SELECT TIMESTAMP, MESSAGE, COMP_NAME, FUNC_NAME, IP_ADDRESS, NAME, PID, SERVER_ID, LABEL,
        from table(%(rel_query_id_xp_logs_view_or_table)s)
        WHERE QUERY_ID = %(query_id)s
            AND JOB_ID IS NOT NULL
        ORDER BY TIMESTAMP DESC
        {f"LIMIT {self.log_limit}" if self.log_limit else ""};
        """


class FilterQueries:
    def __init__(self):
        base_query = """
            SELECT QUERYID,
                CASENUMBER,
                CLIENT_SEND_TIME,
                SQL_TEXT_HASH::varchar as SQL_TEXT_HASH
            from table(%(query_metadata_view_or_table)s)
        """
        self.queryid_filter = (
            base_query
            + """
            ORDER BY CLIENT_SEND_TIME DESC;
        """
        )

        self.query_id_account_filter = (
            base_query
            + """
            WHERE ACCOUNT_NAME = CAST(%(account)s AS VARCHAR(16777216))
            ORDER BY CLIENT_SEND_TIME DESC;
        """
        )
