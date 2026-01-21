from datetime import datetime

import pandas as pd
import snowflake.snowpark as sp
from config import db_config, search_config
from data_operations import SnowflakeDataOperations
from snowflake.snowpark import Session
from snowflake.snowpark import functions as F
from snowflake.snowpark import types as T


def ingest_knowledge(session: Session, fp: str, table_name: str, mode: str) -> sp.DataFrame:
    df = pd.read_csv(fp, encoding="latin_1").rename(columns=str.upper)
    session.create_dataframe(df).write.save_as_table(table_name, mode=mode)
    return session.table(table_name)


def ingest_golden_pairs(session: Session, table_name: str, mode: str = "overwrite") -> sp.DataFrame:
    data = [
        {"INCIDENT": "INC0010234", "INPUT_QUERY": "I cannot connect to the VPN while working from home.", "SUGGESTED_RESOLUTION_CURATED": "Ensure Cisco AnyConnect is updated. Reset your AD password and try reconnecting via the 'Full Tunnel' gateway."},
        {"INCIDENT": "INC0010567", "INPUT_QUERY": "Outlook keeps crashing when I try to open calendar invites.", "SUGGESTED_RESOLUTION_CURATED": "Run Outlook in Safe Mode, disable the 'Teams Meeting' add-in, and clear the local AppData cache for Microsoft Office."},
        {"INCIDENT": "INC0010890", "INPUT_QUERY": "Requesting admin access for software installation on Macbook.", "SUGGESTED_RESOLUTION_CURATED": "Check if the software is in the Self-Service portal. If not, manager approval is required before granting temporary SUDO rights."},
        {"INCIDENT": "INC0011221", "INPUT_QUERY": "Printer in the London office (2nd floor) is jammed and showing error 404.", "SUGGESTED_RESOLUTION_CURATED": "On-site facilities notified. Hardware reset performed; confirmed paper tray 2 was overloaded with A3 paper."},
        {"INCIDENT": "INC0011456", "INPUT_QUERY": "New hire needs access to the Snowflake production warehouse.", "SUGGESTED_RESOLUTION_CURATED": "Assign the user to the 'SNOWFLAKE_PROD_READ' Okta group. Sync may take up to 30 minutes to reflect in the Cortex search role."},
    ]
    df = pd.DataFrame(data)
    session.write_pandas(df.reset_index(drop=True), table_name, auto_create_table=True, overwrite=(mode == "overwrite"))
    return session.table(table_name)


