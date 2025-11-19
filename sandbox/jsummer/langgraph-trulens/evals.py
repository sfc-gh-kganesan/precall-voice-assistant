import uuid
import time

from langchain_core.messages import HumanMessage

import pandas as pd

from trulens.connectors.snowflake import SnowflakeConnector
from trulens.core.otel.instrument import instrument
from trulens.otel.semconv.trace import SpanAttributes
from trulens.apps.langgraph import TruGraph
from trulens.core.run import Run, RunConfig

from utils import get_snowpark_session
from metrics import METRICS

# TruLens Snowflake Connector requires a Snowpark session
# You can pass some credentials directly to it but it must be explicitly `['account', 'user', 'password', 'database', 'schema', 'warehouse', 'role']`
tru_snowflake_connector = SnowflakeConnector(snowpark_session=get_snowpark_session()) # Can also pass credentials directly to this object

app_name = "langgraph-trulens-example2"
app_version = "0.1.0"

from graph import create_graph

graph = create_graph()

# Temporary wrapper handle run config interface with langgraph.
# On TruLens enhancement list to remove need for this wrapper.
class LanggraphWorkflow:
    """Custom app wrapper for the langgraph graph."""

    def __init__(self, graph):
        self.graph = graph

    @instrument(
        span_type=SpanAttributes.SpanType.RECORD_ROOT,
        attributes=lambda ret, exception, *args, **kwargs: {
            SpanAttributes.INPUT_ID: kwargs.get('id', str(uuid.uuid4())), # Will be mapped to Input ID in Snowflake Eval
            SpanAttributes.RECORD_ROOT.INPUT: f"message={kwargs.get('message', '')}",
            SpanAttributes.RECORD_ROOT.OUTPUT: str(ret) if ret is not None else "",
            SpanAttributes.RECORD_ROOT.GROUND_TRUTH_OUTPUT: kwargs.get('reference_output', ''),
        }
    )
    def run_query(self, message: str, id: str = str(uuid.uuid4()), reference_output: str = "") -> str:
        """Main method that TruLens will call for each query from the dataframe."""
        print(f"DEBUG: Processing message={message}, id={id}")
        
        # Call the graph directly with proper RECORD_ROOT instrumentation
        state = {
            "messages": [HumanMessage(content=message)],
        }
        
        result = self.graph.invoke(state)
        # Extract the AIMessage content from the result
        if "messages" in result and len(result["messages"]) > 0:
            return result["messages"][-1].content
        else:
            return "No response from model"

langgraph_workflow = TruGraph(
        LanggraphWorkflow(graph),
        app_name=app_name,
        app_version=app_version,
        connector=tru_snowflake_connector,
        main_method_name="run_query",
    )

if __name__ == "__main__":

    run_name = str(uuid.uuid4())

    data = {
        "ID": [str(0), str(1), str(2)],
        "MESSAGE": ["What is 15 multiplied by 4?", "Who invented the light bulb?", "What month is my birthday?"],
        "REFERENCE_OUTPUT": ["15 * 4 = 60", "Thomas Edison invented the light bulb", "March"],
    }

    df = pd.DataFrame(data)

    run_config = RunConfig(
        run_name=run_name,
        dataset_name="trulens-dataframe-input",
        description="TruLens evaluation of langgraph workflow",
        label="v1.0.0",
        source_type="DATAFRAME",
        dataset_spec={
            "message": "MESSAGE",
            "id": "ID",
            "reference_output": "REFERENCE_OUTPUT",
        },
        llm_judge_name="llama3.1-70b", 
    )

    run: Run = langgraph_workflow.add_run(run_config=run_config)

    run.start(input_df = df)

    while run.get_status() != "INVOCATION_COMPLETED":
        time.sleep(3)

    # "correctness" is a built-in, server-side metric in TruLens that incorporates ground truth from span attributes.
    run.compute_metrics(metrics=METRICS + ["correctness"])

    # Temporary polling logic to wait for metrics computation to complete.
    # Reported to TruLens teams to make this smoother.
    print("DEBUG: Waiting for metrics computation to complete...")
    poll_interval = 5
    while True:
        metrics_meta = run.describe().get("run_metadata", {}).get("metrics") or {}
        statuses = [
            (entry or {}).get("completion_status", {}).get("status")
            for entry in metrics_meta.values()
        ]
        if statuses and all(status and status != "STARTED" for status in statuses):
            break
        time.sleep(poll_interval)

    print(f"DEBUG: Final run status: {run.get_status()}")

    # Calculate client-side metric aggregate scores
    run_name = langgraph_workflow.get_run(run_name=run_name)
    records = run_name.get_records()
    client_side_metric_scores = {}
    for m in METRICS:
        if m.metric_name in records.columns:
            client_side_metric_scores[m.metric_name] = round(float(records[m.metric_name].mean()), 2)
    print('CLIENT-SIDE METRIC SCORES:')
    print(client_side_metric_scores)
