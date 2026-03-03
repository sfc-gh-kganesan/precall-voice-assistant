import { Annotation, StateGraph } from '@langchain/langgraph';
import type { SubworkflowResponse, WorkflowSDK } from './sdk';

// =============================================================================
// Helper: Parse sub-workflow response stdout into structured data
// =============================================================================

function parseSubworkflowOutput(
    response: SubworkflowResponse,
): Record<string, unknown> {
    if (!response.success) {
        throw new Error(
            response.error ||
                `Subworkflow failed with status: ${response.status}`,
        );
    }

    // Prefer structured result (IPC) over stdout
    if (response.result != null) {
        if (
            typeof response.result === 'object' &&
            !Array.isArray(response.result)
        ) {
            return response.result as Record<string, unknown>;
        }
        return { rawResult: response.result };
    }

    // Fall back to parsing stdout
    const output = response.stdout?.join('') || '{}';
    try {
        return JSON.parse(output);
    } catch {
        return { rawOutput: output };
    }
}

// =============================================================================
// Helper: Find a section by header substring from a response[] array
// =============================================================================

function findSection(
    result: Record<string, unknown>,
    headerMatch: string,
): Record<string, unknown> | null {
    const response = (result.response || []) as Record<string, unknown>[];
    for (const section of response) {
        if (
            typeof section.header === 'string' &&
            section.header.toLowerCase().includes(headerMatch.toLowerCase())
        ) {
            return section;
        }
    }
    return null;
}

// =============================================================================
// State Definition
// =============================================================================

const StateAnnotation = Annotation.Root({
    sdk: Annotation<WorkflowSDK>({ reducer: (_, r) => r }),
    accountId: Annotation<string>({ reducer: (_, r) => r }),
    accountName: Annotation<string>({ reducer: (_, r) => r }),
    // Sub-workflow results
    companyResearchResult: Annotation<Record<string, unknown> | null>({
        reducer: (_, r) => r,
    }),
    valuePropositionResult: Annotation<Record<string, unknown> | null>({
        reducer: (_, r) => r,
    }),
    contactIntelligenceResult: Annotation<Record<string, unknown> | null>({
        reducer: (_, r) => r,
    }),
    // Derived context for downstream workflows
    companyProfileSummary: Annotation<string>({ reducer: (_, r) => r }),
    recentNewsSummary: Annotation<string>({ reducer: (_, r) => r }),
    // Output
    finalResult: Annotation<Record<string, unknown> | null>({
        reducer: (_, r) => r,
    }),
    status: Annotation<string>({ reducer: (_, r) => r }),
    errors: Annotation<string[]>({ reducer: (l, r) => l.concat(r) }),
});

// =============================================================================
// LLM Synthesis Schemas (per-section)
// =============================================================================

const COMPANY_INSIGHTS_SCHEMA = {
    type: 'object',
    additionalProperties: false,
    properties: {
        header: { type: 'string' },
        summary: { type: 'string' },
        details: {
            type: 'array',
            items: {
                type: 'object',
                additionalProperties: false,
                properties: {
                    header: { type: 'string' },
                    content: { type: 'string' },
                },
                required: ['header', 'content'],
            },
        },
    },
    required: ['header', 'summary', 'details'],
};

const INDUSTRY_INSIGHTS_SCHEMA = { ...COMPANY_INSIGHTS_SCHEMA };

const COMPETITORS_SCHEMA = {
    type: 'object',
    additionalProperties: false,
    properties: {
        header: { type: 'string' },
        summary: { type: 'string' },
        details: { type: 'array' },
    },
    required: ['header', 'summary', 'details'],
};

// =============================================================================
// Helper: Extract context from company research for downstream workflows
// =============================================================================

