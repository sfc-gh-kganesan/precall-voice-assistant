import { Annotation, StateGraph } from '@langchain/langgraph';
import type { WorkflowSDK } from './sdk';

// =============================================================================
// State Definition
// =============================================================================

const StateAnnotation = Annotation.Root({
    sdk: Annotation<WorkflowSDK>({
        reducer: (_, right) => right,
    }),
    // Input parameters
    accountId: Annotation<string>({
        reducer: (_, right) => right,
    }),
    accountName: Annotation<string>({
        reducer: (_, right) => right,
    }),
    limit: Annotation<number>({
        reducer: (_, right) => right,
    }),
    // Intermediate state
    contacts: Annotation<Record<string, unknown>[]>({
        reducer: (_, right) => right,
    }),
    totalCandidates: Annotation<number>({
        reducer: (_, right) => right,
    }),
    errors: Annotation<string[]>({
        reducer: (left, right) => left.concat(right),
    }),
    // Output
    finalResult: Annotation<Record<string, unknown> | null>({
        reducer: (_, right) => right,
    }),
    status: Annotation<string>({
        reducer: (_, right) => right,
    }),
});

// =============================================================================
// Contact type priority (replicates SP ORDER BY logic)
// =============================================================================

const CONTACT_TYPE_PRIORITY: Record<string, number> = {
    'Quality Contact': 1,
    'Recent MQL': 2,
    'Recently Engaged': 3,
    'Email Contact': 4,
};
const DEFAULT_PRIORITY = 5;

function sortAndLimitContacts(
    contacts: Record<string, unknown>[],
    limit: number,
): Record<string, unknown>[] {
    if (!contacts.length) return [];

    const sorted = [...contacts];

    // Stable sort: first by date DESC (secondary), then by type priority ASC (primary)
    sorted.sort((a, b) => {
        const dateA = String(a.interesting_moment_date || '');
        const dateB = String(b.interesting_moment_date || '');
        return dateB.localeCompare(dateA);
    });
    sorted.sort((a, b) => {
        const typeA = String(a.contact_intelligence_type || '');
        const typeB = String(b.contact_intelligence_type || '');
        const prioA = CONTACT_TYPE_PRIORITY[typeA] ?? DEFAULT_PRIORITY;
        const prioB = CONTACT_TYPE_PRIORITY[typeB] ?? DEFAULT_PRIORITY;
        return prioA - prioB;
    });

    return sorted.slice(0, limit);
}

// =============================================================================
// Prompts
// =============================================================================

const CONTACT_REASONS_PROMPT = `You are generating recommendation reasons for sales contacts at {account_name}.

For each contact, write 1-2 sentences (MAX) explaining why they are recommended for outreach.

Focus on:
1. Their intelligence classification (Quality Contact = high-priority GTM-ready, Recent MQL = marketing qualified lead, Recently Engaged = recent activity, Email Contact = verified contact)
2. Recent engagement or interesting moments (if present)
3. Role relevance to data platform decisions (seniority, department, technical/analytics/finance roles)

Keep it natural, varied, and focused on GTM relevance.

CONTACTS:
{contacts_json}

Generate a recommendation reason for each contact in order. Return JSON with "reasons" array matching contact order.`;

// =============================================================================
// Normalize Snowflake rows (uppercase keys → lowercase)
// =============================================================================

function normalizeRows(
    rows: Record<string, unknown>[],
): Record<string, unknown>[] {
    return rows.map((row) => {
        const normalized: Record<string, unknown> = {};
        for (const [key, value] of Object.entries(row)) {
            normalized[key.toLowerCase()] = value;
        }
        return normalized;
    });
}

// =============================================================================
// Node 1: Fetch Contacts
// =============================================================================

