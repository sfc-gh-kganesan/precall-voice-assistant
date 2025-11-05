"""
User Authentication (SAML/OAUTH) Queries

This module contains SQL queries for analyzing SAML and OAUTH authentication issues.
"""


class AuthQueries:
    """SQL queries for user authentication diagnostics."""

    def __init__(self):
        # Find cases related to SAML/OAUTH authentication
        self.get_userauth_cases = """
            SELECT distinct case_number as casenumber
            FROM FIVETRAN.SALESFORCE.CASE c
            WHERE FUNCTIONAL_AREA_C = 'Security & Platform Governance'
                AND (
                    subject ILIKE '%SAML%' OR
                    subject ILIKE '%OAUTH%' OR
                    description ILIKE '%SAML%' OR
                    description ILIKE '%OAUTH%'
                )
                AND closed_date IS NULL
                AND is_closed = false
                AND created_date > dateadd('days', -45, current_date)
                AND NOT EXISTS (
                    SELECT 1
                    FROM FIVETRAN.SALESFORCE.CASE c2
                    WHERE c2.case_number = c.case_number
                      AND c2.closed_date IS NOT NULL
                );
        """

        # Get SAML integration list with HASH deduplication
        self.get_saml_list = """
            SELECT * EXCLUDE hash_value FROM (
                SELECT
                    integration_name,
                    integration_id,
                    deployment,
                    account_id,
                    created_on,
                    updated_on,
                    name_valid_from_time,
                    expired_time,
                    deleted_on,
                    integration_enabled,
                    saml2_x509_cert,
                    saml2_provider,
                    saml2_enable_sp_initiated,
                    saml2_sp_initiated_login_page_label,
                    saml2_sso_url,
                    saml2_issuer,
                    allowed_user_domains,
                    allowed_email_patterns,
                    saml2_snowflake_x509_cert,
                    saml2_requested_nameid_format,
                    saml2_force_authn,
                    saml2_post_logout_redirect_url,
                    HASH(
                        integration_name,
                        integration_id,
                        deployment,
                        account_id,
                        created_on,
                        name_valid_from_time,
                        expired_time,
                        deleted_on,
                        integration_enabled,
                        saml2_x509_cert,
                        saml2_provider,
                        saml2_enable_sp_initiated,
                        saml2_sp_initiated_login_page_label,
                        saml2_sso_url,
                        saml2_issuer,
                        allowed_user_domains,
                        allowed_email_patterns,
                        saml2_snowflake_x509_cert,
                        saml2_requested_nameid_format,
                        saml2_force_authn,
                        saml2_post_logout_redirect_url
                    ) AS hash_value,
                    MAX(updated_on) OVER (partition by hash_value) AS max_updated_on,
                    MAX(updated_on) OVER (partition by deployment, account_id, integration_name) AS last_updated_on,
                    IFF(last_updated_on = updated_on, true, false) AS is_last_updated_on
                FROM dda_rel_acc_md_saml_integration_v
            ) AS dda_rel_acc_md_saml_integration_hash
            WHERE
                account_id = %(account_id)s
                AND deployment = %(deployment)s
                AND is_last_updated_on
            ORDER BY updated_on DESC;
        """

        # Check if auth data exists in package table
        self.get_userauth_json_from_tsw_userauth_package = """
            -- Check if data exists in TSW_OAUTH_SAML_DATA_PACKAGE table
            SELECT DATA_PACKAGE, _ingestion_timestamp
            FROM TSW_OAUTH_SAML_DATA_PACKAGE
            WHERE case_number = %(case_number)s
                AND parse_json(deployment_account_id):deployment::string = %(deployment)s
                AND parse_json(deployment_account_id):account_id::number = %(account_id)s
            LIMIT 1;
        """

    # Dynamic methods for deployment-specific SNOWHOUSE_IMPORT tables
    def get_oauth_list(self, deployment: str) -> str:
        """
        Get OAUTH integration list from SNOWHOUSE_IMPORT.

        This is a complex CTE-based query that extracts OAUTH integration details
        including blocked/authorized roles.

        Args:
            deployment: Snowflake deployment name

        Returns:
            SQL query string
        """
        return (
            "WITH int_types AS (\n"
            "    SELECT key, value\n"
            "    FROM TABLE(FLATTEN(input => parse_json(SYSTEM$DUMP_ENUM('IntegrationType'))))\n"
            "    WHERE value LIKE '%%OAUTH%%'\n"
            "),\n"
            "account_integrations AS (\n"
            f"    SELECT account_id, id, name, created_on, deleted_on, enabled, parse_json(DPO) AS dpo_json\n"
            f"    FROM SNOWHOUSE_IMPORT.{deployment}.integration_etl_v\n"
            "    WHERE account_id = %(account_id)s\n"
            "      AND deleted_on IS NULL\n"
            "      AND type_id IN (SELECT key FROM int_types)\n"
            "),\n"
            "basic AS (\n"
            "    SELECT\n"
            "      account_id, id, name, created_on, deleted_on, enabled, dpo_json,\n"
            '      dpo_json:"IntegrationDPO:primary":"basicInfo":redirectURI::string AS redirect_url,\n'
            '      dpo_json:"IntegrationDPO:primary":"basicInfo":refreshTokenValidity::string AS refresh_token_validity,\n'
            '      dpo_json:"IntegrationDPO:primary":"basicInfo":clientId::string AS client_id\n'
            "    FROM account_integrations\n"
            "),\n"
            "blocked_ids AS (\n"
            "    SELECT b.id, b.account_id, fl.value::int AS blocked_role_id\n"
            '    FROM basic b, LATERAL FLATTEN(input => b.dpo_json:"IntegrationDPO:primary":"basicInfo":blockedRolesList) fl\n'
            "),\n"
            "authorized_ids AS (\n"
            "    SELECT b.id, b.account_id, fl.value::int AS authorized_role_id\n"
            '    FROM basic b, LATERAL FLATTEN(input => b.dpo_json:"IntegrationDPO:primary":"basicInfo":authorizedRolesList) fl\n'
            "),\n"
            "blocked AS (\n"
            f"    SELECT bi.id, bi.account_id, r.name AS blocked_role_name\n"
            f"    FROM blocked_ids bi LEFT JOIN SNOWHOUSE_IMPORT.{deployment}.role_etl_v r\n"
            "      ON r.id = bi.blocked_role_id AND r.account_id = bi.account_id\n"
            "),\n"
            "authorized AS (\n"
            f"    SELECT ai.id, ai.account_id, r.name AS authorized_role_name\n"
            f"    FROM authorized_ids ai LEFT JOIN SNOWHOUSE_IMPORT.{deployment}.role_etl_v r\n"
            "      ON r.id = ai.authorized_role_id AND r.account_id = ai.account_id\n"
            ")\n"
            "SELECT\n"
            "  b.name AS NAME,\n"
            "  b.id AS ID,\n"
            "  b.created_on AS CREATED_ON,\n"
            "  b.deleted_on AS DELETED_ON,\n"
            "  b.enabled AS ENABLED,\n"
            "  b.redirect_url AS REDIRECT_URL,\n"
            "  b.refresh_token_validity AS REFRESH_TOKEN_VALIDITY,\n"
            "  b.client_id AS CLIENT_ID,\n"
            "  LISTAGG(DISTINCT a.authorized_role_name, ', ') WITHIN GROUP (ORDER BY a.authorized_role_name) AS AUTHORIZED_ROLE_NAMES,\n"
            "  LISTAGG(DISTINCT bl.blocked_role_name, ', ') WITHIN GROUP (ORDER BY bl.blocked_role_name) AS BLOCKED_ROLE_NAMES\n"
            "FROM basic b\n"
            "LEFT JOIN authorized a ON a.id = b.id AND a.account_id = b.account_id\n"
            "LEFT JOIN blocked bl ON bl.id = b.id AND bl.account_id = b.account_id\n"
            "GROUP BY b.name, b.id, b.created_on, b.deleted_on, b.enabled, b.redirect_url, b.refresh_token_validity, b.client_id;"
        )

    def get_saml_logs(self, deployment: str) -> str:
        """
        Get SAML authentication logs from SNOWHOUSE_IMPORT.

        Args:
            deployment: Snowflake deployment name

        Returns:
            SQL query string
        """
        return (
            "SELECT\n"
            "    timestamp,\n"
            "    gs_cluster,\n"
            "    level,\n"
            "    class,\n"
            "    thread,\n"
            "    message\n"
            f"FROM SNOWHOUSE_IMPORT.{deployment}.gs_logs_v\n"
            "WHERE account_id = %(account_id)s\n"
            "  AND (message LIKE 'SECURITY:SAML%%' OR message LIKE '%%User%%not found%%')\n"
            "  AND timestamp BETWEEN %(start_time)s AND %(end_time)s\n"
            "ORDER BY timestamp DESC;"
        )

    def get_oauth_logs(self, deployment: str) -> str:
        """
        Get OAUTH authentication logs from SNOWHOUSE_IMPORT.

        Args:
            deployment: Snowflake deployment name

        Returns:
            SQL query string
        """
        return (
            "SELECT\n"
            "    timestamp,\n"
            "    gs_cluster,\n"
            "    level,\n"
            "    class,\n"
            "    thread,\n"
            "    message\n"
            f"FROM SNOWHOUSE_IMPORT.{deployment}.gs_logs_v\n"
            "WHERE account_id = %(account_id)s\n"
            "  AND message LIKE 'SECURITY%%OAUTH%%'\n"
            "  AND timestamp BETWEEN %(start_time)s AND %(end_time)s\n"
            "ORDER BY timestamp DESC;"
        )
