// TODO (follow-up if PoC succeeds):
//   1. Add mcp.atlassian.com to SNOWFLAKE_EGRESS_EAI callback in native-app/configure_callbacks.sql
//      so it survives app redeploys. Currently added as a one-off to the network rule.
//   2. Consider a generic "workflow egress" EAI pattern so workflow devs can reach arbitrary
//      MCP servers / APIs without needing admin intervention per-host.
//   3. Dashboard UI should filter secretRef/oauthRef params from the run form (CLI already does
//      this in run.ts:218). Currently secrets show as editable fields.
//   4. p67 doctor should send the PAT in health check requests (currently unauthenticated,
//      always fails on SPCS endpoints that require auth).

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import type { WorkflowSDK } from './sdk';

const MCP_ENDPOINT = 'https://mcp.atlassian.com/v1/mcp';
const MCP_ENDPOINT_SSE = 'https://mcp.atlassian.com/v1/sse';

interface JiraIssue {
    key: string;
    summary: string;
    status: string;
    assignee: string;
    priority: string;
}

/**
 * Create an MCP client connected to Atlassian's remote MCP server.
 * Uses Basic Auth (email:api_token) for non-interactive authentication.
 * Falls back from Streamable HTTP to SSE if needed.
 */
async function createMcpClient(
    email: string,
    apiToken: string,
): Promise<Client> {
    const basicAuth = Buffer.from(`${email}:${apiToken}`).toString('base64');
    const headers = { Authorization: `Basic ${basicAuth}` };

    // Try Streamable HTTP first (recommended transport)
    try {
        console.log('[connect_mcp] Connecting via Streamable HTTP...');
        const client = new Client({
            name: 'p67-jira-mcp-poc',
            version: '1.0.0',
        });
        const transport = new StreamableHTTPClientTransport(
            new URL(MCP_ENDPOINT),
            {
                requestInit: { headers },
            },
        );
        await client.connect(transport);
        console.log('[connect_mcp] Connected via Streamable HTTP');
        return client;
    } catch (err) {
        console.log(
            `[connect_mcp] Streamable HTTP failed: ${err instanceof Error ? err.message : err}`,
        );
    }

    // Fall back to SSE transport
    console.log('[connect_mcp] Falling back to SSE transport...');
    const client = new Client({ name: 'p67-jira-mcp-poc', version: '1.0.0' });
    const sseTransport = new SSEClientTransport(new URL(MCP_ENDPOINT_SSE), {
        requestInit: { headers },
    });
    await client.connect(sseTransport);
    console.log('[connect_mcp] Connected via SSE');
    return client;
}

/**
 * List available MCP tools and log them.
 */
async function discoverTools(client: Client): Promise<string[]> {
    const { tools } = await client.listTools();
    const toolNames = tools.map((t) => t.name);
    console.log(`[discover_tools] Found ${tools.length} tools:`);
    for (const tool of tools) {
        console.log(
            `  - ${tool.name}: ${tool.description?.slice(0, 80) || 'no description'}`,
        );
    }
    return toolNames;
}

/**
 * Resolve the Atlassian cloudId for the first accessible site.
 */
async function resolveCloudId(client: Client): Promise<string> {
    console.log('[resolve_cloud_id] Fetching accessible resources...');
    const result = await client.callTool({
        name: 'getAccessibleAtlassianResources',
        arguments: {},
    });

    let cloudId = '';
    if (Array.isArray(result.content)) {
        for (const item of result.content) {
            if (item.type === 'text' && typeof item.text === 'string') {
                console.log(
                    `[resolve_cloud_id] Response: ${item.text.slice(0, 500)}`,
                );
                try {
                    const parsed = JSON.parse(item.text);
                    if (Array.isArray(parsed) && parsed.length > 0) {
                        cloudId = parsed[0].id || parsed[0].cloudId || '';
                        console.log(
                            `[resolve_cloud_id] Using site: ${parsed[0].name || parsed[0].url || 'unknown'} (cloudId: ${cloudId})`,
                        );
                    } else if (parsed.id || parsed.cloudId) {
                        cloudId = parsed.id || parsed.cloudId;
                    }
                } catch {
                    // Try extracting cloudId from plain text
                    const match = item.text.match(
                        /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/,
                    );
                    if (match) cloudId = match[0];
                }
            }
        }
    }

    if (!cloudId) {
        throw new Error(
            'Could not resolve cloudId from getAccessibleAtlassianResources',
        );
    }
    return cloudId;
}

/**
 * Search Jira issues using JQL via the MCP server.
 */