async function fetchContacts(state: typeof StateAnnotation.State) {
    const { sdk, accountId, limit: rawLimit } = state;
    const effectiveLimit = Math.min(Math.max(rawLimit || 10, 1), 100);

    if (!accountId) {
        return {
            contacts: [],
            totalCandidates: 0,
            errors: ['account_id is required for contact intelligence'],
            status: 'failed',
        };
    }

    try {
        // Call GET_QUALITY_CONTACTS table function via SQL
        console.log(
            `[contact_intelligence] Querying with accountId=${accountId}, limit=${effectiveLimit}`,
        );
        const result = await sdk.executeQueryReadOnly({
            sqlText: `SELECT * FROM TABLE(SALES.UDF.GET_QUALITY_CONTACTS(?))`,
            binds: [accountId],
        });

        const rawRows = result.rows || [];
        console.log(
            `[contact_intelligence] Query returned ${rawRows.length} rows`,
        );
        if (rawRows.length > 0) {
            console.log(
                `[contact_intelligence] First row keys: ${Object.keys(rawRows[0]).join(', ')}`,
            );
        }
        const allContacts = normalizeRows(rawRows);
        const contacts = sortAndLimitContacts(allContacts, effectiveLimit);

        return {
            contacts,
            totalCandidates: contacts.length,
            errors: [],
        };
    } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        console.error(`[contact_intelligence] Primary query failed: ${msg}`);

        // If primary function fails with unknown function, try fallback
        if (
            msg.includes('002143') ||
            msg.includes('Unknown user-defined table function')
        ) {
            try {
                const result = await sdk.executeQueryReadOnly({
                    sqlText: `SELECT * FROM TABLE(GET_QUALITY_CONTACTS(?))`,
                    binds: [accountId],
                });
                const allContacts = normalizeRows(result.rows || []);
                const contacts = sortAndLimitContacts(
                    allContacts,
                    effectiveLimit,
                );
                return {
                    contacts,
                    totalCandidates: contacts.length,
                    errors: [],
                };
            } catch (fallbackErr: unknown) {
                const fallbackMsg =
                    fallbackErr instanceof Error
                        ? fallbackErr.message
                        : String(fallbackErr);
                return {
                    contacts: [],
                    totalCandidates: 0,
                    errors: [`Contact retrieval failed: ${fallbackMsg}`],
                    status: 'failed',
                };
            }
        }

        return {
            contacts: [],
            totalCandidates: 0,
            errors: [`Contact retrieval failed: ${msg}`],
            status: 'failed',
        };
    }
}

// =============================================================================
// Node 2: Format Output
// =============================================================================

function buildRecommendationReason(contact: Record<string, unknown>): string {
    const reasons: string[] = [];

    const intelType = (contact.contact_intelligence_type as string) || '';
    if (intelType === 'Quality Contact')
        reasons.push('High-quality GTM-ready contact');
    else if (intelType === 'Recent MQL')
        reasons.push('Recent marketing qualified lead');
    else if (intelType === 'Recently Engaged')
        reasons.push('Recently engaged with Snowflake');
    else if (intelType === 'Email Contact')
        reasons.push('Verified email contact');

    const momentDesc = (contact.interesting_moment_desc as string) || '';
    const momentType = (contact.interesting_moment_type as string) || '';
    if (momentDesc) reasons.push(`Recent activity: ${momentDesc}`);
    else if (momentType)
        reasons.push(`Recent ${momentType.toLowerCase()} activity`);

    const seniority = (contact.seniority as string) || '';
    const role = (contact.role as string) || '';
    const department = (contact.department as string) || '';
    const roleParts: string[] = [];

    if (seniority.includes('CxO') || seniority.includes('Founder'))
        roleParts.push('C-level decision-maker');
    else if (seniority.includes('VP') || seniority.includes('SVP'))
        roleParts.push('VP-level executive');
    else if (seniority.includes('Director'))
        roleParts.push('Director-level leader');

    if (role.includes('Technical')) roleParts.push('technical role');
    else if (role.includes('BI') || role.includes('Analyst'))
        roleParts.push('analytics/BI role');

    if (department && department !== 'Unknown')
        roleParts.push(`${department} department`);

    if (roleParts.length) reasons.push(roleParts.join(', '));

    return reasons.length
        ? reasons.join('; ')
        : 'Identified as relevant contact for account';
}

function formatContactAsDetail(
    contact: Record<string, unknown>,
    recommendation: string,
): Record<string, unknown> {
    const name = (contact.name as string) || 'Unknown Contact';
    const title = (contact.title as string) || '';

    const attributes: Record<string, unknown>[] = [];

    if (recommendation)
        attributes.push({
            label: 'Recommendation',
            value: recommendation,
            type: 'string',
        });

    const email = (contact.email as string) || '';
    if (email) attributes.push({ label: 'Email', value: email, type: 'email' });

    const phone = (contact.phone as string) || '';
    if (phone)
        attributes.push({ label: 'Phone', value: phone, type: 'string' });

    const department = (contact.department as string) || '';
    if (department)
        attributes.push({
            label: 'Department',
            value: department,
            type: 'string',
        });

    const seniority = (contact.seniority as string) || '';
    if (seniority)
        attributes.push({
            label: 'Seniority',
            value: seniority,
            type: 'string',
        });

    const role = (contact.role as string) || '';
    if (role) attributes.push({ label: 'Role', value: role, type: 'string' });

    const intelType = (contact.contact_intelligence_type as string) || '';
    if (intelType)
        attributes.push({ label: 'Type', value: intelType, type: 'string' });

    const status = (contact.status as string) || '';
    if (status)
        attributes.push({ label: 'Status', value: status, type: 'string' });

    const momentType = (contact.interesting_moment_type as string) || '';
    if (momentType)
        attributes.push({
            label: 'Recent Activity',
            value: momentType,
            type: 'string',
        });

    return { header: name, content: title, attributes };
}