function extractContextForDownstream(
    companyResult: Record<string, unknown>,
): [string, string] {
    let companyProfileSummary = '';
    let recentNewsSummary = '';

    // Extract from response[] array (actual COMPANY_RESEARCH output format)
    const profileSection = findSection(companyResult, 'Company Profile');
    if (profileSection) {
        companyProfileSummary = JSON.stringify(profileSection);
    }

    const newsSection = findSection(companyResult, 'News');
    if (newsSection) {
        const summary = newsSection.summary as string;
        if (summary) {
            recentNewsSummary = summary.slice(0, 500);
        } else {
            const details = (newsSection.details || []) as Record<
                string,
                unknown
            >[];
            if (details.length > 0) {
                recentNewsSummary = details
                    .slice(0, 3)
                    .map((d) => `- ${d.header || 'News'}`)
                    .join('\n');
            }
        }
    }

    // Fallback: try legacy flat keys for backwards compatibility
    if (!companyProfileSummary) {
        const companyProfile = companyResult.company_profile;
        if (companyProfile) {
            companyProfileSummary = JSON.stringify(companyProfile);
        }
    }
    if (!recentNewsSummary) {
        let recentNews = companyResult.recent_news as
            | Record<string, unknown>
            | string
            | null;
        if (typeof recentNews === 'string') {
            try {
                recentNews = JSON.parse(recentNews);
            } catch {
                recentNews = null;
            }
        }
        if (recentNews && typeof recentNews === 'object') {
            const summary = (recentNews as Record<string, unknown>)
                .combined_summary_all_news_articles as string;
            if (summary) {
                recentNewsSummary = summary.slice(0, 500);
            }
        }
    }

    return [companyProfileSummary, recentNewsSummary];
}

// =============================================================================
// Helper: Format contacts section mechanically
// =============================================================================

function formatContactsSection(
    contactResult: Record<string, unknown> | null,
    accountName: string,
): Record<string, unknown> {
    if (!contactResult) {
        return {
            header: 'Contacts',
            summary:
                'No contacts available at this time. Please go to LinkedIn Sales Navigator to add contacts to Salesforce for the account.',
            details: [],
        };
    }

    const response = (contactResult.response || []) as Record<
        string,
        unknown
    >[];
    // Find the Contacts section in the response
    for (const section of response) {
        if ((section.header as string)?.includes('Contact')) {
            return section;
        }
    }

    // Fallback: build from raw contacts if available
    const contacts = (contactResult.contacts || []) as Record<
        string,
        unknown
    >[];
    if (contacts.length === 0) {
        return {
            header: 'Contacts',
            summary: 'No contacts available at this time.',
            details: [],
        };
    }

    const details = contacts.slice(0, 5).map((c) => ({
        header: (c.name as string) || 'Unknown',
        content: (c.title as string) || '',
        attributes: [
            { label: 'Email', value: (c.email as string) || '', type: 'email' },
            {
                label: 'Department',
                value: (c.department as string) || '',
                type: 'string',
            },
            {
                label: 'Seniority',
                value: (c.seniority as string) || '',
                type: 'string',
            },
        ].filter((a) => a.value),
    }));

    return {
        header: 'Contacts',
        summary: `There are ${contacts.length} contacts available for ${accountName}.`,
        details,
    };
}

// =============================================================================
// Helper: Format news section mechanically
// =============================================================================

function formatNewsSection(
    companyResult: Record<string, unknown> | null,
): Record<string, unknown> {
    const noNews = {
        header: 'Recent Company News',
        summary: 'No recent news available within the last 90 days.',
        details: [],
    };

    if (!companyResult) {
        return noNews;
    }

    // Check response[] array first (actual COMPANY_RESEARCH format)
    const newsFromResponse = findSection(companyResult, 'News');
    if (newsFromResponse) {
        return {
            header: 'Recent Company News',
            summary: (newsFromResponse.summary as string) || noNews.summary,
            details: (newsFromResponse.details as unknown[]) || [],
        };
    }

    // Fallback: legacy flat key format
    let recentNews = companyResult.recent_news as
        | Record<string, unknown>
        | string
        | null;
    if (typeof recentNews === 'string') {
        try {
            recentNews = JSON.parse(recentNews);
        } catch {
            recentNews = null;
        }
    }

    if (!recentNews || typeof recentNews !== 'object') {
        return noNews;
    }

    const newsSummary =
        ((recentNews as Record<string, unknown>)
            .combined_summary_all_news_articles as string) || '';
    const articles = ((recentNews as Record<string, unknown>).articles ||
        []) as Record<string, unknown>[];

    const details = articles.slice(0, 3).map((a) => ({
        header: `• ${(a.title as string) || 'Article'}`,
        content: `Published by ${(a.publisher as string) || (a.source as string) || 'Unknown'}`,
        attributes: [
            {
                label: 'Source',
                value: (a.publisher as string) || (a.source as string) || '',
                type: 'string',
            },
            ...(a.date
                ? [{ label: 'Date', value: a.date as string, type: 'date' }]
                : []),
            ...(a.url
                ? [{ label: 'URL', value: a.url as string, type: 'url' }]
                : []),
        ].filter((attr) => attr.value),
    }));

    return {
        header: 'Recent Company News',
        summary:
            newsSummary ||
            (articles.length > 0
                ? `${articles.length} recent news articles found.`
                : 'No recent news available within the last 90 days.'),
        details,
    };
}