async function searchJiraIssues(
    client: Client,
    jql: string,
    cloudId: string,
): Promise<JiraIssue[]> {
    console.log(`[search_issues] Executing JQL: ${jql} (cloudId: ${cloudId})`);

    const result = await client.callTool({
        name: 'searchJiraIssuesUsingJql',
        arguments: { jql, cloudId, maxResults: 10 },
    });

    console.log(`[search_issues] Raw result type: ${typeof result.content}`);

    // Parse the response — MCP tool results come as content array
    const issues: JiraIssue[] = [];
    if (Array.isArray(result.content)) {
        for (const item of result.content) {
            if (item.type === 'text' && typeof item.text === 'string') {
                console.log(
                    `[search_issues] Response text (first 500 chars): ${item.text.slice(0, 500)}`,
                );
                // Try to parse structured data from the text
                try {
                    const parsed = JSON.parse(item.text);
                    if (Array.isArray(parsed)) {
                        for (const issue of parsed) {
                            issues.push({
                                key: issue.key || 'unknown',
                                summary:
                                    issue.fields?.summary ||
                                    issue.summary ||
                                    'no summary',
                                status:
                                    issue.fields?.status?.name ||
                                    issue.status ||
                                    'unknown',
                                assignee:
                                    issue.fields?.assignee?.displayName ||
                                    issue.assignee ||
                                    'unassigned',
                                priority:
                                    issue.fields?.priority?.name ||
                                    issue.priority ||
                                    'none',
                            });
                        }
                    } else if (parsed.issues && Array.isArray(parsed.issues)) {
                        for (const issue of parsed.issues) {
                            issues.push({
                                key: issue.key || 'unknown',
                                summary:
                                    issue.fields?.summary ||
                                    issue.summary ||
                                    'no summary',
                                status:
                                    issue.fields?.status?.name ||
                                    issue.status ||
                                    'unknown',
                                assignee:
                                    issue.fields?.assignee?.displayName ||
                                    issue.assignee ||
                                    'unassigned',
                                priority:
                                    issue.fields?.priority?.name ||
                                    issue.priority ||
                                    'none',
                            });
                        }
                    }
                } catch {
                    // Not JSON — treat as plain text description
                    console.log(
                        '[search_issues] Response is plain text, not JSON',
                    );
                }
            }
        }
    }

    console.log(`[search_issues] Parsed ${issues.length} issues`);
    for (const issue of issues) {
        console.log(
            `  ${issue.key}: ${issue.summary} [${issue.status}] (${issue.assignee})`,
        );
    }

    return issues;
}

/**
 * Summarize Jira issues using Cortex Complete (LLM).
 */
async function summarizeIssues(
    sdk: WorkflowSDK,
    issues: JiraIssue[],
    jql: string,
): Promise<string> {
    if (issues.length === 0) {
        return 'No issues found for the given JQL query.';
    }

    const issueList = issues
        .map(
            (i) =>
                `- ${i.key}: "${i.summary}" — Status: ${i.status}, Assignee: ${i.assignee}, Priority: ${i.priority}`,
        )
        .join('\n');

    console.log('[summarize] Calling Cortex Complete for summary...');

    const result = await sdk.cortexComplete({
        model: 'claude-haiku-4-5',
        messages: [
            {
                role: 'user',
                content: `You are a project manager. Summarize the following Jira issues returned by the query "${jql}". Group them by status or theme if possible. Be concise.\n\nIssues:\n${issueList}`,
            },
        ],
        maxTokens: 500,
        temperature: 0.3,
    });

    const summary =
        typeof result === 'string' ? result : JSON.stringify(result);
    console.log(`[summarize] Summary generated (${summary.length} chars)`);
    return summary;
}

/**
 * Main workflow entry point.
 */
export async function main(sdk: WorkflowSDK) {
    const jqlQuery = sdk.getParameter('jql_query') || 'ORDER BY created DESC';
    const jiraEmail = sdk.getParameter('JIRA_EMAIL');
    const jiraApiToken = sdk.getParameter('JIRA_API_TOKEN');

    if (!jiraEmail || !jiraApiToken) {
        throw new Error(
            'Missing required secrets: JIRA_EMAIL and JIRA_API_TOKEN must be configured in manifest.yaml',
        );
    }

    console.log('=== P67 Jira MCP PoC Workflow ===\n');

    // Step 1: Connect to Atlassian MCP server
    let client: Client;
    try {
        client = await createMcpClient(jiraEmail, jiraApiToken);
    } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        console.error(`[connect_mcp] Failed to connect: ${msg}`);
        return {
            success: false,
            error: `MCP connection failed: ${msg}`,
            hint: 'Ensure your org admin has enabled API token auth for the Atlassian Rovo MCP server.',
        };
    }

    // Step 2: Discover available tools
    let toolNames: string[];
    try {
        toolNames = await discoverTools(client);
    } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        console.error(`[discover_tools] Failed: ${msg}`);
        return { success: false, error: `Tool discovery failed: ${msg}` };
    }

    // Step 3: Resolve cloudId (required for API token auth — tokens aren't bound to a site)
    let cloudId: string;
    try {
        cloudId = await resolveCloudId(client);
    } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        console.error(`[resolve_cloud_id] Failed: ${msg}`);
        return {
            success: false,
            error: `CloudId resolution failed: ${msg}`,
            availableTools: toolNames,
        };
    }

    // Step 4: Search Jira issues
    let issues: JiraIssue[];
    try {
        issues = await searchJiraIssues(client, jqlQuery, cloudId);
    } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        console.error(`[search_issues] Failed: ${msg}`);
        return {
            success: false,
            error: `JQL search failed: ${msg}`,
            availableTools: toolNames,
        };
    }

    // Step 5: Summarize with LLM
    let summary: string;
    try {
        summary = await summarizeIssues(sdk, issues, jqlQuery);
    } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        console.error(`[summarize] Failed: ${msg}`);
        summary = `Summary generation failed: ${msg}`;
    }

    // Close the MCP client
    try {
        await client.close();
    } catch {
        // Ignore close errors
    }

    console.log('\n=== Workflow Complete ===');

    return {
        success: true,
        jqlQuery,
        issueCount: issues.length,
        issues: issues.map((i) => ({
            key: i.key,
            summary: i.summary,
            status: i.status,
            assignee: i.assignee,
            priority: i.priority,
        })),
        summary,
        availableTools: toolNames,
    };
}
