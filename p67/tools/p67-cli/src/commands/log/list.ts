import { select } from '@inquirer/prompts';
import { Command } from '@p67-cli/Command.ts';
import {
    ControldClient,
    type LogSource,
} from '@p67-cli/clients/ControldClient.ts';
import { DotP67Config } from '@p67-cli/config/DotP67Config.ts';
import { ctx } from '@p67-cli/context';

export const listCommand = new Command('list')
    .description('List logs for a workflow')
    .argument(
        '[workflowId]',
        'Workflow ID (optional, will prompt if not provided)',
    )
    .option('-r, --run <runId>', 'Filter by specific run ID')
    .option(
        '-s, --source <source>',
        'Filter by source (RuntimeHost, WorkflowNode, ToolCall)',
    )
    .option('-l, --limit <limit>', 'Maximum number of logs to return', '100')
    .option('--offset <offset>', 'Pagination offset', '0')
    .action(
        async (
            workflowId: string | undefined,
            options: {
                run?: string;
                source?: string;
                limit: string;
                offset: string;
            },
        ) => {
            try {
                const { connection } = ctx();

                const dotP67Config = new DotP67Config('.');

                const client = new ControldClient({
                    baseUrl: connection.endpoint,
                    pat: connection.pat,
                });

                let selectedWorkflowId = workflowId;

                // If no workflow ID provided, prompt user to select one
                if (!selectedWorkflowId) {
                    console.log('Fetching available workflows...\n');
                    const result = await client.listWorkflows();

                    if (result.workflows.length === 0) {
                        throw new Error('No workflows found');
                    }

                    const choices = result.workflows.map((wf) => ({
                        value: wf.workflowId,
                        updatedAt: wf.updatedAt,
                        name: `${wf.workflowId} (${wf.updatedAt}, owner: ${wf.owner})`,
                    }));

                    // Sort by updatedAt descending
                    choices.sort(
                        (a, b) =>
                            new Date(b.updatedAt).getTime() -
                            new Date(a.updatedAt).getTime(),
                    );

                    // If there's a workflowId in the dotP67Config, sort such that it's first
                    if (dotP67Config.get().workflowId) {
                        choices.sort((a, _b) =>
                            a.value === dotP67Config.get().workflowId ? -1 : 1,
                        );
                    }

                    selectedWorkflowId = await select({
                        message: 'Select a workflow to view logs:',
                        choices: choices,
                    });
                }

                console.log(
                    `\nFetching logs for workflow: ${selectedWorkflowId}\n`,
                );

                // Validate source if provided
                let source: LogSource | undefined;
                if (options.source) {
                    const validSources = [
                        'RuntimeHost',
                        'WorkflowNode',
                        'ToolCall',
                    ];
                    if (!validSources.includes(options.source)) {
                        throw new Error(
                            `Invalid source: ${options.source}. Must be one of: ${validSources.join(', ')}`,
                        );
                    }
                    source = options.source as LogSource;
                }

                const logsResult = await client.listLogs({
                    workflowId: selectedWorkflowId,
                    runId: options.run,
                    source,
                    limit: Number.parseInt(options.limit, 10),
                    offset: Number.parseInt(options.offset, 10),
                });

                if (logsResult.logs.length === 0) {
                    console.log('No logs found for this workflow.');
                    return;
                }

                // Group logs by run
                const logsByRun = new Map<string, typeof logsResult.logs>();
                for (const log of logsResult.logs) {
                    const runLogs = logsByRun.get(log.runId) ?? [];
                    runLogs.push(log);
                    logsByRun.set(log.runId, runLogs);
                }

                // Display logs grouped by run
                for (const [runId, logs] of logsByRun) {
                    console.log('─'.repeat(50));
                    console.log(`Run ID: ${runId}`);
                    console.log('─'.repeat(50));

                    for (const log of logs) {
                        const timestamp = new Date(log.timestamp).toISOString();
                        console.log(
                            `[${timestamp}] [${log.source}] ${log.message}`,
                        );
                    }
                    console.log('');
                }

                console.log(`Total logs: ${logsResult.total}`);
            } catch (error) {
                console.error('Failed to list logs');
                throw error;
            }
        },
    );
