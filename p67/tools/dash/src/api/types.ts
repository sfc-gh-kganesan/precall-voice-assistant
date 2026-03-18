export interface Workflow {
    workflowId: string;
    name: string | null;
    owner: string;
    createdAt: string;
    updatedAt: string;
    visibility: 'Private' | 'Public';
    versionCount?: number;
}

export interface WorkflowListResponse {
    workflows: Workflow[];
}

export type RunStatus = 'running' | 'completed' | 'interrupted' | 'failed';

export interface RunEntry {
    id: string;
    workflowId: string;
    status: RunStatus;
    startedAt: string;
    completedAt: string | null;
    exitCode: number | null;
    logCount: number;
}

export interface RunListResponse {
    runs: RunEntry[];
    total: number;
}

export type LogSource = 'RuntimeHost' | 'WorkflowNode' | 'ToolCall';

export interface LogEntry {
    id: string;
    runId: string;
    workflowId: string;
    source: LogSource;
    message: string;
    attributes: Record<string, unknown>;
    timestamp: string;
}

export interface LogListResponse {
    logs: LogEntry[];
    total: number;
}

export type InterruptStatus = 'Pending' | 'Resumed' | 'Expired';

export interface Interrupt {
    id: string;
    runId: string;
    workflowId: string;
    payload: unknown;
    nodeId: string | null;
    status: InterruptStatus;
    response: unknown | null;
    createdAt: string;
    resumedAt: string | null;
}

export interface InterruptListResponse {
    interrupts: Interrupt[];
    total: number;
}

export interface WorkflowRunResponse {
    exitCode: number;
    stdout: string[];
    stderr: string[];
    log: string[];
    success: boolean;
    errors: Array<{ error: string; message: string }>;
    status?: 'running' | 'completed' | 'interrupted' | 'failed';
    pendingInterrupt?: {
        interruptId: string;
        value: unknown;
        timestamp: string;
        nodeId?: string;
    };
    runId?: string;
    result?: unknown;
}

export interface ManifestParamValue {
    value?: string;
    valueRef?: string;
    secretRef?: string;
    oauthRef?: string;
    required?: boolean;
    description?: string;
}

export interface WorkflowManifestResponse {
    params?: Record<string, ManifestParamValue>;
}

export interface GraphNodeDef {
    id: string;
    type: string;
    name: string;
    description?: string;
    action_name?: string;
    subgraph_name?: string;
    question?: string;
    human_role?: string;
    human_task?: string;
    end_type?: string;
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
    }>;
}

export interface WorkflowGraphResponse {
    graph: WorkflowGraphDef | null;
}

export interface WhoamiResponse {
    id: string;
    snowflakeUser: string;
}

export interface ErrorResponse {
    error: string;
    message?: string;
}

export interface WorkflowRunAccepted {
    runId: string;
    status: 'running';
}

export interface WorkflowRunStatusResponse {
    runId: string;
    status: RunStatus;
    exitCode: number | null;
    result?: unknown;
    stdout?: string[];
    stderr?: string[];
    log?: string[];
    errors?: Array<{ error: string; message: string }>;
    pendingInterrupt?: {
        interruptId: string;
        value: unknown;
        timestamp: string;
        nodeId?: string;
    };
}
