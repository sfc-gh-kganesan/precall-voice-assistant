#!/usr/bin/env npx tsx
/**
 * Seed script to populate test data for local p67 development.
 *
 * Creates workflows with real files on disk (under DATA_ROOT), plus
 * runs, logs, and interrupts in the database so the dash UI can be
 * tested end-to-end including the graph visualisation.
 *
 * Usage:
 *   npx tsx scripts/seed-test-data.ts          # seed (additive)
 *   npx tsx scripts/seed-test-data.ts --reset   # wipe seed data first
 */

import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { createPrismaClient } from '../../../packages/db/src/client.js';

const DATA_ROOT = process.env.DATA_ROOT || '/tmp/p67_controld_data';

const prisma = createPrismaClient(
    process.env.DATABASE_URL ||
        'postgresql://postgres:password@localhost:5432/controld_dev?schema=public',
);

// ---------------------------------------------------------------------------
// Workflow fixture definitions
// ---------------------------------------------------------------------------

type WorkflowFixture = {
    dirName: string;
    name: string;
    visibility: 'Public' | 'Private';
    manifest: string | null;
    graphJson: string | null;
    entryFile: { name: string; content: string };
    description: string;
};

const FIXTURES: WorkflowFixture[] = [
    {
        dirName: 'wf-seed-manual-graph',
        name: 'manual-graph-demo',
        visibility: 'Public',
        description: 'Graph from graph.json (ETL pipeline demo)',
        entryFile: {
            name: 'index.js',
            content: `export async function main(sdk) {
    console.log('Starting data pipeline');
    return { status: 'ok', records: 42 };
}
`,
        },
        manifest: `name: manual-graph-demo
visibility: public
config: []
`,
        graphJson: JSON.stringify(
            {
                name: 'Data Pipeline',
                description: 'A 4-node ETL pipeline',
                nodes: [
                    { id: 'start', type: 'start_node', name: 'Start' },
                    {
                        id: 'extract',
                        type: 'action_node',
                        name: 'Extract Data',
                        description: 'Pull records from source system',
                        action_name: 'extractData',
                    },
                    {
                        id: 'transform',
                        type: 'action_node',
                        name: 'Transform',
                        description: 'Clean and reshape data',
                        action_name: 'transformRecords',
                    },
                    {
                        id: 'load',
                        type: 'action_node',
                        name: 'Load',
                        description: 'Write to destination table',
                        action_name: 'loadToTable',
                    },
                    {
                        id: 'end',
                        type: 'end_node',
                        name: 'Done',
                        end_type: 'success',
                    },
                ],
                edges: [
                    { id: 'e1', from_node: 'start', to_node: 'extract' },
                    { id: 'e2', from_node: 'extract', to_node: 'transform' },
                    { id: 'e3', from_node: 'transform', to_node: 'load' },
                    { id: 'e4', from_node: 'load', to_node: 'end' },
                ],
            },
            null,
            2,
        ),
    },
    {
        dirName: 'wf-seed-auto-graph',
        name: 'auto-graph-demo',
        visibility: 'Public',
        description:
            'Manifest has NO graph, but graph.json exists (auto-extracted)',
        entryFile: {
            name: 'index.js',
            content: `export async function main(sdk) {
    console.log('Agent loop starting');
    return { status: 'ok' };
}
`,
        },
        manifest: `name: auto-graph-demo
visibility: public
config: []
`,
        graphJson: JSON.stringify(
            {
                name: 'LangGraph Auto-Extracted',
                description:
                    'Graph auto-extracted from LangGraph StateGraph at build time',
                nodes: [
                    {
                        id: '__start__',
                        type: 'start_node',
                        name: 'Start',
                    },
                    {
                        id: 'agent',
                        type: 'action_node',
                        name: 'Agent',
                        description: 'Main LLM reasoning step',
                        action_name: 'agent',
                    },
                    {
                        id: 'tools',
                        type: 'action_node',
                        name: 'Tool Executor',
                        description: 'Execute selected tools',
                        action_name: 'tools',
                    },
                    {
                        id: 'should_continue',
                        type: 'decision_node',
                        name: 'Should Continue?',
                        branches: [
                            { label: 'yes', condition: 'has_tool_calls' },
                            { label: 'no', condition: 'otherwise' },
                        ],
                    },
                    {
                        id: '__end__',
                        type: 'end_node',
                        name: 'End',
                        end_type: 'success',
                    },
                ],
                edges: [
                    {
                        id: 'e1',
                        from_node: '__start__',
                        to_node: 'agent',
                    },
                    {
                        id: 'e2',
                        from_node: 'agent',
                        to_node: 'should_continue',
                    },
                    {
                        id: 'e3',
                        from_node: 'should_continue',
                        to_node: 'tools',
                        label: 'yes',
                    },
                    { id: 'e4', from_node: 'tools', to_node: 'agent' },
                    {
                        id: 'e5',
                        from_node: 'should_continue',
                        to_node: '__end__',
                        label: 'no',
                    },
                ],
            },
            null,
            2,
        ),
    },
    {
        dirName: 'wf-seed-no-graph',
        name: 'simple-query',
        visibility: 'Public',
        description:
            'Manifest exists but no graph field & no graph.json — Graph tab hidden',
        entryFile: {
            name: 'index.js',
            content: `export async function main(sdk) {
    console.log('Running simple query workflow');
    return { result: 'ok', timestamp: new Date().toISOString() };
}
`,
        },
        manifest: `name: simple-query
visibility: public
params:
  query:
    description: SQL query to execute
    value: SELECT 1
    required: false
config: []
`,
        graphJson: null,
    },
    {
        dirName: 'wf-seed-decision-flow',
        name: 'decision-flow',
        visibility: 'Public',
        description:
            'Complex graph with decision nodes, subgraphs, query nodes, human nodes',
        entryFile: {
            name: 'index.js',
            content: `export async function main(sdk) {
    console.log('Triage started');
    return { status: 'triaged' };
}
`,
        },
        manifest: `name: decision-flow
visibility: public
config: []
`,
        graphJson: JSON.stringify(
            {
                name: 'Ticket Triage Pipeline',
                description:
                    'Multi-path triage with decision nodes, subgraphs, and queries',
                nodes: [
                    { id: 'start', type: 'start_node', name: 'Start' },
                    {
                        id: 'fetch_ticket',
                        type: 'query_node',
                        name: 'Fetch Ticket',
                        description: 'Query Snowflake for new ticket data',
                        question:
                            "SELECT * FROM tickets WHERE status = 'new' LIMIT 1",
                    },
                    {
                        id: 'classify',
                        type: 'action_node',
                        name: 'Classify Ticket',
                        description: 'Use Cortex to classify severity',
                        action_name: 'classifyTicket',
                    },
                    {
                        id: 'severity_check',
                        type: 'decision_node',
                        name: 'Severity?',
                        branches: [
                            {
                                label: 'critical',
                                condition: "severity == 'critical'",
                            },
                            { label: 'normal', condition: 'otherwise' },
                        ],
                    },
                    {
                        id: 'escalate',
                        type: 'subgraph_node',
                        name: 'Escalation Flow',
                        description: 'Run the escalation sub-workflow',
                        subgraph_name: 'escalation_subworkflow',
                    },
                    {
                        id: 'auto_respond',
                        type: 'action_node',
                        name: 'Auto Respond',
                        description: 'Generate and send automated response',
                        action_name: 'autoRespond',
                    },
                    {
                        id: 'human_review',
                        type: 'human_node',
                        name: 'Manager Review',
                        description: 'Manager must approve escalation',
                        human_role: 'Manager',
                        human_task: 'Review critical ticket escalation',
                    },
                    {
                        id: 'end_resolved',
                        type: 'end_node',
                        name: 'Resolved',
                        end_type: 'success',
                    },
                    {
                        id: 'end_escalated',
                        type: 'end_node',
                        name: 'Escalated',
                        end_type: 'success',
                    },
                ],
                edges: [
                    { id: 'e1', from_node: 'start', to_node: 'fetch_ticket' },
                    {
                        id: 'e2',
                        from_node: 'fetch_ticket',
                        to_node: 'classify',
                    },
                    {
                        id: 'e3',
                        from_node: 'classify',
                        to_node: 'severity_check',
                    },
                    {
                        id: 'e4',
                        from_node: 'severity_check',
                        to_node: 'escalate',
                        label: 'critical',
                    },
                    {
                        id: 'e5',
                        from_node: 'severity_check',
                        to_node: 'auto_respond',
                        label: 'normal',
                    },
                    {
                        id: 'e6',
                        from_node: 'escalate',
                        to_node: 'human_review',
                    },
                    {
                        id: 'e7',
                        from_node: 'human_review',
                        to_node: 'end_escalated',
                        label: 'Approved',
                    },
                    {
                        id: 'e8',
                        from_node: 'auto_respond',
                        to_node: 'end_resolved',
                    },
                ],
            },
            null,
            2,
        ),
    },
    {
        dirName: 'wf-seed-hitl-approval',
        name: 'hitl-approval',
        visibility: 'Public',
        description:
            'HITL workflow with params, approval gate, and interrupt data',
        entryFile: {
            name: 'index.js',
            content: `export async function main(sdk) {
    const env = sdk.getParameter('environment');
    console.log(\`Starting deploy to \${env}\`);
    const response = await sdk.interrupt({
        type: 'approval',
        question: \`Approve deployment to \${env}?\`,
    });
    console.log(\`Approved: \${JSON.stringify(response)}\`);
    return { deployed: true, environment: env };
}
`,
        },
        manifest: `name: hitl-approval
visibility: public
params:
  environment:
    description: Target deployment environment
    value: staging
    required: true
  version:
    description: Version to deploy
    required: true
config: []
`,
        graphJson: JSON.stringify(
            {
                name: 'Deploy with Approval',
                description: 'Deployment workflow requiring human approval',
                nodes: [
                    { id: 'start', type: 'start_node', name: 'Start' },
                    {
                        id: 'validate',
                        type: 'action_node',
                        name: 'Validate Build',
                        description: 'Run test suite and check build artifacts',
                        action_name: 'validateBuild',
                    },
                    {
                        id: 'approval',
                        type: 'human_node',
                        name: 'Approve Deploy',
                        description: 'Wait for deployment approval',
                        human_role: 'Release Manager',
                        human_task: 'Approve deployment to production',
                    },
                    {
                        id: 'deploy',
                        type: 'action_node',
                        name: 'Deploy',
                        description: 'Execute deployment to target environment',
                        action_name: 'runDeploy',
                    },
                    {
                        id: 'notify',
                        type: 'action_node',
                        name: 'Notify Team',
                        description:
                            'Send Slack notification with deploy status',
                        action_name: 'sendNotification',
                    },
                    {
                        id: 'end',
                        type: 'end_node',
                        name: 'Complete',
                        end_type: 'success',
                    },
                ],
                edges: [
                    { id: 'e1', from_node: 'start', to_node: 'validate' },
                    { id: 'e2', from_node: 'validate', to_node: 'approval' },
                    {
                        id: 'e3',
                        from_node: 'approval',
                        to_node: 'deploy',
                        label: 'Approved',
                    },
                    { id: 'e4', from_node: 'deploy', to_node: 'notify' },
                    { id: 'e5', from_node: 'notify', to_node: 'end' },
                ],
            },
            null,
            2,
        ),
    },
    {
        dirName: 'wf-seed-minimal',
        name: 'minimal-workflow',
        visibility: 'Private',
        description: 'No manifest at all — just an entry file',
        entryFile: {
            name: 'index.js',
            content: `export async function main(sdk) {
    return { hello: 'world' };
}
`,
        },
        manifest: null,
        graphJson: null,
    },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function writeFixtureToDisk(fixture: WorkflowFixture) {
    const dir = join(DATA_ROOT, fixture.dirName);
    mkdirSync(dir, { recursive: true });

    writeFileSync(join(dir, fixture.entryFile.name), fixture.entryFile.content);

    if (fixture.manifest) {
        writeFileSync(join(dir, 'manifest.yaml'), fixture.manifest);
    }

    if (fixture.graphJson) {
        writeFileSync(join(dir, 'graph.json'), fixture.graphJson);
    }

    return dir;
}

function ago(hours: number): Date {
    return new Date(Date.now() - hours * 3600_000);
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
    const doReset = process.argv.includes('--reset');

    if (doReset) {
        console.log('Resetting seed data...');
        const seedWorkflows = await prisma.workflow.findMany({
            where: {
                storagePath: { startsWith: join(DATA_ROOT, 'wf-seed-') },
            },
            select: { id: true },
        });
        const ids = seedWorkflows.map((w) => w.id);
        if (ids.length > 0) {
            await prisma.workflowInterrupt.deleteMany({
                where: { workflowId: { in: ids } },
            });
            await prisma.log.deleteMany({
                where: { workflowId: { in: ids } },
            });
            await prisma.workflowRun.deleteMany({
                where: { workflowId: { in: ids } },
            });
            await prisma.workflow.deleteMany({
                where: { id: { in: ids } },
            });
            console.log(`  Deleted ${ids.length} old seed workflows\n`);
        }
    }

    console.log('Seeding test data for p67 dash...\n');

    mkdirSync(DATA_ROOT, { recursive: true });

    const user = await prisma.user.upsert({
        where: { snowflakeUser: 'bobthebuilder' },
        update: {},
        create: { snowflakeUser: 'bobthebuilder' },
    });
    console.log(`  User: ${user.id} (${user.snowflakeUser})`);

    const wfMap: Record<string, { id: string; name: string }> = {};

    for (const fixture of FIXTURES) {
        const storagePath = writeFixtureToDisk(fixture);
        const workflow = await prisma.workflow.create({
            data: {
                id: fixture.dirName,
                name: fixture.name,
                storagePath,
                ownerId: user.id,
                visibility: fixture.visibility,
            },
        });
        wfMap[fixture.dirName] = { id: workflow.id, name: fixture.name };
        console.log(
            `  Workflow: ${fixture.name} (${workflow.id}) — ${fixture.description}`,
        );
    }

    // --- Runs -----------------------------------------------------------

    type RunSpec = {
        wfKey: string;
        status: string;
        exitCode: number | null;
        startedAgo: number;
        completedAgo: number | null;
    };

    const runSpecs: RunSpec[] = [
        {
            wfKey: 'wf-seed-manual-graph',
            status: 'Completed',
            exitCode: 0,
            startedAgo: 48,
            completedAgo: 47,
        },
        {
            wfKey: 'wf-seed-manual-graph',
            status: 'Completed',
            exitCode: 0,
            startedAgo: 24,
            completedAgo: 23,
        },
        {
            wfKey: 'wf-seed-manual-graph',
            status: 'Running',
            exitCode: null,
            startedAgo: 1,
            completedAgo: null,
        },
        {
            wfKey: 'wf-seed-auto-graph',
            status: 'Completed',
            exitCode: 0,
            startedAgo: 12,
            completedAgo: 11,
        },
        {
            wfKey: 'wf-seed-auto-graph',
            status: 'Failed',
            exitCode: 1,
            startedAgo: 6,
            completedAgo: 6,
        },
        {
            wfKey: 'wf-seed-no-graph',
            status: 'Completed',
            exitCode: 0,
            startedAgo: 72,
            completedAgo: 71,
        },
        {
            wfKey: 'wf-seed-decision-flow',
            status: 'Completed',
            exitCode: 0,
            startedAgo: 36,
            completedAgo: 35,
        },
        {
            wfKey: 'wf-seed-decision-flow',
            status: 'Interrupted',
            exitCode: null,
            startedAgo: 2,
            completedAgo: null,
        },
        {
            wfKey: 'wf-seed-hitl-approval',
            status: 'Interrupted',
            exitCode: null,
            startedAgo: 4,
            completedAgo: null,
        },
        {
            wfKey: 'wf-seed-hitl-approval',
            status: 'Completed',
            exitCode: 0,
            startedAgo: 96,
            completedAgo: 95,
        },
        {
            wfKey: 'wf-seed-minimal',
            status: 'Completed',
            exitCode: 0,
            startedAgo: 120,
            completedAgo: 119,
        },
    ];

    const runs: Array<{
        id: string;
        wfKey: string;
        status: string;
    }> = [];

    for (const spec of runSpecs) {
        const wf = wfMap[spec.wfKey];
        const run = await prisma.workflowRun.create({
            data: {
                workflowId: wf.id,
                userId: user.id,
                status: spec.status,
                exitCode: spec.exitCode,
                completedAt: spec.completedAgo ? ago(spec.completedAgo) : null,
                startedAt: ago(spec.startedAgo),
            },
        });
        runs.push({ id: run.id, wfKey: spec.wfKey, status: spec.status });
    }
    console.log(`  ${runs.length} runs created`);

    // --- Logs -----------------------------------------------------------

    const logTemplates: Array<{
        source: string;
        messages: string[];
    }> = [
        {
            source: 'RuntimeHost',
            messages: [
                'Starting workflow execution...',
                'Loading workflow configuration',
                'Initializing runtime environment',
            ],
        },
        {
            source: 'WorkflowNode',
            messages: [
                'Executing node: start',
                'Node completed successfully',
                'Processing records...',
                'Node completed successfully',
            ],
        },
        {
            source: 'ToolCall',
            messages: ['Calling external service', 'Response received: 200 OK'],
        },
    ];

    let logCount = 0;
    for (const run of runs) {
        for (const tpl of logTemplates) {
            for (const message of tpl.messages) {
                await prisma.log.create({
                    data: {
                        runId: run.id,
                        workflowId: wfMap[run.wfKey].id,
                        userId: user.id,
                        source: tpl.source,
                        message,
                        attributes: { timestamp: new Date().toISOString() },
                    },
                });
                logCount++;
            }
        }
    }

    const failedRun = runs.find((r) => r.status === 'Failed');
    if (failedRun) {
        for (const msg of [
            'ERROR: Connection timeout while calling external service',
            'Workflow execution failed with exit code 1',
        ]) {
            await prisma.log.create({
                data: {
                    runId: failedRun.id,
                    workflowId: wfMap[failedRun.wfKey].id,
                    userId: user.id,
                    source: 'RuntimeHost',
                    message: msg,
                    attributes: { level: 'error' },
                },
            });
            logCount++;
        }
    }
    console.log(`  ${logCount} logs created`);

    // --- Interrupts -----------------------------------------------------

    const interruptedRuns = runs.filter((r) => r.status === 'Interrupted');
    for (const run of interruptedRuns) {
        await prisma.workflowInterrupt.create({
            data: {
                runId: run.id,
                workflowId: wfMap[run.wfKey].id,
                nodeId: 'approval',
                status: 'Pending',
                payload: {
                    type: 'approval',
                    question: 'Do you approve this action?',
                    options: ['Approve', 'Reject'],
                    requester: 'CI/CD Pipeline',
                    context: {
                        environment: 'production',
                        version: '2.1.0',
                    },
                },
            },
        });
    }
    if (interruptedRuns.length > 0) {
        await prisma.workflowInterrupt.create({
            data: {
                runId: interruptedRuns[0].id,
                workflowId: wfMap[interruptedRuns[0].wfKey].id,
                nodeId: 'review_node',
                status: 'Resumed',
                payload: {
                    type: 'review',
                    question: 'Please review the generated report',
                },
                response: {
                    action: 'approved',
                    comment: 'Looks good!',
                    reviewer: 'bobthebuilder',
                },
                resumedAt: ago(1),
            },
        });
    }
    console.log(`  ${interruptedRuns.length + 1} interrupts created`);

    // --- Secret ---------------------------------------------------------

    await prisma.secret.upsert({
        where: {
            ownerId_name: { ownerId: user.id, name: 'TEST_API_KEY' },
        },
        update: {},
        create: {
            name: 'TEST_API_KEY',
            ownerId: user.id,
            secret: 'encrypted_test_secret_value',
            type: 'Secret',
        },
    });

    console.log('\nSeed complete!\n');
    console.log('Workflows created:');
    console.log(
        '  manual-graph-demo   — graph.json ETL pipeline (Graph tab visible)',
    );
    console.log(
        '  auto-graph-demo     — graph.json auto-extracted LangGraph (Graph tab visible)',
    );
    console.log(
        '  simple-query        — no graph data at all (Graph tab hidden)',
    );
    console.log(
        '  decision-flow       — complex graph: decision/subgraph/query/human nodes',
    );
    console.log(
        '  hitl-approval       — HITL workflow with params + approval gate',
    );
    console.log('  minimal-workflow    — no manifest, just index.js (Private)');
    console.log('\nVisit http://localhost:3001 to test the dashboard.');
}

main()
    .catch((e) => {
        console.error('Seed failed:', e);
        process.exit(1);
    })
    .finally(async () => {
        await prisma.$disconnect();
    });