// =============================================================================
// Helper: Synthesize a single section via LLM
// =============================================================================

async function synthesizeSection(
    sdk: WorkflowSDK,
    sectionName: string,
    prompt: string,
    schema: Record<string, unknown>,
): Promise<Record<string, unknown> | null> {
    try {
        const schemaHint = JSON.stringify(schema, null, 2);
        const fullPrompt = `${prompt}\n\nYou MUST respond with ONLY valid JSON matching this schema:\n${schemaHint}`;

        const result = await sdk.cortexComplete({
            model: 'claude-haiku-4-5',
            messages: fullPrompt,
            maxTokens: 2000,
            temperature: 0.3,
        });

        if (!result.success) {
            throw new Error(result.error || 'cortexComplete failed');
        }

        let content = result.choices?.[0]?.message?.content;
        if (!content) {
            throw new Error('No content in cortexComplete response');
        }

        // Strip markdown code fences if the LLM wrapped the JSON
        content = content
            .replace(/^```(?:json)?\s*\n?/, '')
            .replace(/\n?```\s*$/, '');

        return JSON.parse(content);
    } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        console.error(`[SYNTHESIS_ERROR] section=${sectionName} error=${msg}`);
        return null;
    }
}

// =============================================================================
// Empty section fallback
// =============================================================================

function emptySection(header: string): Record<string, unknown> {
    return {
        header,
        summary: 'Information currently unavailable.',
        details: [],
    };
}

// =============================================================================
// Node 1: Company Research (invoke COMPANY_RESEARCH sub-workflow — fail-fast)
// =============================================================================

async function companyResearch(state: typeof StateAnnotation.State) {
    const { sdk, accountId, accountName } = state;

    if (!accountId && !accountName) {
        throw new Error('PROSPECT_BRIEF requires account_id or account_name');
    }

    try {
        const crParams = {
            account_id: accountId,
            account_name: accountName,
        };
        console.log(
            `[DEBUG_INPUT] COMPANY_RESEARCH params: ${JSON.stringify(crParams)}`,
        );
        const response = await sdk.executeSubworkflow({
            workflowName: 'COMPANY_RESEARCH',
            params: crParams,
        });
        console.log(
            `[DEBUG_OUTPUT] COMPANY_RESEARCH raw response: ${JSON.stringify({ success: response.success, status: response.status, exitCode: response.exitCode, error: response.error, resultType: typeof response.result, resultKeys: response.result && typeof response.result === 'object' ? Object.keys(response.result as Record<string, unknown>) : null, stdoutLength: response.stdout?.length ?? 0, stderrLength: response.stderr?.length ?? 0 })}`,
        );
        console.log(
            `[DEBUG_OUTPUT] COMPANY_RESEARCH result: ${JSON.stringify(response.result)}`,
        );
        console.log(
            `[DEBUG_OUTPUT] COMPANY_RESEARCH stdout: ${JSON.stringify(response.stdout)}`,
        );
        if (response.stderr && response.stderr.length > 0) {
            console.log(
                `[DEBUG_OUTPUT] COMPANY_RESEARCH stderr: ${JSON.stringify(response.stderr)}`,
            );
        }

        const crResult = parseSubworkflowOutput(response);
        console.log(
            `[PROSPECT_BRIEF] COMPANY_RESEARCH parsed keys: ${Object.keys(crResult).join(', ')}`,
        );
        const [profileSummary, newsSummary] =
            extractContextForDownstream(crResult);

        console.log(
            `[PROSPECT_BRIEF] Extracted context: profile=${profileSummary.length} chars, news=${newsSummary.length} chars`,
        );

        return {
            companyResearchResult: crResult,
            companyProfileSummary: profileSummary,
            recentNewsSummary: newsSummary,
            errors: [],
        };
    } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        // Fail-fast: company research is required
        throw new Error(`Company research failed: ${msg}`);
    }
}