def ingest_synthetic_pairs(session: Session, table_name: str, mode: str = "overwrite") -> sp.DataFrame:
    data = [
        {
            "SOURCE_TABLE": "SEED_DATA",
            "ATTRS": {},
            "SCORING": {},
            "GENERATED": {"query": "I received a suspicious email asking for my login credentials.", "answer": "This appears to be a phishing attempt. Do not click any links or provide credentials. Forward the email to security@company.com and delete it from your inbox."},
            "L1_RAW": "it services",
            "L2_RAW": "access management",
            "L3_RAW": "authentication",
            "L4_RAW": "request process",
            "L1_TAG": "IT Services",
            "L2_TAG": "User Access Provisioning",
            "L3_TAG": "Access and Authentication Management",
            "L4_TAG": "Privileged Access Authentication Workflow",
        },
        {
            "SOURCE_TABLE": "SEED_DATA",
            "ATTRS": {},
            "SCORING": {},
            "GENERATED": {"query": "My company iPhone is stuck on the Apple logo after an update.", "answer": "Perform a forced restart by pressing and releasing Volume Up, then Volume Down, then holding the Side button until the Apple logo reappears. If unsuccessful, use DFU mode restoration."},
            "L1_RAW": "hardware",
            "L2_RAW": "server management",
            "L3_RAW": "batch job management",
            "L4_RAW": "troubleshooting",
            "L1_TAG": "IT Services",
            "L2_TAG": "Network Resource Management",
            "L3_TAG": "Batch Job Failure Troubleshooting",
            "L4_TAG": "Technical Error Type Classification",
        },
        {
            "SOURCE_TABLE": "SEED_DATA",
            "ATTRS": {},
            "SCORING": {},
            "GENERATED": {"query": "Locked out of Workday after three failed login attempts.", "answer": "Your account has been temporarily locked for security. Wait 15 minutes or contact IT Help Desk to manually unlock your account and reset your password."},
            "L1_RAW": "access management",
            "L2_RAW": "active directory",
            "L3_RAW": "account management",
            "L4_RAW": "account management",
            "L1_TAG": "Access Management",
            "L2_TAG": "Account Access Management",
            "L3_TAG": "Identity and Access Management",
            "L4_TAG": "User Account Permission Management",
        },
        {
            "SOURCE_TABLE": "SEED_DATA",
            "ATTRS": {},
            "SCORING": {},
            "GENERATED": {"query": "External monitor is not detecting my laptop via the USB-C dock.", "answer": "Try these steps: 1) Unplug and reconnect the dock, 2) Update DisplayLink drivers, 3) Check display settings to detect external monitors, 4) Try a different USB-C port or cable."},
            "L1_RAW": "hardware",
            "L2_RAW": "monitoring",
            "L3_RAW": "storage management",
            "L4_RAW": "troubleshooting",
            "L1_TAG": "IT Services",
            "L2_TAG": "Network Connectivity Issues",
            "L3_TAG": "Software Application Functionality",
            "L4_TAG": "Application Specific Configuration Issues",
        },
        {
            "SOURCE_TABLE": "SEED_DATA",
            "ATTRS": {},
            "SCORING": {},
            "GENERATED": {"query": "Adobe Creative Cloud says my trial has expired, but I have a license.", "answer": "Sign out of Adobe Desktop app, then sign back in using 'Company Account' SSO option. If the issue persists, verify your license is assigned in the Adobe Admin Console."},
            "L1_RAW": "software",
            "L2_RAW": "applications",
            "L3_RAW": "authentication",
            "L4_RAW": "error resolution",
            "L1_TAG": "Application Systems",
            "L2_TAG": "Enterprise Software Applications",
            "L3_TAG": "Enterprise Software Applications",
            "L4_TAG": "Application Launch Failure Diagnostics",
        },
    ]
    df = session.create_dataframe(
        data,
        schema=T.StructType(
            [
                T.StructField("SOURCE_TABLE", T.StringType()),
                T.StructField("ATTRS", T.VariantType()),
                T.StructField("SCORING", T.VariantType()),
                T.StructField("GENERATED", T.VariantType()),
                T.StructField("L1_RAW", T.StringType()),
                T.StructField("L2_RAW", T.StringType()),
                T.StructField("L3_RAW", T.StringType()),
                T.StructField("L4_RAW", T.StringType()),
                T.StructField("L1_TAG", T.StringType()),
                T.StructField("L2_TAG", T.StringType()),
                T.StructField("L3_TAG", T.StringType()),
                T.StructField("L4_TAG", T.StringType()),
            ]
        ),
    )
    df.write.save_as_table(table_name, mode=mode, column_order="name")
    return session.table(table_name)


def search_golden_pairs(
    session: Session,
    data_ops: SnowflakeDataOperations,
    df: pd.DataFrame | sp.DataFrame,
) -> None:
    if isinstance(df, sp.DataFrame):
        df = df.to_pandas()
    current_user = session.get_current_user()
    css = data_ops.get_cortex_search_service()
    for _, row in df.iterrows():
        input_query = row["INPUT_QUERY"]
        search_args = search_config.to_dict()
        search_args["query"] = input_query
        resp = css.search(**search_args)
        data_ops.save_search(
            [
                [
                    "GOLDEN_PAIR",
                    search_args,
                    resp.results,
                    current_user,
                    datetime.now(),
                ]
            ]
        )


