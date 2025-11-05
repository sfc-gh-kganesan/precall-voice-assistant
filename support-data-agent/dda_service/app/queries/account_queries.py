"""
Account View SQL Queries

SQL queries for account-related operations including search, metadata retrieval,
warehouse listings, case associations, and more.

Ported from: Views/AccountView/AccountQueries.py
"""


class AccountViewQueries:
    """SQL queries for account view operations."""

    def __init__(self):
        # 1. ACCOUNT SEARCH - Find accounts by partial match on locator/alias/ID
        self.account_search_query = """
        -- Account search with ranking (exact match > partial match)
        SELECT DISTINCT
            a.snowflake_deployment as DEPLOYMENT,
            a.alias,
            a.name as LOCATOR,
            a.snowflake_account_id as ACCOUNT_ID,
            a.replication_group
        FROM table(%(fdtn_snwflk_account)s) a
        WHERE a.replication_group is not null
            AND (
                -- snowflake account partial match
                a.name ILIKE %(search_query_wildcard_pattern)s
                OR a.alias ILIKE %(search_query_wildcard_pattern)s
                OR a.snowflake_account_id LIKE %(search_query_wildcard_pattern)s
            )
            AND DELETED_ON is NULL
        ORDER BY
            -- prioritize exact matches then partial matches on snowflake account or alias
            CASE
                WHEN LOWER(a.name) = LOWER(%(search_query_value)s)
                    OR LOWER(a.alias) = LOWER(%(search_query_value)s) THEN 3
                WHEN LOWER(a.name) ILIKE LOWER(%(search_query_wildcard_pattern)s)
                    OR LOWER(a.alias) ILIKE LOWER(%(search_query_wildcard_pattern)s) THEN 2
                ELSE 1
            END DESC;
        """

        # 2. ACCOUNT METADATA - Comprehensive account information
        self.account_metadata = """
        -- Account metadata including deployment, service level, status, type
        SELECT
            a.name,
            a.alias,
            a.snowflake_deployment AS deployment,
            a.replication_group,
            a.snowflake_account_id AS account_id,
            ext.service_level_value AS service_level,
            DECODE(a.state,
                0, 'NON_EXISTENT',
                1, 'BLANK',
                2, 'ACTIVE',
                3, 'INACTIVE',
                4, 'PENDING',
                5, 'PENDING INVITATION',
                6, 'SUSPENDED',
                7, 'READY FOR SELF SERVICE',
                8, 'MARKED FOR DECOMMISSION'
            ) AS account_status,
            DECODE(a.type,
                1, 'CUSTOMER',
                2, 'INTERNAL',
                3, 'PARTNER',
                4, 'TRIAL',
                5, 'LEGACY',
                6, 'SELF_SERVICE',
                7, 'READER',
                8, 'TESTING',
                9, 'CAPACITY'
            ) AS account_type,
            a.deleted_on,
            ext.version_group,
            ext.release_group,
            a.is_org_admin,
            a.created_on,
            CASE
                WHEN a.LOAD_BALANCER_ID IS NULL OR a.LOAD_BALANCER_ID = 0 THEN 'Nginx'
                WHEN a.LOAD_BALANCER_ID = 1 THEN 'Envoy'
                ELSE '--'
            END AS load_balancer,
            dm.service_region,
            dm.engineering_region,
            dm.deployment_url,
            dm.cloud
        FROM
            table(%(fdtn_snwflk_account)s) a
        JOIN
            CXE_DEPLOYMENT_MAPPING_V dm ON a.snowflake_deployment = dm.deployment
        LEFT JOIN
            table(%(dda_account_extended_properties_history)s) ext
            ON a.snowflake_deployment = ext.deployment
            AND a.snowflake_account_id = ext.account_id
            AND IS_LAST
        WHERE
            a.replication_group IS NOT NULL
            AND a.name = %(acc_locator)s
            AND a.snowflake_deployment = %(dda_snwflk_deployment)s;
        """

        # 3. RELEASE VERSION HISTORY - Account release version timeline
        self.release_version = """
        -- Release version history for account
        SELECT RELEASE_VERSION, RELEASE_TIME
        FROM DDA_RELEASE_VERSION_HISTORY
        WHERE ACCOUNT_ID = %(account_id)s
            AND DEPLOYMENT = %(dda_snwflk_deployment)s
            AND GS_SERVICE_TYPE_ID = 1
            AND MAPPING_INDEX = 0
        -- gs_service_type_id = 1 means query cluster
        -- gs_service_type_id = 2 means auth_cluster
        -- mapping_index = 0 means permanent mapping, <0 means ephemeral
        ORDER BY RELEASE_TIME DESC;
        """

        # 4. ACCOUNT WAREHOUSES - List of warehouses for account
        self.get_account_warehouses = """
        -- Get all warehouses for an account with load data availability
        SELECT DISTINCT
            fwm.ID,
            fwm.WAREHOUSE_NAME,
            fwm.SIZE,
            fwm.WAREHOUSE_TYPE,
            fwm.LAST_PROVISIONED_ON,
            fwm.UPDATED_ON,
            fwm.CREATED_ON,
            fwm.DELETED_ON,
            IFNULL(lwqs.LOAD_DATA, false) AS LOAD_DATA,
            lwqs.START_TIME,
            lwqs.END_TIME
        FROM FDTN_WAREHOUSE_METADATA fwm
        JOIN (
            SELECT
                WAREHOUSE_NAME,
                MAX(UPDATED_ON) AS MaxUpdatedOn
            FROM FDTN_WAREHOUSE_METADATA
            WHERE ACCOUNT_ID = %(account_id)s
                AND DEPLOYMENT = %(dda_snwflk_deployment)s
            GROUP BY WAREHOUSE_NAME
        ) latest_update ON fwm.WAREHOUSE_NAME = latest_update.WAREHOUSE_NAME
            AND fwm.UPDATED_ON = latest_update.MaxUpdatedOn
        LEFT JOIN (
            SELECT
                WAREHOUSE_NAME,
                TRUE AS LOAD_DATA,
                MIN(cur_sec_slice) as START_TIME,
                MAX(cur_sec_slice) as END_TIME
            FROM dda_rel_wh_load_query_sec_slice
            WHERE ACCOUNT_ID = %(account_id)s
                AND DEPLOYMENT = %(dda_snwflk_deployment)s
            GROUP BY WAREHOUSE_NAME
        ) AS lwqs ON fwm.WAREHOUSE_NAME = lwqs.WAREHOUSE_NAME
        WHERE fwm.ACCOUNT_ID = %(account_id)s
            AND fwm.DEPLOYMENT = %(dda_snwflk_deployment)s
        ORDER BY fwm.LAST_PROVISIONED_ON DESC;
        """

        # 5. OPEN CASES FOR ACCOUNT - Salesforce cases
        self.get_open_cases_for_account = """
        -- Get open Salesforce cases for an account
        SELECT
            c.case_number,
            c.status,
            c.created_date,
            c.category_c as category,
            c.sub_category_c as sub_category,
            c.subject
        FROM table(%(fdtn_case)s) c
        WHERE c.snowflake_account_locator = %(acc_locator)s
            AND c.snowflake_account_alias = %(acc_alias)s
            AND c.status <> 'Closed'
            AND c.is_deleted = 0;
        """

        # 6. QUERIES FOR ACCOUNT - Queries executed on this account
        self.dda_quuid_with_same_account = """
        -- Get queries executed on this account
        SELECT
            QUERYID as query_id,
            CASENUMBER,
            CLIENT_SEND_TIME,
            SQL_TEXT_HASH::varchar as SQL_TEXT_HASH
        FROM table(%(query_metadata_view_or_table)s)
        WHERE DEPLOYMENT = %(dda_snwflk_deployment)s
            AND ACCOUNT_NAME = %(acc_locator)s
        ORDER BY CLIENT_SEND_TIME DESC;
        """

        # 7. ACCOUNT ENVIRONMENT - Get account environment type
        self.get_account_environment = """
        -- Get account environment (prod/dev/test)
        SELECT environment
        FROM DDA_REL_SF_PS_ACCOUNT_SNFL_ACCOUNT_DEPLOYMENT_V
        WHERE snowflake_account_id = %(account_id)s
            AND snowflake_deployment = %(dda_snwflk_deployment)s;
        """
