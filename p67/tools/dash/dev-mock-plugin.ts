import type { Plugin, ViteDevServer } from 'vite';

const MOCK_WORKFLOWS = {
    workflows: [
        {
            workflowId: 'with_interrupt',
            name: 'with_interrupt',
            owner: 'dev-user',
            createdAt: '2025-12-01T00:00:00Z',
            updatedAt: '2025-12-15T00:00:00Z',
            visibility: 'Public' as const,
            versionCount: 1,
        },
        {
            workflowId: 'number_one',
            name: 'number_one',
            owner: 'dev-user',
            createdAt: '2025-11-01T00:00:00Z',
            updatedAt: '2025-11-20T00:00:00Z',
            visibility: 'Public' as const,
            versionCount: 1,
        },
        {
            workflowId: 'decision_demo',
            name: 'decision_demo',
            owner: 'dev-user',
            createdAt: '2025-10-01T00:00:00Z',
            updatedAt: '2025-10-10T00:00:00Z',
            visibility: 'Private' as const,
            versionCount: 2,
        },
        {
            workflowId: 'no_graph',
            name: 'no_graph',
            owner: 'dev-user',
            createdAt: '2025-09-01T00:00:00Z',
            updatedAt: '2025-09-05T00:00:00Z',
            visibility: 'Public' as const,
            versionCount: 1,
        },
        {
            workflowId: 'auto_extracted',
            name: 'auto_extracted',
            owner: 'dev-user',
            createdAt: '2025-08-01T00:00:00Z',
            updatedAt: '2025-08-15T00:00:00Z',
            visibility: 'Public' as const,
            versionCount: 1,
        },
    ],
};

const MOCK_GRAPHS: Record<string, { graph: unknown }> = {
    with_interrupt: {
        graph: {
            name: 'Interrupt Workflow',
            description:
                'A workflow that requests human approval before completing',
            nodes: [
                { id: 'start', type: 'start_node', name: 'Start' },
                {
                    id: 'initial_work',
                    type: 'action_node',
                    name: 'Initial Work',
                    description: 'Prepare deployment items',
                    action_name: 'prepareDeployment',
                },
                {
                    id: 'approval_node',
                    type: 'human_node',
                    name: 'Request Approval',
                    description: 'Wait for human to approve deployment',
                    human_role: 'Approver',
                    human_task: 'Review and approve deployment to production',
                },
                {
                    id: 'complete_work',
                    type: 'action_node',
                    name: 'Complete Work',
                    description: 'Finalize deployment with approval response',
                    action_name: 'finalizeDeployment',
                },
                {
                    id: 'end_success',
                    type: 'end_node',
                    name: 'Done',
                    end_type: 'success',
                },
            ],
            edges: [
                { id: 'e1', from_node: 'start', to_node: 'initial_work' },
                {
                    id: 'e2',
                    from_node: 'initial_work',
                    to_node: 'approval_node',
                },
                {
                    id: 'e3',
                    from_node: 'approval_node',
                    to_node: 'complete_work',
                    label: 'Approved',
                },
                {
                    id: 'e4',
                    from_node: 'complete_work',
                    to_node: 'end_success',
                },
            ],
        },
    },
    number_one: {
        graph: {
            name: 'LangGraph Pipeline',
            description: 'A simple 3-node LangGraph workflow',
            nodes: [
                { id: 'start', type: 'start_node', name: 'Start' },
                {
                    id: 'node1',
                    type: 'action_node',
                    name: 'Initialize',
                    description: 'Initialize state and messages',
                    action_name: 'nodeOne',
                },
                {
                    id: 'node2',
                    type: 'action_node',
                    name: 'Process',
                    description: 'Process data',
                    action_name: 'nodeTwo',
                },
                {
                    id: 'node3',
                    type: 'action_node',
                    name: 'Finalize',
                    description: 'Finalize results',
                    action_name: 'nodeThree',
                },
                {
                    id: 'end',
                    type: 'end_node',
                    name: 'End',
                    end_type: 'success',
                },
            ],
            edges: [
                { id: 'e1', from_node: 'start', to_node: 'node1' },
                { id: 'e2', from_node: 'node1', to_node: 'node2' },
                { id: 'e3', from_node: 'node2', to_node: 'node3' },
                { id: 'e4', from_node: 'node3', to_node: 'end' },
            ],
        },
    },
    decision_demo: {
        graph: {
            name: 'Decision Demo',
            description: 'A workflow with branching decisions and a query node',
            nodes: [
                { id: 'start', type: 'start_node', name: 'Start' },
                {
                    id: 'fetch_data',
                    type: 'query_node',
                    name: 'Fetch Data',
                    description: 'Query customer database',
                    question: 'SELECT * FROM customers WHERE active = true',
                },
                {
                    id: 'check_tier',
                    type: 'decision_node',
                    name: 'Check Tier',
                    description: 'Route based on customer tier',
                    branches: [
                        { label: 'Premium', condition: 'tier == "premium"' },
                        { label: 'Standard', condition: 'tier == "standard"' },
                    ],
                },
                {
                    id: 'premium_flow',
                    type: 'subgraph_node',
                    name: 'Premium Processing',
                    description: 'Run premium customer sub-workflow',
                    subgraph_name: 'premium_handler',
                },
                {
                    id: 'standard_flow',
                    type: 'action_node',
                    name: 'Standard Processing',
                    description: 'Handle standard tier',
                    action_name: 'processStandard',
                },
                {
                    id: 'end_ok',
                    type: 'end_node',
                    name: 'Complete',
                    end_type: 'success',
                },
                {
                    id: 'end_fail',
                    type: 'end_node',
                    name: 'Failed',
                    end_type: 'failure',
                },
            ],
            edges: [
                { id: 'e1', from_node: 'start', to_node: 'fetch_data' },
                { id: 'e2', from_node: 'fetch_data', to_node: 'check_tier' },
                {
                    id: 'e3',
                    from_node: 'check_tier',
                    to_node: 'premium_flow',
                    label: 'Premium',
                },
                {
                    id: 'e4',
                    from_node: 'check_tier',
                    to_node: 'standard_flow',
                    label: 'Standard',
                },
                { id: 'e5', from_node: 'premium_flow', to_node: 'end_ok' },
                { id: 'e6', from_node: 'standard_flow', to_node: 'end_ok' },
                {
                    id: 'e7',
                    from_node: 'check_tier',
                    to_node: 'end_fail',
                    label: 'Unknown',
                },
            ],
        },
    },
    no_graph: {
        graph: null,
    },
    auto_extracted: {
        graph: {
            name: 'Workflow',
            description: 'Auto-extracted from LangGraph',
            nodes: [
                { id: 'start', type: 'start_node', name: 'Start' },
                { id: 'retrieve', type: 'action_node', name: 'Retrieve' },
                {
                    id: 'grade_documents',
                    type: 'action_node',
                    name: 'Grade Documents',
                },
                { id: 'generate', type: 'action_node', name: 'Generate' },
                { id: 'end', type: 'end_node', name: 'End' },
            ],
            edges: [
                { id: 'e1', from_node: 'start', to_node: 'retrieve' },
                { id: 'e2', from_node: 'retrieve', to_node: 'grade_documents' },
                { id: 'e3', from_node: 'grade_documents', to_node: 'generate' },
                { id: 'e4', from_node: 'generate', to_node: 'end' },
            ],
        },
    },
};

