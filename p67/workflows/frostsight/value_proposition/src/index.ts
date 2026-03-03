import { Annotation, StateGraph } from '@langchain/langgraph';
import type { WorkflowSDK } from './sdk';

// =============================================================================
// State Definition
// =============================================================================

const StateAnnotation = Annotation.Root({
    sdk: Annotation<WorkflowSDK>({
        reducer: (_, right) => right,
    }),
    accountId: Annotation<string>({
        reducer: (_, right) => right,
    }),
    accountName: Annotation<string>({
        reducer: (_, right) => right,
    }),
    companyProfile: Annotation<string>({
        reducer: (_, right) => right,
    }),
    accountRecentNews: Annotation<string>({
        reducer: (_, right) => right,
    }),
    // Intermediate
    recommenderOutput: Annotation<Record<string, unknown> | null>({
        reducer: (_, right) => right,
    }),
    recommendationText: Annotation<string>({
        reducer: (_, right) => right,
    }),
    // Output
    finalResult: Annotation<Record<string, unknown> | null>({
        reducer: (_, right) => right,
    }),
    status: Annotation<string>({
        reducer: (_, right) => right,
    }),
    errors: Annotation<string[]>({
        reducer: (left, right) => left.concat(right),
    }),
});

// =============================================================================
// Node 1: Call Recommender (USE_CASE_RECOMMENDER stored procedure)
// =============================================================================

async function callRecommender(state: typeof StateAnnotation.State) {
    const { sdk, accountId, companyProfile, accountRecentNews } = state;

    if (!accountId) {
        return {
            recommenderOutput: null,
            recommendationText: '',
            errors: ['account_id is required for value proposition generation'],
            status: 'failed',
        };
    }

    try {
        // Call RECO_FOR_PROSPECTING_SP(account_id, company_profile, recent_news)
        const result = await sdk.executeQuery({
            sqlText: `CALL RECO_FOR_PROSPECTING_SP(?, ?, ?)`,
            binds: [accountId, companyProfile || '', accountRecentNews || ''],
        });

        // Parse result - SP returns JSON with recommendation and summary_context
        const rows = result.rows || [];
        let recommendation = '';
        let summaryContext = '';
        let rawOutput: Record<string, unknown> = {};

        if (rows.length > 0) {
            const row = rows[0];
            // SP may return a single column with JSON string
            const firstVal = Object.values(row)[0];
            if (typeof firstVal === 'string') {
                try {
                    rawOutput = JSON.parse(firstVal);
                } catch {
                    rawOutput = { recommendation: firstVal };
                }
            } else if (typeof firstVal === 'object' && firstVal !== null) {
                rawOutput = firstVal as Record<string, unknown>;
            }

            recommendation = (rawOutput.recommendation as string) || '';
            summaryContext = (rawOutput.summary_context as string) || '';
        }

        return {
            recommenderOutput: {
                ...rawOutput,
                summary_context: summaryContext,
            },
            recommendationText: recommendation,
            errors: [],
        };
    } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        return {
            recommenderOutput: null,
            recommendationText: '',
            errors: [`USE_CASE_RECOMMENDER failed: ${msg}`],
            status: 'failed',
        };
    }
}

// =============================================================================
// Node 2: Format Output
// =============================================================================

async function formatOutput(state: typeof StateAnnotation.State) {
    const { sdk, accountName, recommendationText, recommenderOutput } = state;
    const name = accountName || 'the company';

    if (!recommendationText) {
        return {
            finalResult: {
                response: [
                    {
                        header: 'Use Case Recommendations',
                        summary:
                            'No use case recommendations available at this time.',
                        details: [],
                    },
                ],
                sources: [],
                raw_recommendation: '',
                summary_context: '',
            },
            status: 'no_results',
        };
    }

    // Generate concise summary via cortexComplete
    let generatedSummary = '';
    const summaryContext = (recommenderOutput?.summary_context as string) || '';

    try {
        const prompt = `Generate a concise 1-2 sentence summary (max 50 words) for the Snowflake value proposition.

**Account Context:**
${summaryContext || 'No context available'}

**Recommended Use Cases:**
${recommendationText.slice(0, 2000)}

**Instructions:**
Focus on what ${name} is trying to achieve or their key operational challenges, and how the recommended Snowflake capabilities directly address these needs.
DO NOT simply restate what the company does. Instead, emphasize their goals, initiatives, or pain points and the solution fit.

**Format:**
- 1-2 sentences only (50 words maximum)
- Lead with what they're trying to achieve or scale
- End with how Snowflake addresses this need

Return ONLY the summary text.`;

        const llmResult = await sdk.cortexComplete({
            model: 'claude-haiku-4-5',
            prompt,
            maxTokens: 500,
            temperature: 0.3,
        });

        generatedSummary = (
            typeof llmResult.text === 'string' ? llmResult.text : ''
        ).trim();
    } catch {
        // Fallback to summary_context or generic
    }

    const summary =
        generatedSummary ||
        summaryContext ||
        'Use case recommendations available below.';

    const details = [
        {
            header: '',
            content: recommendationText, // Pass raw markdown as-is
            attributes: [] as unknown[],
        },
    ];

    return {
        finalResult: {
            response: [
                {
                    header: 'Use Case Recommendations',
                    summary,
                    details,
                },
            ],
            sources: [],
            raw_recommendation: recommendationText,
            summary_context: summary,
        },
        status: 'success',
    };
}

// =============================================================================
// Graph: START -> call_recommender -> format_output -> END
// =============================================================================

const workflow = new StateGraph(StateAnnotation)
    .addNode('call_recommender', callRecommender)
    .addNode('format_output', formatOutput)
    .addEdge('__start__', 'call_recommender')
    .addEdge('call_recommender', 'format_output')
    .addEdge('format_output', '__end__');

const app = workflow.compile();

// =============================================================================
// Entry Point
// =============================================================================

export async function main(sdk: WorkflowSDK) {
    const accountId = sdk.getParameter('account_id') || '';
    const accountName = sdk.getParameter('account_name') || '';
    const companyProfile = sdk.getParameter('company_profile') || '';
    const accountRecentNews = sdk.getParameter('account_recent_news') || '';

    const result = await app.invoke({
        sdk,
        accountId,
        accountName,
        companyProfile,
        accountRecentNews,
        recommenderOutput: null,
        recommendationText: '',
        finalResult: null,
        status: 'pending',
        errors: [],
    });

    if (result.status === 'failed') {
        throw new Error(
            `Value proposition failed: ${result.errors.join('; ')}`,
        );
    }

    await sdk.close();

    return result.finalResult;
}
