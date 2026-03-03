import { Command } from '@p67-cli/Command.ts';
import type { Workflow } from '@p67-cli/clients/ControldClient.ts';
import { ControldClient } from '@p67-cli/clients/ControldClient.ts';
import { ctx } from '@p67-cli/context';

export const listCommand = new Command('list')
    .description('List all available workflows')
    .action(async () => {
        try {
            const { connection } = ctx();
            const client = new ControldClient({
                baseUrl: connection.endpoint,
                pat: connection.pat,
            });
            const result = await client.listWorkflows();

            if (result.workflows.length === 0) {
                console.log('No workflows found.');
                return;
            }

            // Group workflows by name for display
            const named = new Map<string, Workflow[]>();
            const unnamed: Workflow[] = [];

            for (const workflow of result.workflows) {
                if (workflow.name) {
                    const group = named.get(workflow.name) ?? [];
                    group.push(workflow);
                    named.set(workflow.name, group);
                } else {
                    unnamed.push(workflow);
                }
            }

            // Sort versions within each group by createdAt descending
            for (const group of named.values()) {
                group.sort(
                    (a, b) =>
                        new Date(b.createdAt).getTime() -
                        new Date(a.createdAt).getTime(),
                );
            }

            // Display named workflows grouped
            for (const [name, versions] of named) {
                const latest = versions[0];
                if (!latest) continue;
                const versionLabel =
                    versions.length === 1
                        ? '1 version'
                        : `${versions.length} versions`;
                console.log(
                    `${name} (${versionLabel}, ${latest.visibility}, owner: ${latest.owner})`,
                );
                versions.forEach((v, i) => {
                    const label =
                        i === 0 ? 'latest' : `v${versions.length - i}`;
                    const date = v.createdAt.split('T')[0];
                    console.log(
                        `  ${label.padEnd(8)} ${v.workflowId}  ${date}`,
                    );
                });
            }

            // Display unnamed workflows individually
            for (const workflow of unnamed) {
                console.log(
                    `${workflow.workflowId} (${workflow.visibility}, owner: ${workflow.owner})`,
                );
            }
        } catch (error) {
            console.error('Error listing workflows');
            throw error;
        }
    });
