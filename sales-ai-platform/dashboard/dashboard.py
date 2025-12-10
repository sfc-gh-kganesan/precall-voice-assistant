import os
from pathlib import Path

import altair as alt
import snowflake.connector
import streamlit as st
from dotenv import load_dotenv
from snowflake.snowpark import Session

load_dotenv()

# ----------------------------
# Load environment variables
# ----------------------------
eval_results_table = os.getenv("EVAL_RESULTS_TABLE")
eval_correctness_results_table = os.getenv("EVAL_CORRECTNESS_RESULTS_TABLE")
database = os.getenv("DATABASE")
schema = os.getenv("SCHEMA")
st.set_page_config(page_title="Eval Dashboard", layout="wide")


# ----------------------------
# 1. Connect to Snowflake
# ----------------------------
def create_snowflake_session():
    account = os.getenv("SNOWFLAKE_ACCOUNT")
    user = os.getenv("SNOWFLAKE_USER")
    warehouse = os.getenv("SNOWFLAKE_WAREHOUSE")
    database = os.getenv("SNOWFLAKE_DATABASE")
    schema = os.getenv("SNOWFLAKE_SCHEMA")
    role = os.getenv("SNOWFLAKE_ROLE")

    # -----------------------
    # LOCAL MODE: Uses Okta SSO with external browser
    # -----------------------
    if Path("/snowflake/session/token").exists():
        token_path = Path("/snowflake/session/token")
        snowflake_conn = snowflake.connector.connect(
            host=os.getenv("SNOWFLAKE_HOST"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            token=token_path.read_text().strip(),
            authenticator="oauth",
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        )

        return Session.builder.configs({"connection": snowflake_conn}).getOrCreate()

    st.write("Using LOCAL environment authentication (externalbrowser)")
    return Session.builder.configs(
        {
            "account": account,
            "user": user,
            "authenticator": "externalbrowser",
            "warehouse": warehouse,
            "database": database,
            "schema": schema,
            "role": role,
        }
    ).create()


session = create_snowflake_session()


# ----------------------------
# 2. Load the eval table
# ----------------------------
@st.cache_data(ttl=300)
def load_data(table_name: str):
    try:
        df = session.table(table_name)
    except Exception as e:
        st.error(f"Error loading data from table {table_name}: {e}")
        return None
    return df.to_pandas()


eval_results_df = load_data(f"{database}.{schema}.{eval_results_table}")
eval_correctness_results_df = load_data(f"{database}.{schema}.{eval_correctness_results_table}")

# ----------------------------
# 3. Sidebar filters
# ----------------------------
st.sidebar.header("Filters")

graph_versions = sorted(eval_results_df["GRAPH_VERSION"].dropna().unique())
selected_versions = st.sidebar.multiselect("Graph Version", graph_versions, default=graph_versions)

owners = sorted(eval_results_df["OWNER_ID"].dropna().unique())
selected_owners = st.sidebar.multiselect("Owner", owners)

start_date = st.sidebar.date_input("Start Date", eval_results_df["EVAL_DTTM"].min().date())
end_date = st.sidebar.date_input("End Date", eval_results_df["EVAL_DTTM"].max().date())

# Apply filters
mask = eval_results_df["GRAPH_VERSION"].isin(selected_versions) & (eval_results_df["EVAL_DTTM"].dt.date >= start_date) & (eval_results_df["EVAL_DTTM"].dt.date <= end_date)

if selected_owners:
    mask = mask & eval_results_df["OWNER_ID"].isin(selected_owners)

filtered = eval_results_df[mask]

# ----------------------------
# 4. KPI Metrics
# ----------------------------
st.title("Use Case Summary Evaluation Dashboard")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Average Accuracy", f"{filtered['ACCURACY'].mean():.2f}")
col2.metric("Average Groundedness", f"{filtered['GROUNDEDNESS'].mean():.2f}")
col3.metric("Average Completeness", f"{filtered['COMPLETENESS'].mean():.2f}")
col4.metric("Average Actionability", f"{filtered['ACTIONABILITY'].mean():.2f}")

# ----------------------------
# 5. Time-series chart
# ----------------------------
st.subheader("Average Evaluation Metrics Over Time (Daily)")

# Select columns
chart_data = filtered[["EVAL_DTTM", "ACCURACY", "GROUNDEDNESS", "COMPLETENESS", "ACTIONABILITY"]]

# Convert timestamp → day bins
chart_data["DAY"] = chart_data["EVAL_DTTM"].dt.floor("D")  # or: chart_data["EVAL_DTTM"].dt.date

# Group by day and average metrics for that day
daily = chart_data.groupby("DAY").agg({"ACCURACY": "mean", "GROUNDEDNESS": "mean", "COMPLETENESS": "mean", "ACTIONABILITY": "mean"})

# Plot
st.line_chart(daily)


# ----------------------------
# 6. Graph Version Comparison
# ----------------------------
st.subheader("Metric Distributions (All Graph Versions)")

metrics = ["ACCURACY", "GROUNDEDNESS", "COMPLETENESS", "ACTIONABILITY"]

for metric in metrics:
    st.write(f"### {metric} Distribution")

    chart = alt.Chart(filtered).mark_bar(opacity=0.7).encode(alt.X(metric, bin=alt.Bin(maxbins=20), title=f"{metric}"), alt.Y("count()", title="Count")).properties(height=200, width="container")

    st.altair_chart(chart)

# ----------------------------
# 7. Full table
# ----------------------------
st.subheader("Detailed Results")

st.dataframe(
    filtered[
        [
            "EVAL_ID",
            "ACTIVITY_ID",
            "OWNER_ID",
            "SALESFORCE_ACCOUNT_ID",
            "ACCURACY",
            "GROUNDEDNESS",
            "COMPLETENESS",
            "ACTIONABILITY",
            "GRAPH_VERSION",
            "EVAL_DTTM",
        ]
    ],
)