// =============================================================================
// Node 2: Parallel Research (VALUE_PROPOSITION ∥ CONTACT_INTELLIGENCE)
// =============================================================================

async function parallelResearch(state: typeof StateAnnotation.State) {
    const {
        sdk,
        accountId,
        accountName,
        companyProfileSummary,
        recentNewsSummary,
    } = state;
    const errors: string[] = [];

    // Launch both sub-workflows in parallel
    const vpParams = {
        account_id: accountId,
        account_name: accountName,
        company_profile: companyProfileSummary || '',
        account_recent_news: recentNewsSummary || '',
    };
    const ciParams = {
        account_id: accountId,
        account_name: accountName,
        limit: '10',
    };
    console.log(
        `[DEBUG_INPUT] VALUE_PROPOSITION params: ${JSON.stringify(vpParams)}`,
    );
    console.log(
        `[DEBUG_INPUT] CONTACT_INTELLIGENCE params: ${JSON.stringify(ciParams)}`,
    );
    const [vpResult, ciResult] = await Promise.allSettled([
        sdk.executeSubworkflow({
            workflowName: 'VALUE_PROPOSITION',
            params: vpParams,
        }),
        sdk.executeSubworkflow({
            workflowName: 'CONTACT_INTELLIGENCE',
            params: ciParams,
        }),
    ]);

    let valuePropositionResult: Record<string, unknown> | null = null;
    let contactIntelligenceResult: Record<string, unknown> | null = null;

    if (vpResult.status === 'fulfilled') {
        console.log(
            `[DEBUG_OUTPUT] VALUE_PROPOSITION raw response: ${JSON.stringify({ success: vpResult.value.success, status: vpResult.value.status, exitCode: vpResult.value.exitCode, error: vpResult.value.error, resultType: typeof vpResult.value.result, resultKeys: vpResult.value.result && typeof vpResult.value.result === 'object' ? Object.keys(vpResult.value.result as Record<string, unknown>) : null, stdoutLength: vpResult.value.stdout?.length ?? 0, stderrLength: vpResult.value.stderr?.length ?? 0 })}`,
        );
        console.log(
            `[DEBUG_OUTPUT] VALUE_PROPOSITION result: ${JSON.stringify(vpResult.value.result)}`,
        );
        console.log(
            `[DEBUG_OUTPUT] VALUE_PROPOSITION stdout: ${JSON.stringify(vpResult.value.stdout)}`,
        );
        if (vpResult.value.stderr && vpResult.value.stderr.length > 0) {
            console.log(
                `[DEBUG_OUTPUT] VALUE_PROPOSITION stderr: ${JSON.stringify(vpResult.value.stderr)}`,
            );
        }
        try {
            valuePropositionResult = parseSubworkflowOutput(vpResult.value);
            console.log(
                `[PROSPECT_BRIEF] VALUE_PROPOSITION parsed keys: ${Object.keys(valuePropositionResult).join(', ')}`,
            );
        } catch (err: unknown) {
            errors.push(
                `VALUE_PROPOSITION failed: ${err instanceof Error ? err.message : String(err)}`,
            );
        }
    } else {
        console.log(
            `[PROSPECT_BRIEF] VALUE_PROPOSITION rejected: ${vpResult.reason}`,
        );
        errors.push(`VALUE_PROPOSITION failed: ${vpResult.reason}`);
    }

    if (ciResult.status === 'fulfilled') {
        console.log(
            `[DEBUG_OUTPUT] CONTACT_INTELLIGENCE raw response: ${JSON.stringify({ success: ciResult.value.success, status: ciResult.value.status, exitCode: ciResult.value.exitCode, error: ciResult.value.error, resultType: typeof ciResult.value.result, resultKeys: ciResult.value.result && typeof ciResult.value.result === 'object' ? Object.keys(ciResult.value.result as Record<string, unknown>) : null, stdoutLength: ciResult.value.stdout?.length ?? 0, stderrLength: ciResult.value.stderr?.length ?? 0 })}`,
        );
        console.log(
            `[DEBUG_OUTPUT] CONTACT_INTELLIGENCE result: ${JSON.stringify(ciResult.value.result)}`,
        );
        console.log(
            `[DEBUG_OUTPUT] CONTACT_INTELLIGENCE stdout: ${JSON.stringify(ciResult.value.stdout)}`,
        );
        if (ciResult.value.stderr && ciResult.value.stderr.length > 0) {
            console.log(
                `[DEBUG_OUTPUT] CONTACT_INTELLIGENCE stderr: ${JSON.stringify(ciResult.value.stderr)}`,
            );
        }
        try {
            contactIntelligenceResult = parseSubworkflowOutput(ciResult.value);
            console.log(
                `[PROSPECT_BRIEF] CONTACT_INTELLIGENCE parsed keys: ${Object.keys(contactIntelligenceResult).join(', ')}`,
            );
        } catch (err: unknown) {
            errors.push(
                `CONTACT_INTELLIGENCE failed: ${err instanceof Error ? err.message : String(err)}`,
            );
        }
    } else {
        console.log(
            `[PROSPECT_BRIEF] CONTACT_INTELLIGENCE rejected: ${ciResult.reason}`,
        );
        errors.push(`CONTACT_INTELLIGENCE failed: ${ciResult.reason}`);
    }

    return {
        valuePropositionResult,
        contactIntelligenceResult,
        errors,
    };
}

