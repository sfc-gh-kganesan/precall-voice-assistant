import os

DATABASE = os.getenv("DATABASE")
SCHEMA = os.getenv("SCHEMA")


def build_eval_insert_query(eval_id: str, salesforce_account_id: str, owner_id: str, activity_id: str, graph_version: str, scores: dict) -> str:
    return f"""
        MERGE INTO {DATABASE}.{SCHEMA}.use_case_summary_eval_results AS t
        USING (
            SELECT
                '{eval_id}' AS eval_id,
                '{activity_id}' AS activity_id,
                '{owner_id}' AS owner_id,
                '{salesforce_account_id}' AS salesforce_account_id,
                {scores.get("accuracy", "NULL")} AS accuracy,
                {scores.get("groundedness", "NULL")} AS groundedness,
                {scores.get("completeness", "NULL")} AS completeness,
                {scores.get("actionability", "NULL")} AS actionability,
                '{graph_version}' AS graph_version
        ) AS s
        ON t.eval_id = s.eval_id
        WHEN NOT MATCHED THEN INSERT (
            eval_id,
            activity_id,
            owner_id,
            salesforce_account_id,
            accuracy,
            groundedness,
            completeness,
            actionability,
            graph_version
        )
        VALUES (
            s.eval_id,
            s.activity_id,
            s.owner_id,
            s.salesforce_account_id,
            s.accuracy,
            s.groundedness,
            s.completeness,
            s.actionability,
            s.graph_version
        );
    """


def build_eval_correctness_results_query(
    eval_id: str,
    graph_version: str,
    eval_success: bool,
    eval_error_message: str,
    error_stage: str,
) -> str:
    """
    Build the evaluation correctness results query.
    """
    # SQL-escape error message for quotes
    eval_error_message = eval_error_message.replace("'", "''")
    error_stage = error_stage.replace("'", "''")

    return f"""
        MERGE INTO {DATABASE}.{SCHEMA}.use_case_summary_eval_correctness_results AS t
        USING (
            SELECT
                '{eval_id}' AS eval_id,
                '{graph_version}' AS graph_version,
                {eval_success} AS eval_success,
                '{eval_error_message}' AS eval_error_message,
                '{error_stage}' AS error_stage,
                CURRENT_TIMESTAMP() AS eval_dttm
        ) AS s
        ON t.eval_id = s.eval_id
        WHEN NOT MATCHED THEN
            INSERT (
                eval_id,
                graph_version,
                eval_success,
                eval_error_message,
                error_stage,
                eval_dttm
            )
            VALUES (
                s.eval_id,
                s.graph_version,
                s.eval_success,
                s.eval_error_message,
                s.error_stage,
                s.eval_dttm
            );
    """


def build_eval_results_lookup_query(eval_id: str) -> str:
    return f"""
        SELECT *
        FROM {DATABASE}.{SCHEMA}.use_case_summary_eval_results
        WHERE eval_id = '{eval_id}'
        LIMIT 1;
    """


def build_eval_state_lookup_query(eval_id: str) -> str:
    return f"""
        SELECT *
        FROM {DATABASE}.{SCHEMA}.use_case_summary_eval_correctness_results
        WHERE eval_id = '{eval_id}'
        ORDER BY eval_dttm DESC
        LIMIT 1;
    """


def build_eval_transcript_lookup_query(owner_id: str, activity_id: str, salesforce_account_id: str) -> str:
    return f"""
        SELECT RAW_CONTENT
        FROM sales.engagement360_pitch.all_engagement_details
        WHERE owner_id = '{owner_id}'
        AND activity_id = '{activity_id}'
        AND salesforce_account_id = '{salesforce_account_id}'
        ORDER BY activity_date DESC
        LIMIT 1;
    """
