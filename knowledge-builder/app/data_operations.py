from datetime import datetime

import pandas as pd
from config import db_config, search_config
from snowflake.core import CreateMode, Root
from snowflake.core.table import (
    ForeignKey,
    PrimaryKey,
    Table,
    TableCollection,
    TableColumn,
    TableResource,
)
from snowflake.snowpark import Session
from snowflake.snowpark import functions as F
from snowflake.snowpark import types as T


def create_table(
    table_collection: TableCollection,
    name: str,
    columns: list[TableColumn],
    mode: CreateMode = CreateMode.error_if_exists,
) -> TableResource:
    table_definition = Table(name=name, columns=columns)
    return table_collection.create(table_definition, mode=mode)


class SnowflakeDataOperations:
    def __init__(self, session: Session):
        self._session = session
        self._root = Root(session)

    def _get_table_collection(self) -> TableCollection:
        return self._root.databases[db_config.database].schemas[db_config.schema].tables

    def _ensure_tables_exist(self) -> None:
        tc = self._get_table_collection()

        create_table(
            tc,
            db_config.results_table,
            [
                TableColumn(
                    name="SEARCH_ID",
                    datatype="INT",
                    autoincrement=True,
                    constraints=[PrimaryKey()],
                ),
                TableColumn(name="INPUT_TYPE", datatype="VARCHAR"),
                TableColumn(name="INPUT_ARGS", datatype="VARIANT"),
                TableColumn(name="RESPONSE", datatype="VARIANT"),
                TableColumn(name="CREATED_BY", datatype="VARCHAR"),
                TableColumn(name="CREATED_ON", datatype="TIMESTAMP_NTZ(9)"),
            ],
            CreateMode.if_not_exists,
        )

        create_table(
            tc,
            db_config.target_table,
            [
                TableColumn(
                    name="FEEDBACK_ID",
                    datatype="INT",
                    autoincrement=True,
                    constraints=[PrimaryKey()],
                ),
                TableColumn(
                    name="SEARCH_ID",
                    datatype="INT",
                    constraints=[
                        ForeignKey(
                            referenced_table_name=db_config.results_table,
                            referenced_column_names=["SEARCH_ID"],
                        )
                    ],
                ),
                TableColumn(name="USER_FEEDBACK", datatype="VARCHAR"),
                TableColumn(name="USER_RATING", datatype="INT"),
                TableColumn(name="CREATED_BY", datatype="VARCHAR"),
                TableColumn(name="CREATED_ON", datatype="TIMESTAMP_NTZ(9)"),
            ],
            CreateMode.if_not_exists,
        )

        create_table(
            tc,
            db_config.golden_pairs_table,
            [
                TableColumn(name="INCIDENT", datatype="VARCHAR"),
                TableColumn(name="SSF_KB_GUEST", datatype="VARCHAR"),
                TableColumn(name="INPUT_QUERY", datatype="VARCHAR"),
                TableColumn(name="RESOLUTION_FROM_RESOLUTION_NOTES", datatype="VARCHAR"),
                TableColumn(name="USER_EDUCATION_POSSIBLY_DUE_TO_KB_GAP_OR_MISSING_CONTENT", datatype="VARCHAR"),
                TableColumn(name="SUGGESTED_RESOLUTION_CURATED", datatype="VARCHAR"),
                TableColumn(name="RESOLUTION_DETAILS_FOUND_UNIQUE_TO_SSF_AND_NOT_COVERED_IN_SELFHELP", datatype="VARCHAR"),
                TableColumn(name="COVERED_IN_SELFHELP", datatype="VARCHAR"),
                TableColumn(name="FOUND_IN_CONCIERGE", datatype="VARCHAR"),
                TableColumn(name="DEFLECTION", datatype="VARCHAR"),
                TableColumn(name="LUMA_COMMENTS_AND_RESOLUTION", datatype="VARCHAR"),
                TableColumn(name="CONCIERGE_RESPONSE_BETA", datatype="VARCHAR"),
                TableColumn(name="ALTERNATE_QUERIES_OR_UTTERANCES", datatype="VARCHAR"),
                TableColumn(name="FOLLOW_UP", datatype="VARCHAR"),
            ],
            CreateMode.if_not_exists,
        )

        create_table(
            tc,
            db_config.synthetic_pairs_table,
            [
                TableColumn(name="SOURCE_TABLE", datatype="VARCHAR"),
                TableColumn(name="ATTRS", datatype="VARIANT"),
                TableColumn(name="SCORING", datatype="VARIANT"),
                TableColumn(name="GENERATED", datatype="VARIANT"),
                TableColumn(name="L1_RAW", datatype="VARCHAR"),
                TableColumn(name="L2_RAW", datatype="VARCHAR"),
                TableColumn(name="L3_RAW", datatype="VARCHAR"),
                TableColumn(name="L4_RAW", datatype="VARCHAR"),
                TableColumn(name="L1_TAG", datatype="VARCHAR"),
                TableColumn(name="L2_TAG", datatype="VARCHAR"),
                TableColumn(name="L3_TAG", datatype="VARCHAR"),
                TableColumn(name="L4_TAG", datatype="VARCHAR"),
                TableColumn(name="CREATED_ON", datatype="TIMESTAMP_LTZ(9)", default="CURRENT_TIMESTAMP()"),
            ],
            CreateMode.if_not_exists,
        )

        create_table(
            tc,
            db_config.evaluation_results_table,
            [
                TableColumn(
                    name="SEARCH_ID",
                    datatype="INT",
                    constraints=[
                        ForeignKey(
                            referenced_table_name=db_config.results_table,
                            referenced_column_names=["SEARCH_ID"],
                        )
                    ],
                ),
                TableColumn(name="INPUT_QUERY", datatype="VARCHAR"),
                TableColumn(name="CHUNKS", datatype="VARCHAR"),
                TableColumn(name="EVALUATION_MODEL", datatype="VARCHAR"),
                TableColumn(name="EVALUATION", datatype="VARIANT"),
                TableColumn(name="CREATED_BY", datatype="VARCHAR"),
                TableColumn(name="CREATED_ON", datatype="TIMESTAMP_NTZ(9)", default="CURRENT_TIMESTAMP()"),
            ],
            CreateMode.if_not_exists,
        )

    def validate_environment(self) -> tuple[bool, list]:
        missing_resources = []

        try:
            self._ensure_tables_exist()

            database = self._root.databases[db_config.database]
            schema = database.schemas[db_config.schema]

            try:
                _ = schema.cortex_search_services[db_config.search_service]
            except Exception:
                missing_resources.append(f"Cortex Search Service: {db_config.get_table_name(db_config.search_service)}")

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

    def save_evaluation_results(
        self,
        search_id: int,
        input_query: str,
        chunks: str,
        evaluation_model: str,
        evaluation: dict,
    ) -> None:
        data = [
            [
                search_id,
                input_query,
                chunks,
                evaluation_model,
                evaluation,
                self._session.get_current_user(),
                datetime.now(),
            ]
        ]

        evaluation_table = self._root.databases[db_config.database].schemas[db_config.schema].tables[db_config.evaluation_results_table]

        return self._session.create_dataframe(
            data,
            schema=T.StructType(
                [
                    T.StructField("SEARCH_ID", T.IntegerType()),
                    T.StructField("INPUT_QUERY", T.StringType()),
                    T.StructField("CHUNKS", T.StringType()),
                    T.StructField("EVALUATION_MODEL", T.StringType()),
                    T.StructField("EVALUATION", T.VariantType()),
                    T.StructField("CREATED_BY", T.StringType()),
                    T.StructField("CREATED_ON", T.TimestampType()),
                ]
            ),
        ).write.save_as_table(evaluation_table.fully_qualified_name, mode="append", column_order="name")

    def get_evaluation_results(self) -> pd.DataFrame:
        try:
            # Join with SEARCH_QUERIES to get INPUT_TYPE
            results = self._session.sql(f"""
                SELECT
                    er.SEARCH_ID,
                    er.INPUT_QUERY,
                    er.CHUNKS,
                    er.EVALUATION_MODEL,
                    er.EVALUATION,
                    er.CREATED_BY,
                    er.CREATED_ON,
                    sq.INPUT_TYPE
                FROM {db_config.get_table_name(db_config.evaluation_results_table)} er
                LEFT JOIN {db_config.get_table_name(db_config.results_table)} sq
                    ON er.SEARCH_ID = sq.SEARCH_ID
            """).to_pandas()
            return results
        except Exception:
            return pd.DataFrame()

    def get_evaluation_aggregate_stats(self) -> pd.DataFrame:
        try:
            return (
                self._session.table(db_config.get_table_name(db_config.evaluation_results_table))
                .select(
                    F.count("*").alias("total_evaluations"),
                    F.avg(F.col("EVALUATION")["metrics"]["answer_relevance"].cast("float")).alias("avg_answer_relevance"),
                    F.avg(F.col("EVALUATION")["metrics"]["context_relevance"].cast("float")).alias("avg_context_relevance"),
                    F.avg(F.col("EVALUATION")["metrics"]["groundedness"].cast("float")).alias("avg_groundedness"),
                )
                .to_pandas()
            )
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
        except Exception as e:
            print(f"Error extracting search results: {e}")
            return pd.DataFrame()

    def get_baseline_results(self) -> pd.DataFrame:
        golden_pair_results = self.extract_search_results("GOLDEN_PAIR", ["SEARCH_ID"])
        if not golden_pair_results.empty:
            original_golden_pairs = self._session.table(db_config.golden_pairs_table).to_pandas()
            return golden_pair_results.merge(original_golden_pairs, on="INPUT_QUERY", how="left")
        return golden_pair_results

    def get_adhoc_results(self) -> pd.DataFrame:
        return self.extract_search_results("ADHOC", ["SEARCH_ID"])

    def extract_search_results_for_evaluation(self) -> pd.DataFrame:
        """Extract all search results from SEARCH_QUERIES for evaluation.

        Returns one row per query with SEARCH_ID, INPUT_QUERY, INPUT_TYPE,
        and CHUNK_TEXT (all chunks concatenated).
        """
        try:
            # Use SQL to flatten and aggregate chunks per query
            results = self._session.sql(f"""
                SELECT
                    SEARCH_ID,
                    INPUT_ARGS:query::STRING as INPUT_QUERY,
                    INPUT_TYPE,
                    LISTAGG(VALUE:CHUNK_TEXT::STRING, '\n\n---\n\n') WITHIN GROUP (ORDER BY INDEX) as CHUNK_TEXT
                FROM {db_config.get_table_name(db_config.results_table)},
                    LATERAL FLATTEN(input => RESPONSE)
                GROUP BY SEARCH_ID, INPUT_ARGS:query::STRING, INPUT_TYPE
            """)
            return results.to_pandas()
        except Exception as e:
            print(f"Error extracting search results for evaluation: {e}")
            return pd.DataFrame()

    def get_evaluation_completion_stats(self) -> dict:
        """Get evaluation completion statistics by input type.

        Returns a dict with counts of total and evaluated queries per input type.
        """
        try:
            # Get all search queries with their input types
            search_queries = (
                self._session.table(db_config.get_table_name(db_config.results_table))
                .group_by("INPUT_TYPE")
                .agg(F.count("*").alias("TOTAL"))
                .to_pandas()
            )

            # Get evaluated search IDs with their input types
            evaluated = self._session.sql(f"""
                SELECT sq.INPUT_TYPE, COUNT(DISTINCT er.SEARCH_ID) as EVALUATED
                FROM {db_config.get_table_name(db_config.results_table)} sq
                JOIN {db_config.get_table_name(db_config.evaluation_results_table)} er
                    ON sq.SEARCH_ID = er.SEARCH_ID
                GROUP BY sq.INPUT_TYPE
            """).to_pandas()

            # Build stats dict
            stats = {}
            for _, row in search_queries.iterrows():
                input_type = row["INPUT_TYPE"]
                total = int(row["TOTAL"])
                evaluated_count = 0
                if not evaluated.empty and input_type in evaluated["INPUT_TYPE"].values:
                    evaluated_count = int(evaluated[evaluated["INPUT_TYPE"] == input_type]["EVALUATED"].iloc[0])
                stats[input_type] = {
                    "total": total,
                    "evaluated": evaluated_count,
                    "remaining": total - evaluated_count,
                }

            return stats
        except Exception as e:
            print(f"Error getting evaluation completion stats: {e}")
            return {}

    def get_feedback_counts(self) -> pd.DataFrame:
        try:
            feedback_counts = self._session.table(db_config.get_table_name(db_config.target_table)).group_by("SEARCH_ID").count().select(F.col("SEARCH_ID"), F.col("COUNT").alias("FEEDBACK_COUNT")).to_pandas()
            return feedback_counts
        except Exception:
            return pd.DataFrame(columns=["SEARCH_ID", "FEEDBACK_COUNT"])

    def get_knowledge_data(self, table_name: str) -> pd.DataFrame:
        return self._session.table(table_name).to_pandas()

    def run_search(self, query: str, input_type: str, limit: int = None) -> tuple[dict, list]:
        cortex_search_service = self.get_cortex_search_service()
        search_args = search_config.to_dict()
        search_args.update({"query": query})
        if limit is not None:
            search_args["limit"] = limit
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

    def execute_playground_search(self, query: str, limit: int = 1) -> tuple[int, list]:
        record, results = self.run_search(query, "ADHOC", limit=limit)

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

        saved_search = self._session.table(db_config.get_table_name(db_config.results_table)).filter(F.col("INPUT_TYPE") == F.lit("ADHOC")).sort(F.col("CREATED_ON").desc()).limit(1).select("SEARCH_ID").collect()
        search_id = saved_search[0]["SEARCH_ID"] if saved_search else None

        return search_id, results

    def generate_llm_responses(self, results: list, query: str, model: str = "mistral-large2") -> pd.DataFrame:
        results_data = [(r["CHUNK_TEXT"], query) for r in results]
        results_df = (
            self._session.create_dataframe(results_data, schema=["chunk_text", "query"])
            .with_column(
                "agent_response",
                F.call_builtin(
                    "SNOWFLAKE.CORTEX.COMPLETE",
                    F.lit(model),
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

    def get_input_types(self) -> list[str]:
        try:
            types = self._session.table(db_config.get_table_name(db_config.results_table)).select(F.col("INPUT_TYPE")).distinct().sort(F.col("INPUT_TYPE")).to_pandas()
            return types["INPUT_TYPE"].tolist()
        except Exception:
            return []

    def get_feedback_for_query(self, query_id: int) -> pd.DataFrame:
        try:
            return self._session.table(db_config.get_table_name(db_config.target_table)).filter(F.col("SEARCH_ID") == F.lit(int(query_id))).select("USER_FEEDBACK", "USER_RATING", "CREATED_BY", "CREATED_ON").sort(F.col("CREATED_ON").desc()).to_pandas()
        except Exception:
            return pd.DataFrame(columns=["USER_FEEDBACK", "USER_RATING", "CREATED_BY", "CREATED_ON"])

    def get_synthetic_query_count(self) -> int:
        try:
            count = self._session.table(db_config.get_table_name(db_config.synthetic_pairs_table)).count()
            return count
        except Exception:
            return 0

    def get_taxonomy_evaluation_rollup(self) -> pd.DataFrame:
        """Get evaluation metrics rolled up by taxonomy levels (L1-L4)."""
        try:
            sql = f"""
            WITH base AS (
                SELECT
                    sp.L1_TAG, sp.L2_TAG, sp.L3_TAG, sp.L4_TAG,
                    sp.GENERATED:query::STRING as QUERY,
                    sq.SEARCH_ID,
                    er.EVALUATION:metrics:answer_relevance::FLOAT as ANSWER_RELEVANCE,
                    er.EVALUATION:metrics:context_relevance::FLOAT as CONTEXT_RELEVANCE,
                    er.EVALUATION:metrics:comprehensiveness::FLOAT as COMPREHENSIVENESS,
                    er.EVALUATION:metrics:harmfulness::FLOAT as HARMFULNESS
                FROM {db_config.get_table_name(db_config.synthetic_pairs_table)} sp
                LEFT JOIN {db_config.get_table_name(db_config.results_table)} sq
                    ON sp.GENERATED:query::STRING = sq.INPUT_ARGS:query::STRING
                    AND UPPER(sq.INPUT_TYPE) = 'SYNTHETIC_PAIR'
                LEFT JOIN {db_config.get_table_name(db_config.evaluation_results_table)} er
                    ON sq.SEARCH_ID = er.SEARCH_ID
            )
            SELECT
                L1_TAG, L2_TAG, L3_TAG, L4_TAG,
                COUNT(*) as QUERY_COUNT,
                COUNT(ANSWER_RELEVANCE) as EVALUATED_COUNT,
                AVG(ANSWER_RELEVANCE) as AVG_ANSWER_RELEVANCE,
                AVG(CONTEXT_RELEVANCE) as AVG_CONTEXT_RELEVANCE,
                AVG(COMPREHENSIVENESS) as AVG_COMPREHENSIVENESS,
                AVG(HARMFULNESS) as AVG_HARMFULNESS
            FROM base
            GROUP BY L1_TAG, L2_TAG, L3_TAG, L4_TAG
            ORDER BY L1_TAG, L2_TAG, L3_TAG, L4_TAG
            """
            return self._session.sql(sql).to_pandas()
        except Exception as e:
            print(f"Error getting taxonomy rollup: {e}")
            return pd.DataFrame()

    def get_taxonomy_summary_by_level(self, level: str = "L1_TAG") -> pd.DataFrame:
        """Get evaluation metrics summarized at a specific taxonomy level."""
        try:
            sql = f"""
            WITH base AS (
                SELECT
                    sp.L1_TAG, sp.L2_TAG, sp.L3_TAG, sp.L4_TAG,
                    sp.GENERATED:query::STRING as QUERY,
                    sq.SEARCH_ID,
                    er.EVALUATION:metrics:answer_relevance::FLOAT as ANSWER_RELEVANCE,
                    er.EVALUATION:metrics:context_relevance::FLOAT as CONTEXT_RELEVANCE,
                    er.EVALUATION:metrics:comprehensiveness::FLOAT as COMPREHENSIVENESS,
                    er.EVALUATION:metrics:harmfulness::FLOAT as HARMFULNESS
                FROM {db_config.get_table_name(db_config.synthetic_pairs_table)} sp
                LEFT JOIN {db_config.get_table_name(db_config.results_table)} sq
                    ON sp.GENERATED:query::STRING = sq.INPUT_ARGS:query::STRING
                    AND UPPER(sq.INPUT_TYPE) = 'SYNTHETIC_PAIR'
                LEFT JOIN {db_config.get_table_name(db_config.evaluation_results_table)} er
                    ON sq.SEARCH_ID = er.SEARCH_ID
            )
            SELECT
                {level} as TAXONOMY_LEVEL,
                COUNT(*) as QUERY_COUNT,
                COUNT(ANSWER_RELEVANCE) as EVALUATED_COUNT,
                AVG(ANSWER_RELEVANCE) as AVG_ANSWER_RELEVANCE,
                AVG(CONTEXT_RELEVANCE) as AVG_CONTEXT_RELEVANCE,
                AVG(COMPREHENSIVENESS) as AVG_COMPREHENSIVENESS,
                AVG(HARMFULNESS) as AVG_HARMFULNESS
            FROM base
            GROUP BY {level}
            ORDER BY {level}
            """
            return self._session.sql(sql).to_pandas()
        except Exception as e:
            print(f"Error getting taxonomy summary: {e}")
            return pd.DataFrame()

    def get_taxonomy_summary_by_levels(self, levels: list[str]) -> pd.DataFrame:
        """Get evaluation metrics summarized by multiple taxonomy levels (hierarchical grouping)."""
        if not levels:
            levels = ["L1_TAG"]

        try:
            level_cols = ", ".join(levels)
            sql = f"""
            WITH base AS (
                SELECT
                    sp.L1_TAG, sp.L2_TAG, sp.L3_TAG, sp.L4_TAG,
                    sp.GENERATED:query::STRING as QUERY,
                    sq.SEARCH_ID,
                    er.EVALUATION:metrics:answer_relevance::FLOAT as ANSWER_RELEVANCE,
                    er.EVALUATION:metrics:context_relevance::FLOAT as CONTEXT_RELEVANCE,
                    er.EVALUATION:metrics:comprehensiveness::FLOAT as COMPREHENSIVENESS,
                    er.EVALUATION:metrics:harmfulness::FLOAT as HARMFULNESS
                FROM {db_config.get_table_name(db_config.synthetic_pairs_table)} sp
                LEFT JOIN {db_config.get_table_name(db_config.results_table)} sq
                    ON sp.GENERATED:query::STRING = sq.INPUT_ARGS:query::STRING
                    AND UPPER(sq.INPUT_TYPE) = 'SYNTHETIC_PAIR'
                LEFT JOIN {db_config.get_table_name(db_config.evaluation_results_table)} er
                    ON sq.SEARCH_ID = er.SEARCH_ID
            )
            SELECT
                {level_cols},
                COUNT(*) as QUERY_COUNT,
                COUNT(CONTEXT_RELEVANCE) as EVALUATED_COUNT,
                AVG(ANSWER_RELEVANCE) as AVG_ANSWER_RELEVANCE,
                AVG(CONTEXT_RELEVANCE) as AVG_CONTEXT_RELEVANCE,
                AVG(COMPREHENSIVENESS) as AVG_COMPREHENSIVENESS,
                AVG(HARMFULNESS) as AVG_HARMFULNESS
            FROM base
            GROUP BY {level_cols}
            ORDER BY {level_cols}
            """
            return self._session.sql(sql).to_pandas()
        except Exception as e:
            print(f"Error getting taxonomy summary by levels: {e}")
            return pd.DataFrame()