// =============================================================================
// Node 3: Hybrid Synthesis (3 LLM sections + 3 mechanical sections)
// =============================================================================

async function hybridSynthesis(state: typeof StateAnnotation.State) {
    const {
        sdk,
        accountId,
        accountName,
        companyResearchResult,
        valuePropositionResult,
        contactIntelligenceResult,
    } = state;

    const cr = companyResearchResult || {};

    console.log(
        '[PROSPECT_BRIEF] Starting hybrid synthesis (3 mechanical + 3 LLM sections)...',
    );

    // === Mechanical sections ===
    const contactsSection = formatContactsSection(
        contactIntelligenceResult,
        accountName || 'Account',
    );
    const newsSection = formatNewsSection(companyResearchResult);

    // Value proposition: pass through mechanically
    let useCaseSection: Record<string, unknown> = emptySection(
        'Potential Snowflake Value Proposition',
    );
    if (valuePropositionResult) {
        const vpResponse = (valuePropositionResult.response || []) as Record<
            string,
            unknown
        >[];
        if (vpResponse.length > 0) {
            useCaseSection = {
                ...vpResponse[0],
                header: 'Potential Snowflake Value Proposition',
            };
        }
    }

    // === LLM sections (3 parallel calls) ===
    console.log('[PROSPECT_BRIEF] Starting 3 parallel LLM synthesis calls...');

    // Extract sections from response[] array (actual COMPANY_RESEARCH format)
    const companyProfileSection = findSection(cr, 'Company Profile');
    const financialSection = findSection(cr, 'Financial');
    const industrySection = findSection(cr, 'Industry');
    const competitorsSection = findSection(cr, 'Competitor');

    const companyInsightsInput = JSON.stringify({
        company_research_result: {
            company_profile: companyProfileSection || cr.company_profile || {},
            financial_overview: financialSection || cr.financial_overview || {},
            tech_stack: cr.tech_stack || {},
        },
    });

    const industryInsightsInput = JSON.stringify({
        company_research_result: {
            industry_overview: industrySection || cr.industry_overview || {},
        },
    });

    const competitorsInput = JSON.stringify({
        company_research_result: {
            competitors: competitorsSection || cr.competitors || {},
        },
    });

    const [companyInsights, industryInsights, competitors] = await Promise.all([
        synthesizeSection(
            sdk,
            'company_insights',
            `# COMPANY INSIGHTS SYNTHESIS\n\nGenerate the "Company Insights" section.\n\n## Input Data\n\n${companyInsightsInput}\n\n## Requirements\n- header: "Company Insights"\n- summary: 4-6 sentences (company name, industry, what they do, market position, differentiators). NO financial metrics.\n- details: 3 items: Products & Services, Financial Insights, Tech Stack\n\nReturn ONLY valid JSON.`,
            COMPANY_INSIGHTS_SCHEMA,
        ),

        synthesizeSection(
            sdk,
            'industry_insights',
            `# INDUSTRY INSIGHTS SYNTHESIS\n\nGenerate the "Industry Insights" section.\n\n## Input Data\n\n${industryInsightsInput}\n\n## Requirements\n- header: "Industry Insights"\n- summary: 3-4 sentences on industry, market size, growth drivers\n- details: 2 items: Trends & Challenges, Data & AI Use Cases\n\nReturn ONLY valid JSON.`,
            INDUSTRY_INSIGHTS_SCHEMA,
        ),

        synthesizeSection(
            sdk,
            'competitors',
            `# COMPETITORS SYNTHESIS\n\nGenerate the "Competitors" section.\n\n## Input Data\n\n${competitorsInput}\n\n## Requirements\n- header: "Competitors"\n- summary: 4 markdown bullets: • **[Name]:** 100-200 chars\n- details: [] (empty)\n\nReturn ONLY valid JSON.`,
            COMPETITORS_SCHEMA,
        ),
    ]);

    console.log(
        `[PROSPECT_BRIEF] LLM synthesis done: company_insights=${!!companyInsights}, industry_insights=${!!industryInsights}, competitors=${!!competitors}`,
    );

    // Assemble final 6-section response
    const response = [
        companyInsights || emptySection('Company Insights'),
        industryInsights || emptySection('Industry Insights'),
        newsSection,
        contactsSection,
        competitors || emptySection('Competitors'),
        useCaseSection,
    ];

    const finalResult = {
        workflow_name: 'PROSPECT_BRIEF',
        account_id: accountId,
        account_name: accountName,
        timestamp_utc: new Date().toISOString(),
        response,
    };

    return {
        finalResult,
        status: 'success',
        errors: [],
    };
}