async function formatOutput(state: typeof StateAnnotation.State) {
    const { sdk, contacts, totalCandidates } = state;
    const accountName = state.accountName || 'this account';

    if (!contacts || !contacts.length) {
        return {
            finalResult: {
                response: [
                    {
                        header: 'Contacts',
                        summary: `No contacts are currently available for ${accountName}. Please verify the account ID or check CRM for updates.`,
                        details: [],
                    },
                ],
                sources: [],
            },
            status: 'no_results',
        };
    }

    // Generate LLM reasons via cortexComplete
    let llmReasons: string[] = [];
    try {
        const contactSummaries = contacts.map((c) => ({
            name: c.name || 'Unknown',
            title: c.title,
            contact_intelligence_type: c.contact_intelligence_type,
            seniority: c.seniority,
            role: c.role,
            department: c.department,
            interesting_moment_type: c.interesting_moment_type,
            interesting_moment_desc: c.interesting_moment_desc,
        }));

        const prompt = CONTACT_REASONS_PROMPT.replace(
            '{account_name}',
            accountName,
        ).replace('{contacts_json}', JSON.stringify(contactSummaries, null, 2));

        const llmResult = await sdk.cortexComplete({
            model: 'claude-haiku-4-5',
            prompt,
            responseFormat: {
                type: 'json',
                schema: {
                    type: 'object',
                    properties: {
                        reasons: {
                            type: 'array',
                            items: { type: 'string' },
                        },
                    },
                    required: ['reasons'],
                },
            },
            maxTokens: 1024,
            temperature: 0.3,
        });

        const parsed =
            typeof llmResult.text === 'string'
                ? JSON.parse(llmResult.text)
                : llmResult.text;
        if (parsed?.reasons && Array.isArray(parsed.reasons)) {
            llmReasons = parsed.reasons;
        }
    } catch {
        // Fallback to mechanical reasons (handled below)
    }

    // Build contacts section
    const highPriorityCount = contacts.filter(
        (c) =>
            c.contact_intelligence_type === 'Quality Contact' ||
            c.contact_intelligence_type === 'Recent MQL',
    ).length;

    const totalText =
        totalCandidates > contacts.length
            ? `There are ${totalCandidates} contacts available for ${accountName}`
            : `There are ${contacts.length} contacts available for ${accountName}`;

    const priorityText =
        highPriorityCount > 0
            ? `, with ${highPriorityCount} high-priority contacts identified based on seniority and strategic roles in technology, finance, and operations`
            : '';

    const summary = `${totalText}${priorityText}.`;

    const details = contacts.map((contact, i) => {
        const recommendation =
            i < llmReasons.length && llmReasons[i]
                ? llmReasons[i]
                : buildRecommendationReason(contact);
        return formatContactAsDetail(contact, recommendation);
    });

    return {
        finalResult: {
            response: [{ header: 'Contacts', summary, details }],
            sources: [],
        },
        status: 'success',
    };
}

// =============================================================================
// Graph: START -> fetch_contacts -> format_output -> END
// =============================================================================

const workflow = new StateGraph(StateAnnotation)
    .addNode('fetch_contacts', fetchContacts)
    .addNode('format_output', formatOutput)
    .addEdge('__start__', 'fetch_contacts')
    .addEdge('fetch_contacts', 'format_output')
    .addEdge('format_output', '__end__');

const app = workflow.compile();

// =============================================================================
// Entry Point
// =============================================================================

export async function main(sdk: WorkflowSDK) {
    const accountId = sdk.getParameter('account_id') || '';
    const accountName = sdk.getParameter('account_name') || 'this account';
    const limit = parseInt(sdk.getParameter('limit') || '10', 10);

    const result = await app.invoke({
        sdk,
        accountId,
        accountName,
        limit,
        contacts: [],
        totalCandidates: 0,
        errors: [],
        finalResult: null,
        status: 'pending',
    });

    if (result.status === 'failed') {
        throw new Error(
            `Contact intelligence failed: ${result.errors.join('; ')}`,
        );
    }

    await sdk.close();

    return result.finalResult;
}
