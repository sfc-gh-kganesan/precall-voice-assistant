import { select } from '@inquirer/prompts';
import { Command } from '@p67-cli/Command.ts';
import type {
    RunEntry,
    WorkflowRunStatusResponse,
} from '@p67-cli/clients/ControldClient.ts';
import { ControldClient } from '@p67-cli/clients/ControldClient.ts';
import { ctx } from '@p67-cli/context';

function formatDate(iso: string): string {
    const d = new Date(iso);
    return d.toLocaleString();
}

function formatDuration(startIso: string, endIso: string | null): string {
    if (!endIso) return 'still running';
    const ms = new Date(endIso).getTime() - new Date(startIso).getTime();
    const seconds = Math.floor(ms / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remaining = seconds % 60;
    return `${minutes}m ${remaining}s`;
}

function statusLabel(run: RunEntry): string {
    switch (run.status) {
        case 'completed':
            return 'completed';
        case 'failed':
            return 'FAILED';
        case 'interrupted':
            return 'interrupted';
        case 'running':
            return 'running...';
        case 'cancelled':
            return 'cancelled';
        default:
            return run.status;
    }
}

function displayRunResult(result: WorkflowRunStatusResponse): void {
    console.log('─'.repeat(50));
    console.log(`Run ID:    ${result.runId}`);
    console.log(`Exit Code: ${result.exitCode ?? 'N/A'}`);
    console.log(
        `Status:    ${result.status === 'completed' ? 'Success' : result.status}`,
    );
    console.log('─'.repeat(50));

    if (result.result !== undefined && result.result !== null) {
        console.log('\nResult:');
        if (typeof result.result === 'string') {
            console.log(result.result);
        } else {
            console.log(JSON.stringify(result.result, null, 2));
        }
    }

    if (result.log && result.log.length > 0) {
        console.log('\nLog:');
        console.log(result.log.join('\n'));
    }
    if (result.stdout && result.stdout.length > 0) {
        console.log('\nStdout:');
        console.log(result.stdout.join('\n'));
    }
    if (result.stderr && result.stderr.length > 0) {
        console.log('\nStderr:');
        console.error(result.stderr.join('\n'));
    }
    if (result.errors && result.errors.length > 0) {
        console.log('\nErrors:');
        for (const err of result.errors) {
            console.error(`  ${err.error} - ${err.message}`);
        }
    }
}

export const runsCommand = new Command('runs')
    .description('Browse workflow runs and view results')
    .argument('[workflowId]', 'Workflow ID (skip selection prompt)')
    .option('-n, --name <name>', 'Select workflow by name')
    .option('-l, --limit <limit>', 'Number of runs to show', '20')
    .action(
        async (
            workflowId: string | undefined,
            options: { name?: string; limit: string },
        ) => {
            try {
                const { connection } = ctx();
                const client = new ControldClient({
                    baseUrl: connection.endpoint,
                    pat: connection.pat,
                });

                let selectedWorkflowId = workflowId;

                // If --name is provided, resolve to latest workflow ID
                if (options.name && !selectedWorkflowId) {
                    const versions = await client.getWorkflowVersions(
                        options.name,
                    );
                    if (versions.workflows.length === 0) {
                        console.error(
                            `No workflow found with name "${options.name}"`,
                        );
                        process.exit(1);
                    }
                    // Use the latest version
                    const latest = versions.workflows[0];
                    if (!latest) {
                        console.error(
                            `No workflow found with name "${options.name}"`,
                        );
                        process.exit(1);
                    }
                    selectedWorkflowId = latest.workflowId;
                }

                // If no workflow specified, prompt user to select
                if (!selectedWorkflowId) {
                    console.log('Fetching workflows...\n');
                    const result = await client.listWorkflows();

                    if (result.workflows.length === 0) {
                        console.log('No workflows found.');
                        return;
                    }

                    const choices = result.workflows.map((wf) => ({
                        value: wf.workflowId,
                        updatedAt: wf.updatedAt,
                        name: wf.name
                            ? `${wf.name} [${wf.workflowId}]`
                            : wf.workflowId,
                    }));
                    choices.sort(
                        (a, b) =>
                            new Date(b.updatedAt).getTime() -
                            new Date(a.updatedAt).getTime(),
                    );

                    selectedWorkflowId = await select({
                        message: 'Select a workflow:',
                        choices,
                    });
                }

                // Fetch runs for the selected workflow
                const limit = Number.parseInt(options.limit, 10);
                const runsResult = await client.listRuns(selectedWorkflowId, {
                    limit,
                });

                if (runsResult.runs.length === 0) {
                    console.log('No runs found for this workflow.');
                    return;
                }

                // Prompt user to select a run
                const runChoices = runsResult.runs.map((run) => ({
                    value: run.id,
                    name: `${formatDate(run.startedAt)}  ${statusLabel(run).padEnd(12)}  ${formatDuration(run.startedAt, run.completedAt).padEnd(10)}  ${run.logCount} logs  [${run.id.slice(0, 8)}]`,
                }));

                const selectedRunId = await select({
                    message: `Select a run (${runsResult.total} total):`,
                    choices: runChoices,
                });

                // Fetch full run details
                console.log('');
                const runDetails = await client.getRunStatus(selectedRunId);
                displayRunResult(runDetails);
            } catch (error) {
                if (
                    error instanceof Error &&
                    error.message.includes('User force closed')
                ) {
                    return;
                }
                console.error('Error browsing workflow runs');
                throw error;
            }
        },
    );