const MOCK_RUNS: Record<string, { runs: unknown[]; total: number }> = {
    with_interrupt: {
        runs: [
            {
                id: 'run-001',
                workflowId: 'with_interrupt',
                status: 'interrupted',
                startedAt: '2025-12-15T10:00:00Z',
                completedAt: null,
                exitCode: null,
                logCount: 5,
            },
            {
                id: 'run-002',
                workflowId: 'with_interrupt',
                status: 'completed',
                startedAt: '2025-12-14T09:00:00Z',
                completedAt: '2025-12-14T09:01:30Z',
                exitCode: 0,
                logCount: 8,
            },
        ],
        total: 2,
    },
    number_one: {
        runs: [
            {
                id: 'run-003',
                workflowId: 'number_one',
                status: 'completed',
                startedAt: '2025-11-20T14:00:00Z',
                completedAt: '2025-11-20T14:00:45Z',
                exitCode: 0,
                logCount: 12,
            },
        ],
        total: 1,
    },
    decision_demo: {
        runs: [
            {
                id: 'run-004',
                workflowId: 'decision_demo',
                status: 'running',
                startedAt: '2025-10-10T08:00:00Z',
                completedAt: null,
                exitCode: null,
                logCount: 3,
            },
        ],
        total: 1,
    },
    no_graph: {
        runs: [
            {
                id: 'run-005',
                workflowId: 'no_graph',
                status: 'completed',
                startedAt: '2025-09-05T12:00:00Z',
                completedAt: '2025-09-05T12:01:00Z',
                exitCode: 0,
                logCount: 4,
            },
        ],
        total: 1,
    },
    auto_extracted: {
        runs: [
            {
                id: 'run-006',
                workflowId: 'auto_extracted',
                status: 'completed',
                startedAt: '2025-08-15T09:00:00Z',
                completedAt: '2025-08-15T09:00:30Z',
                exitCode: 0,
                logCount: 6,
            },
        ],
        total: 1,
    },
};