def search_synthetic_pairs(
    session: Session,
    data_ops: SnowflakeDataOperations,
    df: sp.DataFrame,
) -> None:
    pdf = df.select(F.col("GENERATED")["query"].cast(T.StringType()).alias("INPUT_QUERY")).to_pandas()
    current_user = session.get_current_user()
    css = data_ops.get_cortex_search_service()
    for _, row in pdf.iterrows():
        input_query = row["INPUT_QUERY"]
        search_args = search_config.to_dict()
        search_args["query"] = input_query
        resp = css.search(**search_args)
        data_ops.save_search(
            [
                [
                    "SYNTHETIC_PAIR",
                    search_args,
                    resp.results,
                    current_user,
                    datetime.now(),
                ]
            ]
        )


def deduplicate_search_results(session: Session) -> None:
    table_name = db_config.get_table_name(db_config.results_table)
    session.sql(f"""DELETE FROM {table_name}
    USING
    (
        SELECT SEARCH_ID,
               ROW_NUMBER() OVER
                    (
                        PARTITION BY INPUT_TYPE, INPUT_ARGS, RESPONSE, CREATED_BY
                        ORDER BY CREATED_ON
                    ) AS ROW_NUM
        FROM {table_name}
        QUALIFY ROW_NUM > 1
    ) AS SRC
    WHERE {table_name}.SEARCH_ID = SRC.SEARCH_ID""").collect()


def get_unsearched_golden_pairs(session: Session) -> sp.DataFrame:
    """Get golden pairs that haven't been searched yet."""
    golden_pairs = session.table(db_config.get_table_name(db_config.golden_pairs_table))
    searched_queries = (
        session.table(db_config.get_table_name(db_config.results_table))
        .filter(F.col("INPUT_TYPE") == "GOLDEN_PAIR")
        .select(F.col("INPUT_ARGS")["query"].cast(T.StringType()).alias("INPUT_QUERY"))
        .distinct()
    )
    return golden_pairs.join(searched_queries, on="INPUT_QUERY", how="anti")


def get_unsearched_synthetic_pairs(session: Session) -> sp.DataFrame:
    """Get synthetic pairs that haven't been searched yet."""
    synthetic_pairs = session.table(db_config.get_table_name(db_config.synthetic_pairs_table))
    searched_queries = (
        session.table(db_config.get_table_name(db_config.results_table))
        .filter(F.col("INPUT_TYPE") == "SYNTHETIC_PAIR")
        .select(F.col("INPUT_ARGS")["query"].cast(T.StringType()).alias("INPUT_QUERY"))
        .distinct()
    )
    synthetic_with_query = synthetic_pairs.with_column(
        "INPUT_QUERY",
        F.col("GENERATED")["query"].cast(T.StringType())
    )
    return synthetic_with_query.join(searched_queries, on="INPUT_QUERY", how="anti")


def sync_searches(
    session: Session,
    data_ops: SnowflakeDataOperations,
    sync_golden: bool = True,
    sync_synthetic: bool = True,
) -> dict:
    """
    Sync searches for golden pairs and synthetic pairs that haven't been searched yet.
    Returns a dict with counts of synced items.
    """
    results = {"golden_pairs": 0, "synthetic_pairs": 0}

    if sync_golden:
        unsearched_golden = get_unsearched_golden_pairs(session)
        count = unsearched_golden.count()
        if count > 0:
            search_golden_pairs(session, data_ops, unsearched_golden)
            results["golden_pairs"] = count

    if sync_synthetic:
        unsearched_synthetic = get_unsearched_synthetic_pairs(session)
        count = unsearched_synthetic.count()
        if count > 0:
            search_synthetic_pairs(session, data_ops, unsearched_synthetic)
            results["synthetic_pairs"] = count

    if results["golden_pairs"] > 0 or results["synthetic_pairs"] > 0:
        deduplicate_search_results(session)

    return results


def get_sync_status(session: Session) -> dict:
    """Get the current sync status showing how many pairs need to be synced."""
    unsearched_golden = get_unsearched_golden_pairs(session).count()
    unsearched_synthetic = get_unsearched_synthetic_pairs(session).count()
    return {
        "unsearched_golden_pairs": unsearched_golden,
        "unsearched_synthetic_pairs": unsearched_synthetic,
    }