// =============================================================================
// Graph: START -> company_research -> parallel_research -> synthesis -> END
// =============================================================================

const workflow = new StateGraph(StateAnnotation)
    .addNode('company_research', companyResearch)
    .addNode('parallel_research', parallelResearch)
    .addNode('synthesis', hybridSynthesis)
    .addEdge('__start__', 'company_research')
    .addEdge('company_research', 'parallel_research')
    .addEdge('parallel_research', 'synthesis')
    .addEdge('synthesis', '__end__');

const app = workflow.compile();

// =============================================================================
// Entry Point
// =============================================================================

export async function main(sdk: WorkflowSDK) {
    const accountId = sdk.getParameter('account_id') || '';
    const accountName = sdk.getParameter('account_name') || '';

    console.log(
        `[PROSPECT_BRIEF] Starting for account="${accountName}" (id=${accountId})`,
    );

    const result = await app.invoke({
        sdk,
        accountId,
        accountName,
        companyResearchResult: null,
        valuePropositionResult: null,
        contactIntelligenceResult: null,
        companyProfileSummary: '',
        recentNewsSummary: '',
        finalResult: null,
        status: 'pending',
        errors: [],
    });

    if (result.status === 'failed') {
        throw new Error(`Prospect brief failed: ${result.errors.join('; ')}`);
    }

    if (result.errors.length > 0) {
        console.log(
            `[PROSPECT_BRIEF] Completed with warnings: ${result.errors.join('; ')}`,
        );
    }

    console.log(
        `[PROSPECT_BRIEF] Completed successfully. Response has ${(result.finalResult as Record<string, unknown>)?.response ? ((result.finalResult as Record<string, unknown>).response as unknown[]).length : 0} sections.`,
    );
    console.log(JSON.stringify(result.finalResult));

    await sdk.close();

    return result.finalResult;
}
