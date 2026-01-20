from datetime import datetime

import pandas as pd
import snowflake.snowpark as sp
from data_operations import SnowflakeDataOperations
from snowflake.snowpark import Session
from snowflake.snowpark import functions as F
from snowflake.snowpark import types as T

from config import db_config, search_config


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
        {"INCIDENT": "INC0012101", "INPUT_QUERY": "I received a suspicious email asking for my login credentials.", "SUGGESTED_RESOLUTION_CURATED": "Email identified as phishing. Purged from inbox and user directed to complete security awareness training."},
        {"INCIDENT": "INC0012345", "INPUT_QUERY": "My company iPhone is stuck on the Apple logo after an update.", "SUGGESTED_RESOLUTION_CURATED": "Perform a forced restart. If unsuccessful, use Apple Configurator to restore the device to factory settings."},
        {"INCIDENT": "INC0012678", "INPUT_QUERY": "Locked out of Workday after three failed login attempts.", "SUGGESTED_RESOLUTION_CURATED": "Unlocked account in Active Directory. User advised to clear browser cookies before attempting to log in again."},
        {"INCIDENT": "INC0012899", "INPUT_QUERY": "External monitor is not detecting my laptop via the USB-C dock.", "SUGGESTED_RESOLUTION_CURATED": "Update DisplayLink drivers and power cycle the docking station by unplugging it for 30 seconds."},
        {"INCIDENT": "INC0013112", "INPUT_QUERY": "Adobe Creative Cloud says my trial has expired, but I have a license.", "SUGGESTED_RESOLUTION_CURATED": "Signed out and back into the Adobe Desktop app using the 'Company Account' SSO option."},
    ]
    df = pd.DataFrame(data)
    session.write_pandas(df.reset_index(drop=True), table_name, auto_create_table=True, overwrite=True)
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
    pdf = df.select(F.parse_json("INPUT_ARGS")["query"].cast(T.StringType()).alias("INPUT_QUERY")).to_pandas()
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


def ensure_analyze_image_links_proc(session: Session) -> None:
    proc_name = db_config.get_table_name("ANALYZE_IMAGE_LINKS")
    kb_table = db_config.get_table_name(db_config.kb_knowledge_table)
    session.sql(f"""
CREATE OR REPLACE PROCEDURE {proc_name}()
RETURNS TABLE (CATEGORY STRING, COUNT INT, DISTINCT_ARTICLES INT)
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python', 'lxml', 'pandas')
HANDLER = 'run'
EXECUTE AS CALLER
COMMENT = 'Analyze image src links from KB articles. Returns categories: base64, relative, sys_attachment, or domain.'
AS
$$
import pandas as pd
from lxml import html as lxml_html
from urllib.parse import urlparse
from snowflake.snowpark import Session

def extract_image_srcs(html_text: str) -> list:
    if not html_text or not isinstance(html_text, str):
        return []
    try:
        doc = lxml_html.fromstring(html_text)
        return doc.xpath('//img/@src')
    except Exception:
        return []

def categorize_src(src: str) -> str:
    if not src:
        return None
    src = src.strip()
    if src.startswith('data:'):
        return '[1] base64'
    if '/sys_attachment.do?' in src or src.startswith('sys_attachment.do?'):
        return '[2] sys_attachment'
    if src.startswith(('http://', 'https://', '//')):
        try:
            if src.startswith('//'):
                src = 'https:' + src
            parsed = urlparse(src)
            domain = parsed.netloc.lower()
            if domain:
                return domain
        except Exception:
            pass
        return '[4] unknown_url'
    return '[3] relative'

def run(session: Session):
    df = session.sql(\"\"\"
        SELECT SYS_ID, TEXT
        FROM {kb_table}
        WHERE TEXT IS NOT NULL AND ACTIVE = TRUE AND LATEST = TRUE
    \"\"\").to_pandas()

    if df.empty:
        return session.create_dataframe([], schema=["CATEGORY", "COUNT", "DISTINCT_ARTICLES"])

    processed_data = [(row["SYS_ID"], extract_image_srcs(row["TEXT"])) for _, row in df.iterrows()]
    temp_df = pd.DataFrame(processed_data, columns=["ARTICLE_ID", "IMG_SRC"])
    exploded_df = temp_df.explode("IMG_SRC").dropna(subset=["IMG_SRC"])

    if exploded_df.empty:
        return session.create_dataframe([], schema=["CATEGORY", "COUNT", "DISTINCT_ARTICLES"])

    exploded_df["CATEGORY"] = exploded_df["IMG_SRC"].apply(categorize_src)
    result = exploded_df.groupby("CATEGORY").agg(
        COUNT=("CATEGORY", "size"),
        DISTINCT_ARTICLES=("ARTICLE_ID", "nunique")
    ).reset_index()

    def sort_key(row):
        if row["CATEGORY"].startswith("["):
            return (0, row["CATEGORY"], 0)
        return (1, "", -row["COUNT"])

    result["_sort"] = result.apply(sort_key, axis=1)
    result = result.sort_values("_sort").drop(columns=["_sort"]).reset_index(drop=True)
    result["COUNT"] = result["COUNT"].astype(int)
    result["DISTINCT_ARTICLES"] = result["DISTINCT_ARTICLES"].astype(int)

    return session.create_dataframe(result)
$$
""").collect()
