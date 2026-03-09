#!/usr/bin/env node
/**
 * Seed script to populate test data for local p67 development.
 * This uses the controld API and direct database connection.
 *
 * Usage: node scripts/seed-test-data.mjs
 */

import pg from 'pg';

const { Client } = pg;

const DATABASE_URL =
    process.env.DATABASE_URL ||
    'postgresql://postgres:password@localhost:5432/controld_dev?schema=public';

async function main() {
    console.log('🌱 Seeding test data for p67 dash...\n');

    const client = new Client({ connectionString: DATABASE_URL });
    await client.connect();

    try {
        // Create or get test user
        await client.query(`
      INSERT INTO "User" (id, "createdAt", "updatedAt", "snowflakeUser")
      VALUES ('test-user-001', NOW(), NOW(), 'TEST_USER')
      ON CONFLICT ("snowflakeUser") DO UPDATE SET "updatedAt" = NOW()
    `);
        console.log('✓ User: test-user-001 (TEST_USER)');

        // Create test workflows
        await client.query(`
      INSERT INTO "Workflow" (id, name, "storagePath", "ownerId", "createdAt", "updatedAt", visibility)
      VALUES 
        ('wf-001', 'data-pipeline', '/tmp/p67/workflows/data-pipeline', 'test-user-001', NOW(), NOW(), 'Private'),
        ('wf-002', 'notification-sender', '/tmp/p67/workflows/notification-sender', 'test-user-001', NOW(), NOW(), 'Private'),
        ('wf-003', 'report-generator', '/tmp/p67/workflows/report-generator', 'test-user-001', NOW(), NOW(), 'Public'),
        ('wf-004', 'slack-approval', '/tmp/p67/workflows/slack-approval', 'test-user-001', NOW(), NOW(), 'Private')
      ON CONFLICT (id) DO NOTHING
    `);
        console.log(
            '✓ Workflows created: data-pipeline, notification-sender, report-generator, slack-approval',
        );

        // Create workflow runs with various statuses
        await client.query(`
      INSERT INTO "WorkflowRun" (id, "workflowId", "userId", "startedAt", "completedAt", "exitCode", status)
      VALUES
        ('run-001', 'wf-001', 'test-user-001', NOW() - INTERVAL '2 hours', NOW() - INTERVAL '1 hour', 0, 'Completed'),
        ('run-002', 'wf-001', 'test-user-001', NOW() - INTERVAL '30 minutes', NULL, NULL, 'Running'),
        ('run-003', 'wf-002', 'test-user-001', NOW() - INTERVAL '1 hour', NOW() - INTERVAL '45 minutes', 1, 'Failed'),
        ('run-004', 'wf-003', 'test-user-001', NOW() - INTERVAL '3 hours', NOW() - INTERVAL '2 hours', 0, 'Completed'),
        ('run-005', 'wf-004', 'test-user-001', NOW() - INTERVAL '15 minutes', NULL, NULL, 'Interrupted')
      ON CONFLICT (id) DO NOTHING
    `);
        console.log(
            '✓ Workflow runs created: Completed, Running, Failed, Completed, Interrupted',
        );

        // Create logs for runs
        await client.query(`
      INSERT INTO "Log" (id, "runId", "workflowId", "userId", source, message, attributes, "timestamp")
      VALUES
        -- Logs for completed run (run-001)
        (gen_random_uuid(), 'run-001', 'wf-001', 'test-user-001', 'RuntimeHost', 'Starting workflow execution...', '{"level": "info"}', NOW() - INTERVAL '2 hours'),
        (gen_random_uuid(), 'run-001', 'wf-001', 'test-user-001', 'RuntimeHost', 'Loading workflow configuration', '{"level": "info"}', NOW() - INTERVAL '2 hours' + INTERVAL '1 second'),
        (gen_random_uuid(), 'run-001', 'wf-001', 'test-user-001', 'WorkflowNode', 'Executing node: start', '{"nodeId": "start"}', NOW() - INTERVAL '2 hours' + INTERVAL '2 seconds'),
        (gen_random_uuid(), 'run-001', 'wf-001', 'test-user-001', 'WorkflowNode', 'Processing 1000 records...', '{"nodeId": "process"}', NOW() - INTERVAL '2 hours' + INTERVAL '10 seconds'),
        (gen_random_uuid(), 'run-001', 'wf-001', 'test-user-001', 'ToolCall', 'Calling external API: https://api.example.com/data', '{"tool": "http_request"}', NOW() - INTERVAL '2 hours' + INTERVAL '15 seconds'),
        (gen_random_uuid(), 'run-001', 'wf-001', 'test-user-001', 'ToolCall', 'API response received: 200 OK', '{"tool": "http_request", "status": 200}', NOW() - INTERVAL '2 hours' + INTERVAL '16 seconds'),
        (gen_random_uuid(), 'run-001', 'wf-001', 'test-user-001', 'RuntimeHost', 'Workflow completed successfully', '{"level": "info", "exitCode": 0}', NOW() - INTERVAL '1 hour'),

        -- Logs for running workflow (run-002)
        (gen_random_uuid(), 'run-002', 'wf-001', 'test-user-001', 'RuntimeHost', 'Starting workflow execution...', '{"level": "info"}', NOW() - INTERVAL '30 minutes'),
        (gen_random_uuid(), 'run-002', 'wf-001', 'test-user-001', 'WorkflowNode', 'Executing node: fetch_data', '{"nodeId": "fetch_data"}', NOW() - INTERVAL '29 minutes'),
        (gen_random_uuid(), 'run-002', 'wf-001', 'test-user-001', 'WorkflowNode', 'Fetching data from source...', '{"nodeId": "fetch_data"}', NOW() - INTERVAL '28 minutes'),

        -- Logs for failed run (run-003)
        (gen_random_uuid(), 'run-003', 'wf-002', 'test-user-001', 'RuntimeHost', 'Starting workflow execution...', '{"level": "info"}', NOW() - INTERVAL '1 hour'),
        (gen_random_uuid(), 'run-003', 'wf-002', 'test-user-001', 'WorkflowNode', 'Executing node: send_notification', '{"nodeId": "send_notification"}', NOW() - INTERVAL '55 minutes'),
        (gen_random_uuid(), 'run-003', 'wf-002', 'test-user-001', 'ToolCall', 'Connecting to Slack API...', '{"tool": "slack"}', NOW() - INTERVAL '50 minutes'),
        (gen_random_uuid(), 'run-003', 'wf-002', 'test-user-001', 'RuntimeHost', 'ERROR: Connection timeout while calling Slack API', '{"level": "error", "errorCode": "ETIMEOUT"}', NOW() - INTERVAL '46 minutes'),
        (gen_random_uuid(), 'run-003', 'wf-002', 'test-user-001', 'RuntimeHost', 'Workflow execution failed with exit code 1', '{"level": "error", "exitCode": 1}', NOW() - INTERVAL '45 minutes'),

        -- Logs for interrupted run (run-005)
        (gen_random_uuid(), 'run-005', 'wf-004', 'test-user-001', 'RuntimeHost', 'Starting workflow execution...', '{"level": "info"}', NOW() - INTERVAL '15 minutes'),
        (gen_random_uuid(), 'run-005', 'wf-004', 'test-user-001', 'WorkflowNode', 'Executing node: prepare_deployment', '{"nodeId": "prepare_deployment"}', NOW() - INTERVAL '14 minutes'),
        (gen_random_uuid(), 'run-005', 'wf-004', 'test-user-001', 'WorkflowNode', 'Deployment prepared, awaiting approval...', '{"nodeId": "approval"}', NOW() - INTERVAL '13 minutes'),
        (gen_random_uuid(), 'run-005', 'wf-004', 'test-user-001', 'RuntimeHost', 'Workflow interrupted - waiting for human input', '{"level": "info", "interruptType": "approval"}', NOW() - INTERVAL '12 minutes')
    `);
        console.log('✓ Logs created for all runs');

        // Create interrupts for the interrupted workflow
        await client.query(`
      INSERT INTO "WorkflowInterrupt" (id, "runId", "workflowId", "nodeId", status, payload, response, "createdAt", "resumedAt")
      VALUES
        (
          'interrupt-001',
          'run-005',
          'wf-004',
          'approval_node',
          'Pending',
          '{"type": "approval", "question": "Do you approve this deployment to production?", "options": ["Approve", "Reject", "Request Changes"], "requester": "CI/CD Pipeline", "context": {"environment": "production", "version": "2.1.0", "changes": ["Updated API endpoints", "New dashboard features", "Bug fixes for user auth"]}}',
          NULL,
          NOW() - INTERVAL '12 minutes',
          NULL
        ),
        (
          'interrupt-002',
          'run-005',
          'wf-004',
          'review_node',
          'Resumed',
          '{"type": "review", "question": "Please review the generated report", "context": {"reportId": "RPT-2024-001"}}',
          '{"action": "approved", "comment": "Looks good to me!", "reviewer": "TEST_USER"}',
          NOW() - INTERVAL '2 hours',
          NOW() - INTERVAL '1 hour'
        )
      ON CONFLICT (id) DO NOTHING
    `);
        console.log('✓ Interrupts created (1 Pending, 1 Resumed)');

        // Create a test secret
        await client.query(`
      INSERT INTO "Secret" (id, name, "createdAt", "updatedAt", "ownerId", secret, type)
      VALUES ('secret-001', 'TEST_API_KEY', NOW(), NOW(), 'test-user-001', 'encrypted_test_secret_value', 'Secret')
      ON CONFLICT ("ownerId", name) DO NOTHING
    `);
        console.log('✓ Test secret created');

        console.log('\n✅ Seed complete! Test data has been created.');
        console.log('\nSummary:');
        console.log('  - 1 test user (TEST_USER)');
        console.log(
            '  - 4 workflows (data-pipeline, notification-sender, report-generator, slack-approval)',
        );
        console.log(
            '  - 5 workflow runs (Completed, Running, Failed, Completed, Interrupted)',
        );
        console.log('  - Multiple logs for each run');
        console.log('  - 2 interrupts (1 Pending, 1 Resumed)');
        console.log('  - 1 test secret');
        console.log(
            '\nVisit http://localhost:3001 to see the dash UI with test data.',
        );
    } finally {
        await client.end();
    }
}

main().catch((e) => {
    console.error('❌ Seed failed:', e);
    process.exit(1);
});
