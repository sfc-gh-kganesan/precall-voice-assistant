from datetime import datetime

import pandas as pd
from snowflake.core import Root
from snowflake.snowpark import Session
from snowflake.snowpark import functions as F
from snowflake.snowpark import types as T

from config import db_config, search_config


class SnowflakeDataOperations:
    def __init__(self, session: Session):
        self._session = session
        self._root = Root(session)

    def _ensure_evaluation_table_exists(self) -> None:
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {db_config.get_table_name(db_config.evaluation_results_table)} (
            EVAL_ID INTEGER AUTOINCREMENT PRIMARY KEY,
            QUERY STRING NOT NULL,
            CONTEXT STRING,
            ANSWER STRING,
            METRICS VARIANT,
            REASONS VARIANT,
            CREATED_BY STRING,
            CREATED_ON TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
        """
        comment_sql = f"""
        COMMENT ON TABLE {db_config.get_table_name(db_config.evaluation_results_table)} IS
        'Stores LLM-as-a-Judge evaluation results with TruLens chain-of-thought reasoning'
        """
        self._session.sql(create_table_sql).collect()
        self._session.sql(comment_sql).collect()

    def validate_environment(self) -> tuple[bool, list]:
        required_tables = [
            db_config.target_table,
            db_config.results_table,
            db_config.golden_pairs_table,
        ]
        missing_resources = []

        try:
            database = self._root.databases[db_config.database]
            schema = database.schemas[db_config.schema]

            for table_name in required_tables:
                try:
                    _ = schema.tables[table_name]
                except Exception:
                    missing_resources.append(f"Table: {db_config.get_table_name(table_name)}")

            try:
                _ = schema.cortex_search_services[db_config.search_service]
            except Exception:
                missing_resources.append(f"Cortex Search Service: {db_config.get_table_name(db_config.search_service)}")

            self._ensure_evaluation_table_exists()

        except Exception as e:
            return False, [f"Failed to validate environment: {str(e)}"]

        return len(missing_resources) == 0, missing_resources

    def get_cortex_search_service(self):
        database = self._root.databases[db_config.database]
        schema = database.schemas[db_config.schema]
        return schema.cortex_search_services[db_config.search_service]

    def save_search(self, data: list) -> None:
        search_queries = self._root.databases[db_config.database].schemas[db_config.schema].tables[db_config.results_table]
        return self._session.create_dataframe(
            data,
            schema=T.StructType(
                [
                    T.StructField("INPUT_TYPE", T.StringType()),
                    T.StructField("INPUT_ARGS", T.VariantType()),
                    T.StructField("RESPONSE", T.VariantType()),
                    T.StructField("CREATED_BY", T.StringType()),
                    T.StructField("CREATED_ON", T.TimestampType()),
                ]
            ),
        ).write.save_as_table(search_queries.fully_qualified_name, mode="append", column_order="name")

    def save_feedback(self, data: list) -> None:
        search_feedback = self._root.databases[db_config.database].schemas[db_config.schema].tables[db_config.target_table]
        return self._session.create_dataframe(
            data,
            schema=T.StructType(
                [
                    T.StructField("SEARCH_ID", T.IntegerType()),
                    T.StructField("USER_FEEDBACK", T.StringType()),
                    T.StructField("USER_RATING", T.IntegerType()),
                    T.StructField("CREATED_BY", T.StringType()),
                    T.StructField("CREATED_ON", T.TimestampType()),
                ]
            ),
        ).write.save_as_table(search_feedback.fully_qualified_name, mode="append", column_order="name")

    def save_evaluation_results(self, results_df: pd.DataFrame, metrics: list) -> None:
        data = []
        for _, row in results_df.iterrows():
            metrics_dict = {}
            reasons_dict = {}

            for metric in metrics:
                metric_key = metric.lower().replace(" ", "_")
                reasons_key = f"{metric_key}_reasons"

                if metric_key in row:
                    metrics_dict[metric_key] = float(row[metric_key])

                if reasons_key in row and row[reasons_key]:
                    reasons_dict[metric_key] = row[reasons_key]

            record = [
                row["query"],
                row["context"],
                row["answer"],
                metrics_dict,
                reasons_dict if reasons_dict else None,
                self._session.get_current_user(),
                datetime.now(),
            ]
            data.append(record)

        evaluation_table = self._root.databases[db_config.database].schemas[db_config.schema].tables[db_config.evaluation_results_table]

        return self._session.create_dataframe(
            data,
            schema=T.StructType(
                [
                    T.StructField("QUERY", T.StringType()),
                    T.StructField("CONTEXT", T.StringType()),
                    T.StructField("ANSWER", T.StringType()),
                    T.StructField("METRICS", T.VariantType()),
                    T.StructField("REASONS", T.VariantType()),
                    T.StructField("CREATED_BY", T.StringType()),
                    T.StructField("CREATED_ON", T.TimestampType()),
                ]
            ),
        ).write.save_as_table(evaluation_table.fully_qualified_name, mode="append", column_order="name")

    def get_evaluation_results(self) -> pd.DataFrame:
        try:
            results = self._session.table(db_config.get_table_name(db_config.evaluation_results_table)).to_pandas()
            return results
        except Exception:
            return pd.DataFrame()

    def extract_search_results(self, input_type: str, additional_select_cols: list = None) -> pd.DataFrame:
        try:
            chunk_text_expr = F.col("VALUE")["CHUNK_TEXT"].cast(T.StringType())
            scores_expr = F.col("VALUE")["@scores"]
            cosine_similarity_expr = scores_expr["cosine_similarity"].cast(T.FloatType())
            text_match_expr = scores_expr["text_match"].cast(T.FloatType())

            base_select = [
                "INPUT_QUERY",
                chunk_text_expr.alias("CHUNK_TEXT"),
                cosine_similarity_expr.alias("COSINE_SIMILARITY"),
                text_match_expr.alias("TEXT_MATCH"),
                F.lit(input_type).alias("INPUT_TYPE"),
            ]

            if additional_select_cols:
                base_select = additional_select_cols + base_select

            results = self._session.table(db_config.results_table).filter(F.upper(F.col("INPUT_TYPE")) == F.lit(input_type.upper())).with_column("INPUT_QUERY", F.col("INPUT_ARGS")["query"].cast(T.StringType())).join_table_function("flatten", F.col("RESPONSE")).select(*base_select)
            return results.to_pandas()
        except Exception:
            return pd.DataFrame()

    def get_baseline_results(self) -> pd.DataFrame:
        golden_pair_results = self.extract_search_results("GOLDEN_PAIR", ["INDEX"])
        if not golden_pair_results.empty:
            original_golden_pairs = self._session.table(db_config.golden_pairs_table).to_pandas()
            return golden_pair_results.merge(original_golden_pairs, on="INPUT_QUERY", how="left")
        return golden_pair_results

    def get_adhoc_results(self) -> pd.DataFrame:
        return self.extract_search_results("ADHOC", ["SEARCH_ID"])

    def get_feedback_counts(self) -> pd.DataFrame:
        try:
            feedback_counts = self._session.table(db_config.get_table_name(db_config.target_table)).group_by("SEARCH_ID").count().select(F.col("SEARCH_ID"), F.col("COUNT").alias("FEEDBACK_COUNT")).to_pandas()
            return feedback_counts
        except Exception:
            return pd.DataFrame(columns=["SEARCH_ID", "FEEDBACK_COUNT"])

    def get_knowledge_data(self, table_name: str) -> pd.DataFrame:
        return self._session.table(table_name).to_pandas()

    def run_search(self, query: str, input_type: str) -> tuple[dict, list]:
        cortex_search_service = self.get_cortex_search_service()
        search_args = search_config.to_dict()
        search_args.update({"query": query})
        response = cortex_search_service.search(**search_args)
        record = {
            "INPUT_QUERY": query,
            "RESPONSE": response.results,
            "INPUT_ARGS": search_args,
            "CREATED_ON": datetime.now(),
            "CREATED_BY": self._session.get_current_user(),
            "INPUT_TYPE": input_type,
        }
        return record, response.results

    def execute_playground_search(self, query: str) -> tuple[int, list]:
        record, results = self.run_search(query, "adhoc")

        save_data = [
            [
                record["INPUT_TYPE"],
                record["INPUT_ARGS"],
                record["RESPONSE"],
                record["CREATED_BY"],
                record["CREATED_ON"],
            ]
        ]
        self.save_search(save_data)

        saved_search = self._session.table(db_config.get_table_name(db_config.results_table)).filter(F.col("INPUT_TYPE") == F.lit("adhoc")).sort(F.col("CREATED_ON").desc()).limit(1).select("SEARCH_ID").collect()
        search_id = saved_search[0]["SEARCH_ID"] if saved_search else None

        return search_id, results

    def generate_llm_responses(self, results: list, query: str) -> pd.DataFrame:
        results_data = [(r["CHUNK_TEXT"], query) for r in results]
        results_df = (
            self._session.create_dataframe(results_data, schema=["chunk_text", "query"])
            .with_column(
                "agent_response",
                F.call_builtin(
                    "SNOWFLAKE.CORTEX.COMPLETE",
                    F.lit("mistral-large2"),
                    F.prompt(
                        "You are a helpful AI assistant. Use the following context to answer the user's question.\n\nContext: {0}\n\nUser Question: {1}\n\nPlease provide a helpful and accurate answer based on the context provided.",
                        F.col("chunk_text"),
                        F.col("query"),
                    ),
                ),
            )
            .to_pandas()
        )
        results_df.columns = results_df.columns.str.lower()
        return results_df

    def call_stored_procedure(self, proc_name: str) -> pd.DataFrame:
        return self._session.call(proc_name).to_pandas()
