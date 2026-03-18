import type { Edge, Node } from '@xyflow/react';

export type WorkflowNodeType =
    | 'start_node'
    | 'action_node'
    | 'decision_node'
    | 'subgraph_node'
    | 'query_node'
    | 'human_node'
    | 'end_node';

export type ExecutionState =
    | 'idle'
    | 'running'
    | 'completed'
    | 'failed'
    | 'waiting';

export interface GraphNodeDef {
    id: string;
    type: WorkflowNodeType;
    name: string;
    description?: string;
    action_name?: string;
    subgraph_name?: string;
    question?: string;
    human_role?: string;
    human_task?: string;
    end_type?: 'success' | 'failure' | 'cancelled';
    branches?: Array<{ label: string; condition: string }>;
}

export interface GraphEdgeDef {
    id: string;
    from_node: string;
    to_node: string;
    label?: string;
}

export interface WorkflowGraphDef {
    name?: string;
    description?: string;
    nodes: GraphNodeDef[];
    edges: GraphEdgeDef[];
    variables?: Array<{
        name: string;
        data_type: string;
        description: string;
        default?: unknown;
    }>;
}

export interface WorkflowGraphResponse {
    graph: WorkflowGraphDef | null;
}

export interface WorkflowNodeData {
    label: string;
    nodeType: WorkflowNodeType;
    description?: string;
    executionState: ExecutionState;
    endType?: 'success' | 'failure' | 'cancelled';
    humanTask?: string;
    actionName?: string;
    question?: string;
    subgraphName?: string;
    [key: string]: unknown;
}

export type WorkflowFlowNode = Node<WorkflowNodeData>;
export type WorkflowFlowEdge = Edge;
