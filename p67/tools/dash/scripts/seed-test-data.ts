#!/usr/bin/env npx tsx
/**
 * Seed script to populate test data for local p67 development.
 * This creates workflows, runs, logs, and interrupts directly in the database
 * via Prisma to test the dash UI end-to-end.
 *
 * Usage: npx tsx scripts/seed-test-data.ts
 */

import { PrismaClient } from '@p67/db';

const prisma = new PrismaClient({
    datasources: {
        db: {
            url:
                process.env.DATABASE_URL ||
                'postgresql://postgres:password@localhost:5432/controld_dev?schema=public',
        },
    },
});

async function main() {
    console.log('🌱 Seeding test data for p67 dash...\n');

    // Create or find a test user
    const user = await prisma.user.upsert({
        where: { snowflakeUser: 'TEST_USER' },
        update: {},
        create: {
            snowflakeUser: 'TEST_USER',
        },
    });
    console.log(`✓ User: ${user.id} (${user.snowflakeUser})`);

    // Create test workflows
    const workflows = [
        {
            name: 'data-pipeline',
            storagePath: '/tmp/p67/workflows/data-pipeline',
        },
        {
            name: 'notification-sender',
            storagePath: '/tmp/p67/workflows/notification-sender',
        },
        {
            name: 'report-generator',
            storagePath: '/tmp/p67/workflows/report-generator',
        },
        {
            name: 'slack-approval',
            storagePath: '/tmp/p67/workflows/slack-approval',
        },
    ];

    const createdWorkflows = [];
    for (const wf of workflows) {
        const workflow = await prisma.workflow.create({
            data: {
                name: wf.name,
                storagePath: wf.storagePath,
                ownerId: user.id,
                visibility: 'Private',
            },
        });
        createdWorkflows.push(workflow);
        console.log(`✓ Workflow: ${workflow.name} (${workflow.id})`);
    }

    // Create workflow runs with various statuses
    const runConfigs = [
        {
            workflow: createdWorkflows[0],
            status: 'Completed' as const,
            exitCode: 0,
        },
        {
            workflow: createdWorkflows[0],
            status: 'Running' as const,
            exitCode: null,
        },
        {
            workflow: createdWorkflows[1],
            status: 'Failed' as const,
            exitCode: 1,
        },
        {
            workflow: createdWorkflows[2],
            status: 'Completed' as const,
            exitCode: 0,
        },
        {
            workflow: createdWorkflows[3],
            status: 'Interrupted' as const,
            exitCode: null,
        },
    ];

    const createdRuns = [];
    for (const rc of runConfigs) {
        const run = await prisma.workflowRun.create({
            data: {
                workflowId: rc.workflow.id,
                userId: user.id,
                status: rc.status,
                exitCode: rc.exitCode,
                completedAt:
                    rc.status === 'Running' || rc.status === 'Interrupted'
                        ? null
                        : new Date(),
            },
        });
        createdRuns.push({ run, workflow: rc.workflow, status: rc.status });
        console.log(`✓ Run: ${run.id} (${rc.workflow.name} - ${rc.status})`);
    }

    // Create logs for each run
    const logMessages = [
        {
            source: 'RuntimeHost' as const,
            messages: [
                'Starting workflow execution...',
                'Loading workflow configuration',
                'Initializing runtime environment',
            ],
        },
        {
            source: 'WorkflowNode' as const,
            messages: [
                'Executing node: start',
                'Node completed successfully',
                'Executing node: process_data',
                'Processing 1000 records...',
                'Node completed successfully',
            ],
        },
        {
            source: 'ToolCall' as const,
            messages: [
                'Calling external API: https://api.example.com/data',
                'API response received: 200 OK',
                'Data transformation complete',
            ],
        },
    ];

    for (const { run, workflow } of createdRuns) {
        for (const logConfig of logMessages) {
            for (const message of logConfig.messages) {
                await prisma.log.create({
                    data: {
                        runId: run.id,
                        workflowId: workflow.id,
                        userId: user.id,
                        source: logConfig.source,
                        message,
                        attributes: { timestamp: new Date().toISOString() },
                    },
                });
            }
        }
        console.log(`✓ Logs created for run: ${run.id}`);
    }

    // Create some error logs for the failed run
    const failedRun = createdRuns.find((r) => r.status === 'Failed');
    if (failedRun) {
        await prisma.log.create({
            data: {
                runId: failedRun.run.id,
                workflowId: failedRun.workflow.id,
                userId: user.id,
                source: 'RuntimeHost',
                message:
                    'ERROR: Connection timeout while calling external service',
                attributes: { level: 'error', errorCode: 'ETIMEOUT' },
            },
        });
        await prisma.log.create({
            data: {
                runId: failedRun.run.id,
                workflowId: failedRun.workflow.id,
                userId: user.id,
                source: 'RuntimeHost',
                message: 'Workflow execution failed with exit code 1',
                attributes: { level: 'error' },
            },
        });
        console.log(`✓ Error logs added for failed run`);
    }

    // Create interrupts for the interrupted workflow
    const interruptedRun = createdRuns.find((r) => r.status === 'Interrupted');
    if (interruptedRun) {
        await prisma.workflowInterrupt.create({
            data: {
                runId: interruptedRun.run.id,
                workflowId: interruptedRun.workflow.id,
                nodeId: 'approval_node',
                status: 'Pending',
                payload: {
                    type: 'approval',
                    question: 'Do you approve this deployment to production?',
                    options: ['Approve', 'Reject', 'Request Changes'],
                    requester: 'CI/CD Pipeline',
                    context: {
                        environment: 'production',
                        version: '2.1.0',
                        changes: [
                            'Updated API endpoints',
                            'New dashboard features',
                            'Bug fixes for user auth',
                        ],
                    },
                },
            },
        });

        // Add a second interrupt that was already resumed
        await prisma.workflowInterrupt.create({
            data: {
                runId: interruptedRun.run.id,
                workflowId: interruptedRun.workflow.id,
                nodeId: 'review_node',
                status: 'Resumed',
                payload: {
                    type: 'review',
                    question: 'Please review the generated report',
                    context: { reportId: 'RPT-2024-001' },
                },
                response: {
                    action: 'approved',
                    comment: 'Looks good to me!',
                    reviewer: 'TEST_USER',
                },
                resumedAt: new Date(Date.now() - 3600000), // 1 hour ago
            },
        });
        console.log(`✓ Interrupts created for interrupted run`);
    }

    // Create a secret for testing
    await prisma.secret.upsert({
        where: {
            ownerId_name: {
                ownerId: user.id,
                name: 'TEST_API_KEY',
            },
        },
        update: {},
        create: {
            name: 'TEST_API_KEY',
            ownerId: user.id,
            secret: 'encrypted_test_secret_value',
            type: 'Secret',
        },
    });
    console.log(`✓ Test secret created`);

    console.log('\n✅ Seed complete! Test data has been created.');
    console.log(
        '\nYou can now visit http://localhost:3001 to see the dash UI with test data.',
    );
}

main()
    .catch((e) => {
        console.error('❌ Seed failed:', e);
        process.exit(1);
    })
    .finally(async () => {
        await prisma.$disconnect();
    });
