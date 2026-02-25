import * as fs from 'node:fs';
import { input, select } from '@inquirer/prompts';
import { Command } from '@p67-cli/Command.ts';
import { ControldClient } from '@p67-cli/clients/ControldClient.ts';
import { DotP67Config } from '@p67-cli/config/DotP67Config.ts';
import { ctx } from '@p67-cli/context';
import * as yaml from 'js-yaml';

export const runCommand = new Command('run')
    .description('Run a workflow')
    .argument('[workflowId]', 'Workflow ID to run')
    .option('-n, --name <name>', 'Run workflow by name (uses latest version)')
    .option('-t, --timeout <ms>', 'Request timeout in milliseconds', '600000')
    .option(
        '-p, --param <kv>',
        'Parameter in key=value format (repeatable)',
        (val, acc: string[]) => {
            acc.push(val);
            return acc;
        },
        [],
    )
    .option(
        '-P, --param_file <param_file>',
        'Parameter file to pass to the workflow',
    )
    .action(
        async (
            workflowId: string | undefined,
            options: {
                name?: string;
                timeout: string;
                param?: string[];
                param_file?: string;
            },
        ) => {
            // Validate that both workflowId and name are not provided
            if (workflowId && options.name) {
                console.error(
                    'Error: Cannot specify both workflow ID and --name. Use one or the other.',
                );
                process.exit(1);
            }

            const params: Record<string, string> = {};
            if (options.param) {
                // Split the param string into key=value pairs
                for (const param of options.param) {
                    const [key, value] = param.split('=');
                    if (key && value) {
                        params[key] = value;
                    }
                }
            }
            if (options.param_file) {
                const param_file = fs.readFileSync(options.param_file, 'utf8');
                try {
                    const param_file_json = yaml.load(param_file);
                    if (
                        param_file_json &&
                        typeof param_file_json === 'object'
                    ) {
                        for (const [key, value] of Object.entries(
                            param_file_json,
                        )) {
                            if (key && value && typeof value === 'string') {
                                params[key] = value;
                            }
                        }
                    }
                } catch (error) {
                    console.error('Failed to parse parameter file');
                    throw error;
                }
            }
            try {
                const { connection } = ctx();

                const dotP67Config = new DotP67Config('.');

                const client = new ControldClient({
                    baseUrl: connection.endpoint,
                    pat: connection.pat,
                    timeout: Number.parseInt(options.timeout, 10),
                });

                // If running by name, use the name-based endpoint
                if (options.name) {
                    console.log(
                        `\nRunning workflow by name: ${options.name} (latest version)\n`,
                    );

                    const runResult = await client.runWorkflowByName(
                        options.name,
                        params,
                    );

                    // Display results
                    console.log('─'.repeat(50));
                    console.log(`Exit Code: ${runResult.exitCode}`);
                    console.log(`Success: ${runResult.success}`);
                    console.log('─'.repeat(50));
                    console.log(runResult.log.join('\n'));

                    // Exit with the workflow's exit code
                    process.exit(runResult.exitCode);
                }

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
                        name: wf.name
                            ? `${wf.name} [${wf.workflowId}] (${wf.updatedAt}, owner: ${wf.owner})`
                            : `${wf.workflowId} (${wf.updatedAt}, owner: ${wf.owner})`,
                    }));
                    // Sort the choices by updatedAt descending
                    choices.sort(
                        (a, b) =>
                            new Date(b.updatedAt).getTime() -
                            new Date(a.updatedAt).getTime(),
                    );
                    // If there's a workflowid in the dotP67Config, sort such that it's first.
                    if (dotP67Config.get().workflowId) {
                        choices.sort((a, _b) =>
                            a.value === dotP67Config.get().workflowId ? -1 : 1,
                        );
                    }
                    selectedWorkflowId = await select({
                        message: 'Select a workflow to run:',
                        choices: choices,
                    });

                    // In interactive mode, prompt for missing required params
                    try {
                        const manifest =
                            await client.getWorkflowManifest(
                                selectedWorkflowId,
                            );

                        if (
                            manifest.params &&
                            Object.keys(manifest.params).length > 0
                        ) {
                            // Find params that need prompting: required params without defaults
                            // that weren't provided via CLI
                            const paramsToPrompt = Object.entries(
                                manifest.params,
                            ).filter(([key, valueObj]) => {
                                // Skip secrets - they're resolved from the secret store
                                if (valueObj.secretRef || valueObj.oauthRef) {
                                    return false;
                                }
                                // Skip if already provided via CLI
                                if (params[key] !== undefined) {
                                    return false;
                                }
                                // In non-interactive mode (CLI params provided), only prompt for missing required params
                                const hasCliParams =
                                    Object.keys(params).length > 0 ||
                                    options.param_file !== undefined;
                                if (hasCliParams) {
                                    const isRequired =
                                        valueObj.required === true;
                                    const hasDefault =
                                        valueObj.value !== undefined &&
                                        valueObj.value !== '';
                                    return isRequired && !hasDefault;
                                }
                                // In fully interactive mode, prompt for all params
                                return true;
                            });

                            if (paramsToPrompt.length > 0) {
                                console.log(
                                    '\nThis workflow has configurable parameters:\n',
                                );

                                for (const [key, valueObj] of paramsToPrompt) {
                                    const isRequired =
                                        valueObj.required === true;
                                    const defaultVal = valueObj.value ?? '';
                                    const hasDefault = defaultVal !== '';

                                    // Build the prompt message
                                    let message = key;
                                    if (isRequired && !hasDefault) {
                                        message += ' (required)';
                                    }
                                    message += ':';

                                    // Show description if provided
                                    if (valueObj.description) {
                                        console.log(
                                            `  ${key}: ${valueObj.description}`,
                                        );
                                    }

                                    const value = await input({
                                        message,
                                        default: defaultVal,
                                        required: isRequired && !hasDefault,
                                        validate: (val) => {
                                            if (
                                                isRequired &&
                                                !hasDefault &&
                                                !val
                                            ) {
                                                return `${key} is required`;
                                            }
                                            return true;
                                        },
                                    });
                                    if (value && value.trim() !== '') {
                                        params[key] = value;
                                    }
                                }
                            }
                        }
                    } catch (err) {
                        // Log error but continue - workflow may still run
                        console.error(
                            'Warning: Could not fetch workflow manifest:',
                            err instanceof Error ? err.message : err,
                        );
                    }
                }

                console.log(`\nRunning workflow: ${selectedWorkflowId}\n`);

                const runResult = await client.runWorkflow(
                    selectedWorkflowId,
                    params,
                );

                // Display results
                console.log('─'.repeat(50));
                console.log(`Exit Code: ${runResult.exitCode}`);
                console.log(`Success: ${runResult.success}`);
                console.log('─'.repeat(50));
                console.log(runResult.log.join('\n'));

                // Exit with the workflow's exit code
                process.exit(runResult.exitCode);
            } catch (error) {
                console.error('Failed to run workflow');
                throw error;
            }
        },
    );
