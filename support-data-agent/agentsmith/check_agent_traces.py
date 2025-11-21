#!/usr/bin/env python3
"""Query AGENT_TRACES_NG to validate data structure for conversation loading."""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment
load_dotenv("backend/.env")

# Get Snowflake connection from env
account = os.getenv("SNOWFLAKE_ACCOUNT")
user = os.getenv("SNOWFLAKE_USER")
password = os.getenv("SNOWFLAKE_PASSWORD")
warehouse = os.getenv("SNOWFLAKE_WAREHOUSE")
database = "AI_FDE"
schema = "CX360_DEMO"
role = os.getenv("SNOWFLAKE_ROLE")

print(f"Connecting to Snowflake: {account}/{database}/{schema}")
print(f"User: {user}, Warehouse: {warehouse}, Role: {role}\n")

conn_str = f"snowflake://{user}:{password}@{account}/{database}/{schema}?warehouse={warehouse}&role={role}"
engine = create_engine(conn_str)

# Query sample api.query rows
query = text("""
    SELECT
        conversation_id,
        name,
        CASE WHEN input_text IS NOT NULL THEN 'YES' ELSE 'NO' END as has_input,
        CASE WHEN output_text IS NOT NULL THEN 'YES' ELSE 'NO' END as has_output,
        LENGTH(input_text) as input_len,
        LENGTH(output_text) as output_len,
        SUBSTR(input_text, 1, 80) as input_preview,
        SUBSTR(output_text, 1, 80) as output_preview
    FROM AI_FDE.CX360_DEMO.AGENT_TRACES_NG
    WHERE name = 'api.query'
        AND conversation_id IS NOT NULL
        AND start_time >= DATEADD(day, -7, CURRENT_TIMESTAMP())
    LIMIT 10
""")

print("Querying AGENT_TRACES_NG for api.query rows...\n")

with engine.connect() as conn:
    result = conn.execute(query)
    rows = result.fetchall()

    print(f"Found {len(rows)} sample api.query rows:\n")
    print("=" * 80)

    for i, row in enumerate(rows, 1):
        print(f"\n{i}. Conversation: {row[0]}")
        print(f"   Has Input: {row[2]}, Has Output: {row[3]}")
        print(f"   Input Length: {row[4]}, Output Length: {row[5]}")
        if row[6]:
            print(f"   Input Preview: {row[6][:60]}...")
        if row[7]:
            print(f"   Output Preview: {row[7][:60]}...")

    print("\n" + "=" * 80)

    # Summary statistics
    both_count = sum(1 for row in rows if row[2] == "YES" and row[3] == "YES")
    input_only = sum(1 for row in rows if row[2] == "YES" and row[3] == "NO")
    output_only = sum(1 for row in rows if row[2] == "NO" and row[3] == "YES")

    print("\nSummary:")
    print(f"  Rows with BOTH input and output: {both_count}/{len(rows)}")
    print(f"  Rows with input only: {input_only}/{len(rows)}")
    print(f"  Rows with output only: {output_only}/{len(rows)}")

    if both_count == len(rows):
        print("\n✅ All rows have BOTH input and output - fix will work as expected!")
    elif both_count > 0:
        print(
            f"\n⚠️  Most rows ({both_count}/{len(rows)}) have both, but some don't - fix will handle both cases"
        )
    else:
        print(
            "\n❌ NO rows have both input and output - need to reconsider the approach"
        )
