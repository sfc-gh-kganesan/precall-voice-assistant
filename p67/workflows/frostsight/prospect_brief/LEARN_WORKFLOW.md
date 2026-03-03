
# Workflow Structure

A workflow is a directed graph with the following components:

1. Nodes: represents the execution of a step, with 7 types of nodes (action_node, query_node, decision_node, subgraph_node, human_node, start_node, end_node):

- Action_node has exactly one incoming edge and exactly one outgoing edge.  Action_node calls a function `action_[action_name]([parameters])`.  Action_node is meant for updating the real world by taking some actions.

- Query_node has exactly one incoming edge and exactly one outgoing edge.  Query_node calls a function `query([question])`. Query_node is meant for asking questions on semantic view to bring real world information into workflow variables.  Semantic view is a query engine that has access to the underlying database objects and can answer questions.

- Decision_node has exactly one incoming edge and multiple outgoing edges.  Decision_node evaluates conditions based on workflow variables and activates one of its outgoing edges based on which branch condition is met.

  **DECISION NODE STRUCTURE**:
  - No `condition` or `condition_type` fields at the node level
  - Each branch has:
    - `label`: A descriptive name for the branch (e.g., "valid", "invalid", "approved", "rejected")
    - `condition`: A text description of when this branch should be taken (NOT a formal boolean expression)

  **CRITICAL: Two approaches for decision logic**:

  **Option 1: Direct condition evaluation (PREFERRED when simple)**
  Use this when the decision can be expressed by comparing existing workflow variables.

  Example:
  ```json
  {
    "id": "check_legitimacy",
    "type": "decision_node",
    "name": "Check Invoice Legitimacy",
    "description": "Validate invoice against purchase order",
    "branches": [
      {
        "label": "valid",
        "condition": "PO exists, vendor names match, amounts match, and due date has been reached"
      },
      {
        "label": "invalid",
        "condition": "Any of the above checks fail"
      }
    ]
  }
  ```
  The condition description references variables like `po_exists`, `po_vendor`, `invoice_vendor`, `po_amount`, `invoice_amount`, `due_date` that were populated by previous query_node or action_node.

  **Option 2: Query-based decision (for complex logic requiring data access)**
  When the decision logic is complex and requires accessing external data or performing calculations that need a semantic view, use a query_node before the decision_node.

  Example:
  ```json
  {
    "id": "evaluate_credit_risk",
    "type": "query_node",
    "name": "Evaluate Credit Risk",
    "description": "Query credit scoring semantic view to determine risk level",
    "question": "What is the credit risk level for customer {customer_id} based on payment history?"
  }
  ```
  This query_node populates a `risk_level` variable, which is then used by a subsequent decision_node:
  ```json
  {
    "id": "route_by_risk",
    "type": "decision_node",
    "name": "Route by Risk Level",
    "branches": [
      {"label": "low_risk", "condition": "Credit risk level is low"},
      {"label": "high_risk", "condition": "Credit risk level is high"}
    ]
  }
  ```

  **CRITICAL REQUIREMENTS**:
  1. **Variable Dependency**: Every variable referenced in branch conditions MUST be populated by a previous node (query_node, action_node, or human_node)
  2. **Prefer Option 1**: If the decision can be expressed using existing workflow variables, ALWAYS use Option 1 (direct condition)
  3. **Use Query for Complex Logic**: If the decision requires external data access or complex calculations, use Option 2 (query_node)
  4. **Never use action_node for decisions**: Decision logic is read-only and should NOT change external state. Use query_node instead.
  5. **Traceable Data Flow**: For each variable referenced in conditions, trace back to identify which node sets it
  6. **Text Descriptions**: Branch conditions are descriptive text, not formal boolean expressions

- Subgraph_node has exactly one incoming edge and exactly one outgoing edge.  Subgraph_node calls a function `subgraph([workflow_name])` to execute another workflow graph.

- Human_node has exactly one incoming edge and exactly one outgoing edge.  Human_node calls a function `human([role], [task_description])` to assign a task to a human role.

- Start_node is the entry of the workflow graph and is the starting point of execution, it has no incoming edges and has exactly one outgoing edge.  Start_node activates the node connected in its outgoing edge.

- End_node is the exit of the workflow graph, it has multiple incoming edges and has no outgoing edges.  When an end_node is reached, the graph execution is halted and the workflow variables will be returned.

2. Edges: Connections between nodes (from_node -> to_node, optional label/condition if the from_node is a decision_node)

3. Variables: Dictionary of name value pairs
- Variables define the current state of the workflow execution.
- Each variable has a name, data_type (e.g. number, string, array of numbers, array of strings), description (describe its meaning)
- When a node is activated, there is an input_mapping function to populate the input parameters of the associated function based on some workflow variables before calling the function.  When the function returns, there is an output_mapping function to update some workflow variables based on its return value.

The workflow execution starts by an API call that pass in an input workflow variables.  The start_node of working graph will be first activated, and trigger a chain of node executions.  Each of the node will read  workflow parameters into its function's parameters, execute the function, and update the workflow variables.  These variables will be evaluated at the decision_node to determine the route of the subsequent node execution.  When the end_node is reached, the workflow execution will stop and its current workflow variables will be returned.