const MOCK_LOGS: Record<string, { logs: unknown[]; total: number }> = {
    'run-001': {
        logs: [
            {
                id: 'log-1',
                runId: 'run-001',
                workflowId: 'with_interrupt',
                source: 'RuntimeHost',
                message: 'Starting workflow execution',
                attributes: { nodeId: 'start' },
                timestamp: '2025-12-15T10:00:00Z',
            },
            {
                id: 'log-2',
                runId: 'run-001',
                workflowId: 'with_interrupt',
                source: 'WorkflowNode',
                message: 'Preparing deployment items...',
                attributes: { nodeId: 'initial_work' },
                timestamp: '2025-12-15T10:00:01Z',
            },
            {
                id: 'log-3',
                runId: 'run-001',
                workflowId: 'with_interrupt',
                source: 'WorkflowNode',
                message: 'Deployment package ready',
                attributes: { nodeId: 'initial_work' },
                timestamp: '2025-12-15T10:00:02Z',
            },
            {
                id: 'log-4',
                runId: 'run-001',
                workflowId: 'with_interrupt',
                source: 'RuntimeHost',
                message: 'Interrupt requested: awaiting human approval',
                attributes: { nodeId: 'approval_node' },
                timestamp: '2025-12-15T10:00:03Z',
            },
        ],
        total: 4,
    },
    'run-004': {
        logs: [
            {
                id: 'log-10',
                runId: 'run-004',
                workflowId: 'decision_demo',
                source: 'RuntimeHost',
                message: 'Starting workflow',
                attributes: { nodeId: 'start' },
                timestamp: '2025-10-10T08:00:00Z',
            },
            {
                id: 'log-11',
                runId: 'run-004',
                workflowId: 'decision_demo',
                source: 'WorkflowNode',
                message: 'Querying customer database...',
                attributes: { nodeId: 'fetch_data' },
                timestamp: '2025-10-10T08:00:01Z',
            },
            {
                id: 'log-12',
                runId: 'run-004',
                workflowId: 'decision_demo',
                source: 'WorkflowNode',
                message: 'Evaluating tier condition',
                attributes: { nodeId: 'check_tier' },
                timestamp: '2025-10-10T08:00:02Z',
            },
        ],
        total: 3,
    },
};

const MOCK_INTERRUPTS = {
    interrupts: [
        {
            id: 'int-001',
            runId: 'run-001',
            workflowId: 'with_interrupt',
            payload: {
                message: 'Please review deployment to production',
                deploymentId: 'deploy-42',
            },
            nodeId: 'approval_node',
            status: 'Pending',
            response: null,
            createdAt: '2025-12-15T10:00:03Z',
            resumedAt: null,
        },
    ],
    total: 1,
};

const MOCK_RUN_STATUS: Record<string, unknown> = {
    'run-001': {
        runId: 'run-001',
        status: 'interrupted',
        exitCode: null,
        pendingInterrupt: {
            interruptId: 'int-001',
            value: { message: 'Please review deployment to production' },
            timestamp: '2025-12-15T10:00:03Z',
            nodeId: 'approval_node',
        },
    },
    'run-004': {
        runId: 'run-004',
        status: 'running',
        exitCode: null,
    },
};

function json(res: import('http').ServerResponse, data: unknown, status = 200) {
    res.writeHead(status, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(data));
}

export function devMockApi(): Plugin {
    return {
        name: 'dev-mock-api',
        configureServer(server: ViteDevServer) {
            server.middlewares.use((req, res, next) => {
                const url = req.url ?? '';
                if (!url.startsWith('/api/')) return next();

                if (url === '/api/whoami') {
                    return json(res, {
                        id: 'dev-user',
                        snowflakeUser: 'DEV_LOCAL',
                    });
                }

                if (url === '/api/workflow/list') {
                    return json(res, MOCK_WORKFLOWS);
                }

                const graphMatch = url.match(
                    /^\/api\/workflow\/([^/]+)\/graph$/,
                );
                if (graphMatch) {
                    const wfId = graphMatch[1];
                    return json(res, MOCK_GRAPHS[wfId] ?? { graph: null });
                }

                const manifestMatch = url.match(
                    /^\/api\/workflow\/([^/]+)\/manifest$/,
                );
                if (manifestMatch) {
                    return json(res, { params: {} });
                }

                const runStatusMatch = url.match(
                    /^\/api\/workflow\/runs\/([^?]+)/,
                );
                if (runStatusMatch) {
                    const runId = runStatusMatch[1];
                    return json(
                        res,
                        MOCK_RUN_STATUS[runId] ?? {
                            runId,
                            status: 'completed',
                            exitCode: 0,
                        },
                    );
                }

                if (url.startsWith('/api/log/runs')) {
                    const params = new URL(url, 'http://localhost')
                        .searchParams;
                    const wfId = params.get('workflowId') ?? '';
                    return json(res, MOCK_RUNS[wfId] ?? { runs: [], total: 0 });
                }

                if (url.startsWith('/api/log/list')) {
                    const params = new URL(url, 'http://localhost')
                        .searchParams;
                    const runId = params.get('runId') ?? '';
                    return json(
                        res,
                        MOCK_LOGS[runId] ?? { logs: [], total: 0 },
                    );
                }

                if (url.startsWith('/api/workflow/interrupts')) {
                    if (url.includes('/resume')) {
                        return json(res, {
                            success: true,
                            interruptId: 'int-001',
                            resumedAt: new Date().toISOString(),
                        });
                    }
                    const intMatch = url.match(
                        /^\/api\/workflow\/interrupts\/([^/?]+)$/,
                    );
                    if (intMatch) {
                        const found = MOCK_INTERRUPTS.interrupts.find(
                            (i) => i.id === intMatch[1],
                        );
                        return found
                            ? json(res, found)
                            : json(res, { error: 'Not found' }, 404);
                    }
                    return json(res, MOCK_INTERRUPTS);
                }

                json(res, { error: 'Mock endpoint not found' }, 404);
            });
        },
    };
}
