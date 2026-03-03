import { Annotation, StateGraph } from '@langchain/langgraph';
import type { WorkflowSDK } from './sdk';

// =============================================================================
// Types
// =============================================================================

interface SectionData {
    data: Record<string, unknown>;
    timestamp: string;
    source: string;
    rawResponse?: string;
    extractionFailed?: boolean;
}

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
    // Section-level cached data
    sections: Annotation<Record<string, SectionData>>({
        reducer: (_, right) => right,
    }),
    threePData: Annotation<Record<string, unknown> | null>({
        reducer: (_, right) => right,
    }),
    // Cache check results
    staleSections: Annotation<string[]>({
        reducer: (_, right) => right,
    }),
    geminiCallsNeeded: Annotation<string[]>({
        reducer: (_, right) => right,
    }),
    threePStale: Annotation<boolean>({
        reducer: (_, right) => right,
    }),
    // Fetch results
    fetchResults: Annotation<Record<string, Record<string, unknown>>>({
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
// Section TTL Configuration (minutes)
// =============================================================================

const SECTION_TTL_MINUTES: Record<string, number> = {
    company_profile: 43200, // 30 days
    industry_overview: 43200, // 30 days
    competitors: 43200, // 30 days
    financial_overview: 10080, // 7 days
    tech_stack: 10080, // 7 days
    // TODO: recent_news requires a live search provider (e.g. Gemini with Google Search
    // Grounding, or a news API). Cortex Complete alone can't provide current news.
    // See sales-ai-platform's company_research for reference: it uses Vertex AI gemini-2.5-flash
    // with {"tools": [{"google_search": {}}]} to get grounded, real-time results.
    // recent_news: 1440,      // 1 day
};

const GEMINI_CALL_GROUPS: Record<string, string[]> = {
    monthly: ['company_profile', 'industry_overview', 'competitors'],
    weekly: ['financial_overview'],
    // daily: ["recent_news"],  // disabled — see TODO in SECTION_TTL_MINUTES
};

const THREE_P_SECTIONS = ['tech_stack'];

// =============================================================================
// Gemini Query Templates
// =============================================================================

const GEMINI_MONTHLY_QUERY = (
    name: string,
) => `Research ${name} comprehensively:

1. COMPANY PROFILE:
   - One-liner description (25-50 words) of what the company does
   - Main products and services (top 5 with brief descriptions)
   - Headquarters location (city, country)
   - Founding year
   - Company status (public/private)
   - Market position and key differentiators (2-4 points)
   - Current strategic focus areas
DO NOT research: employee count, annual revenue, or technology stack (provided separately).

2. INDUSTRY OVERVIEW:
   - Industry sector classification
   - Industry description (50-100 words)
   - Growth outlook (expanding, stable, contracting)
   - Major industry trends (4-5 key trends with explanations)
   - Data and AI use cases relevant to this industry (3-4 examples)

3. COMPETITORS:
   - Top 3-4 direct competitors
   - For each: company name, brief description, competitive positioning vs ${name}
   - Headquarters location of each competitor

Provide detailed, factual information. Focus on authoritative sources.`;

const GEMINI_WEEKLY_QUERY = (
    name: string,
) => `Research ${name}'s current financial status and market position:

If PUBLIC company:
- Current market capitalization (with date)
- Recent stock performance (30-day trend)
- Latest earnings call date and key takeaways

If PRIVATE company:
- Most recent funding round (date, amount, lead investors, valuation if disclosed)
- Total funding raised to date

IMPORTANT: Do NOT include annual revenue or employee count.
Provide source citations for all financial data.`;

// TODO: Daily news query disabled — requires live search provider (see SECTION_TTL_MINUTES)
// const GEMINI_DAILY_QUERY = (name: string) => `Find the most significant news about ${name} from the last 90 days:
//
// COMBINED SUMMARY (60-80 words):
// Synthesize the key themes, developments, and strategic moves.
//
// TOP 3 MOST IMPORTANT ARTICLES:
// For each: title, date (YYYY-MM-DD), publisher, brief summary (20-30 words), direct URL.
//
// Focus on: earnings, product launches, partnerships, acquisitions, leadership changes, strategic initiatives.
// DO NOT include: job postings, minor blog posts, marketing content.`;

// =============================================================================
// Extraction Prompts
// =============================================================================

const EXTRACTION_SYSTEM = `You are a precise data extraction assistant. Extract structured JSON from research text.
CRITICAL RULES:
1. Extract ONLY information explicitly stated in the text
2. Use null for missing fields - never invent data
3. Return ONLY valid JSON - no explanations, no markdown`;

// =============================================================================
// Node 1: Cache Check
// =============================================================================

async function cacheCheck(state: typeof StateAnnotation.State) {
    const sections = state.sections || {};
    const now = new Date();
    const staleSections: string[] = [];
    const geminiCallsNeeded = new Set<string>();

    for (const [sectionName, ttlMinutes] of Object.entries(
        SECTION_TTL_MINUTES,
    )) {
        const sectionData = sections[sectionName];

        if (!sectionData || typeof sectionData !== 'object') {
            staleSections.push(sectionName);
            continue;
        }

        const timestamp = sectionData.timestamp;
        const data = sectionData.data;

        if (!timestamp) {
            staleSections.push(sectionName);
            continue;
        }

        // Check for empty/failed data
        const isEmpty =
            !data ||
            (typeof data === 'object' && Object.keys(data).length === 0);
        if (isEmpty || sectionData.extractionFailed) {
            staleSections.push(sectionName);
            continue;
        }

        try {
            const sectionTime = new Date(timestamp);
            const ageMinutes = (now.getTime() - sectionTime.getTime()) / 60000;
            if (ageMinutes >= ttlMinutes) {
                staleSections.push(sectionName);
            }
        } catch {
            staleSections.push(sectionName);
        }
    }

    // Determine which Gemini calls are needed
    for (const [callType, sectionsInCall] of Object.entries(
        GEMINI_CALL_GROUPS,
    )) {
        if (sectionsInCall.some((s) => staleSections.includes(s))) {
            geminiCallsNeeded.add(callType);
        }
    }

    const threePStale = THREE_P_SECTIONS.some((s) => staleSections.includes(s));

    return {
        staleSections,
        geminiCallsNeeded: Array.from(geminiCallsNeeded),
        threePStale,
        errors: [],
    };
}

// =============================================================================
// Node 2: Conditional Fetch
// =============================================================================

async function conditionalFetch(state: typeof StateAnnotation.State) {
    const { sdk, accountId, accountName, geminiCallsNeeded, threePStale } =
        state;
    const callsNeeded = new Set(geminiCallsNeeded || []);

    const fetchResults: Record<string, Record<string, unknown>> = {};
    const errors: string[] = [];

    // Helper to research via Cortex Complete
    async function fetchViaCortex(
        query: string,
        callType: string,
    ): Promise<Record<string, unknown>> {
        try {
            const response = await sdk.cortexComplete({
                model: 'claude-4-sonnet',
                messages: [
                    {
                        role: 'system',
                        content:
                            'You are a thorough company research analyst. Provide detailed, factual information based on your knowledge. Be comprehensive but accurate — use null for anything you are not confident about.',
                    },
                    { role: 'user', content: query },
                ],
                maxTokens: 8192,
                temperature: 0,
            });

            if (!response.success) {
                throw new Error(
                    response.error || `cortexComplete returned success=false`,
                );
            }

            const text = response.choices?.[0]?.message?.content || '';
            return { raw_response: text, grounding_sources: [] };
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : String(err);
            throw new Error(`Cortex ${callType} failed: ${msg}`);
        }
    }

    // Build fetch promises
    const fetchPromises: Promise<void>[] = [];

    // 3P data
    if (threePStale && accountId) {
        fetchPromises.push(
            (async () => {
                try {
                    const result = await sdk.executeQueryReadOnly({
                        sql: `SELECT * FROM TABLE(GET_3P_DATA(?))`,
                        binds: [accountId],
                    });
                    fetchResults['3p_data'] = (result.rows || [])[0] || {};
                } catch (err: unknown) {
                    const msg =
                        err instanceof Error ? err.message : String(err);
                    errors.push(`3p_data failed: ${msg}`);
                    fetchResults['3p_data'] = { error: msg };
                }
            })(),
        );
    }

    // Gemini monthly
    if (callsNeeded.has('monthly') && accountName) {
        fetchPromises.push(
            (async () => {
                try {
                    fetchResults.gemini_monthly = await fetchViaCortex(
                        GEMINI_MONTHLY_QUERY(accountName),
                        'monthly',
                    );
                } catch (err: unknown) {
                    const msg =
                        err instanceof Error ? err.message : String(err);
                    errors.push(msg);
                    fetchResults.gemini_monthly = { error: msg };
                }
            })(),
        );
    }

    // Gemini weekly
    if (callsNeeded.has('weekly') && accountName) {
        fetchPromises.push(
            (async () => {
                try {
                    fetchResults.gemini_weekly = await fetchViaCortex(
                        GEMINI_WEEKLY_QUERY(accountName),
                        'weekly',
                    );
                } catch (err: unknown) {
                    const msg =
                        err instanceof Error ? err.message : String(err);
                    errors.push(msg);
                    fetchResults.gemini_weekly = { error: msg };
                }
            })(),
        );
    }

    // Daily news fetch disabled — requires live search provider
    // if (callsNeeded.has("daily") && accountName) {
    //     fetchPromises.push(
    //         (async () => {
    //             try {
    //                 fetchResults["gemini_daily"] = await fetchViaCortex(GEMINI_DAILY_QUERY(accountName), "daily");
    //             } catch (err: unknown) {
    //                 const msg = err instanceof Error ? err.message : String(err);
    //                 errors.push(msg);
    //                 fetchResults["gemini_daily"] = { error: msg };
    //             }
    //         })(),
    //     );
    // }

    if (!fetchPromises.length) {
        return { fetchResults: {}, errors: [] };
    }

    await Promise.all(fetchPromises);

    return { fetchResults, errors };
}

// =============================================================================
// Node 3: Extract and Merge
// =============================================================================

async function extractViaCortex(
    sdk: WorkflowSDK,
    systemPrompt: string,
    extractionPrompt: string,
    schema: Record<string, unknown>,
    maxTokens: number,
): Promise<Record<string, unknown>> {
    const schemaDescription = JSON.stringify(schema, null, 2);
    const result = await sdk.cortexComplete({
        model: 'claude-4-sonnet',
        messages: [
            {
                role: 'system',
                content: `${systemPrompt}\n\nReturn JSON matching this schema:\n${schemaDescription}`,
            },
            { role: 'user', content: extractionPrompt },
        ],
        maxTokens,
        temperature: 0,
    });

    if (!result.success) {
        throw new Error(result.error || 'cortexComplete extraction failed');
    }

    const text = result.choices?.[0]?.message?.content || '{}';
    // Strip markdown code fences if present
    const cleaned = text
        .replace(/^```(?:json)?\s*\n?/i, '')
        .replace(/\n?```\s*$/i, '')
        .trim();
    const parsed = JSON.parse(cleaned);
    return parsed || {};
}

async function extractAndMerge(state: typeof StateAnnotation.State) {
    const { sdk, accountName, fetchResults: fr } = state;
    const fetchResults = fr || {};
    const now = new Date().toISOString();

    const updatedSections: Record<string, SectionData> = {
        ...(state.sections || {}),
    };
    let threePData = state.threePData || {};
    const errors: string[] = [];

    // Update 3P data if fetched
    if (fetchResults['3p_data'] && !fetchResults['3p_data'].error) {
        threePData = fetchResults['3p_data'];
    }

    // Extract from Gemini monthly narrative
    if (fetchResults.gemini_monthly && !fetchResults.gemini_monthly.error) {
        const rawResponse = fetchResults.gemini_monthly.raw_response as string;
        if (rawResponse) {
            try {
                const extracted = await extractViaCortex(
                    sdk,
                    EXTRACTION_SYSTEM,
                    `Extract company profile, industry overview, and competitors from this research about ${accountName}.\n\n<research>\n${rawResponse}\n</research>`,
                    {
                        type: 'object',
                        properties: {
                            company_profile: {
                                type: 'object',
                                properties: {
                                    one_liner: {
                                        type: 'string',
                                        description:
                                            '25-50 word description of what the company does',
                                    },
                                    name: {
                                        type: 'string',
                                        description: 'Company name',
                                    },
                                    hq_city: {
                                        type: 'string',
                                        description:
                                            'Headquarters city and country',
                                    },
                                    founded_year: {
                                        type: 'number',
                                        description:
                                            'Year the company was founded',
                                    },
                                    status: {
                                        type: 'string',
                                        description: 'public or private',
                                    },
                                    market_position: {
                                        type: 'string',
                                        description:
                                            '2-4 sentences on market position and key differentiators',
                                    },
                                    products_and_services: {
                                        type: 'array',
                                        items: { type: 'string' },
                                        description: 'Top 5 products/services',
                                    },
                                    strategic_focus: {
                                        type: 'array',
                                        items: { type: 'string' },
                                        description:
                                            'Current strategic focus areas',
                                    },
                                },
                                required: [
                                    'one_liner',
                                    'name',
                                    'hq_city',
                                    'founded_year',
                                    'status',
                                    'market_position',
                                ],
                            },
                            industry_overview: {
                                type: 'object',
                                properties: {
                                    industry_sector: {
                                        type: 'string',
                                        description:
                                            'Industry sector classification',
                                    },
                                    industry_description: {
                                        type: 'string',
                                        description:
                                            '50-100 word industry description',
                                    },
                                    growth_outlook: {
                                        type: 'string',
                                        description:
                                            'expanding, stable, or contracting',
                                    },
                                    major_trends: {
                                        type: 'array',
                                        items: { type: 'string' },
                                        description: '4-5 key industry trends',
                                    },
                                    ai_use_cases: {
                                        type: 'array',
                                        items: { type: 'string' },
                                        description:
                                            '3-4 data/AI use cases for this industry',
                                    },
                                },
                                required: [
                                    'industry_sector',
                                    'industry_description',
                                    'growth_outlook',
                                ],
                            },
                            competitors: {
                                type: 'array',
                                items: {
                                    type: 'object',
                                    properties: {
                                        company_name: {
                                            type: 'string',
                                            description:
                                                'Competitor company name',
                                        },
                                        description_and_competitive_position_against_company:
                                            {
                                                type: 'string',
                                                description:
                                                    'Brief description and how they compete',
                                            },
                                        hq_city: {
                                            type: 'string',
                                            description:
                                                'Headquarters city and country',
                                        },
                                    },
                                    required: [
                                        'company_name',
                                        'description_and_competitive_position_against_company',
                                    ],
                                },
                                description: 'Top 3-4 direct competitors',
                            },
                        },
                        required: [
                            'company_profile',
                            'industry_overview',
                            'competitors',
                        ],
                    },
                    4096,
                );

                if (extracted.company_profile) {
                    updatedSections.company_profile = {
                        data: extracted.company_profile as Record<
                            string,
                            unknown
                        >,
                        timestamp: now,
                        source: 'gemini_monthly',
                    };
                }
                if (extracted.industry_overview) {
                    updatedSections.industry_overview = {
                        data: extracted.industry_overview as Record<
                            string,
                            unknown
                        >,
                        timestamp: now,
                        source: 'gemini_monthly',
                    };
                }
                if (extracted.competitors) {
                    updatedSections.competitors = {
                        data: { competitors: extracted.competitors },
                        timestamp: now,
                        source: 'gemini_monthly',
                    };
                }

                const groundingSources =
                    (fetchResults.gemini_monthly
                        .grounding_sources as unknown[]) || [];
                updatedSections._grounding_sources = {
                    data: { sources: groundingSources },
                    timestamp: now,
                    source: 'gemini_monthly',
                };
            } catch (err: unknown) {
                const msg = err instanceof Error ? err.message : String(err);
                errors.push(`monthly extraction failed: ${msg}`);
                updatedSections.company_profile = {
                    data: {},
                    timestamp: now,
                    source: 'gemini_monthly',
                    rawResponse: rawResponse.slice(0, 2000),
                    extractionFailed: true,
                };
            }
        }
    }

    // Extract from Gemini weekly narrative
    if (fetchResults.gemini_weekly && !fetchResults.gemini_weekly.error) {
        const rawResponse = fetchResults.gemini_weekly.raw_response as string;
        if (rawResponse) {
            try {
                const extracted = await extractViaCortex(
                    sdk,
                    EXTRACTION_SYSTEM,
                    `Extract financial information from this research.\n\n<research>\n${rawResponse}\n</research>`,
                    {
                        type: 'object',
                        properties: {
                            financial_overview: {
                                type: 'object',
                                properties: {
                                    market_cap_or_last_funding_round_summary: {
                                        type: 'string',
                                        description:
                                            'For public: market cap and recent stock trend. For private: last funding round details. 1-2 sentences.',
                                    },
                                    is_public: {
                                        type: 'boolean',
                                        description:
                                            'Whether the company is publicly traded',
                                    },
                                    market_cap: {
                                        type: 'string',
                                        description:
                                            'Market capitalization if public, null if private',
                                    },
                                    stock_trend_30d: {
                                        type: 'string',
                                        description:
                                            '30-day stock trend summary if public',
                                    },
                                    latest_earnings_date: {
                                        type: 'string',
                                        description:
                                            'Latest earnings call date if public',
                                    },
                                    latest_earnings_takeaways: {
                                        type: 'string',
                                        description:
                                            'Key takeaways from latest earnings if public',
                                    },
                                    last_funding_round: {
                                        type: 'string',
                                        description:
                                            'Most recent funding round details if private',
                                    },
                                    total_funding: {
                                        type: 'string',
                                        description:
                                            'Total funding raised if private',
                                    },
                                },
                                required: [
                                    'market_cap_or_last_funding_round_summary',
                                ],
                            },
                        },
                        required: ['financial_overview'],
                    },
                    2048,
                );
                if (extracted.financial_overview) {
                    updatedSections.financial_overview = {
                        data: extracted.financial_overview as Record<
                            string,
                            unknown
                        >,
                        timestamp: now,
                        source: 'gemini_weekly',
                    };
                }
            } catch (err: unknown) {
                const msg = err instanceof Error ? err.message : String(err);
                errors.push(`weekly extraction failed: ${msg}`);
            }
        }
    }

    // Daily news extraction disabled — requires live search provider
    // if (fetchResults["gemini_daily"] && !fetchResults["gemini_daily"].error) {
    //     const rawResponse = fetchResults["gemini_daily"].raw_response as string;
    //     if (rawResponse) {
    //         try {
    //             const extracted = await extractViaCortex(
    //                 sdk, EXTRACTION_SYSTEM,
    //                 `Extract recent news from this research.\n\n<research>\n${rawResponse}\n</research>`,
    //                 { ... },
    //                 2048,
    //             );
    //             if (extracted.recent_news) {
    //                 updatedSections["recent_news"] = { data: extracted.recent_news, timestamp: now, source: "gemini_daily" };
    //             }
    //         } catch (err: unknown) {
    //             const msg = err instanceof Error ? err.message : String(err);
    //             errors.push(`daily extraction failed: ${msg}`);
    //         }
    //     }
    // }

    // Update tech_stack from 3P data
    if (threePData && Object.keys(threePData).length) {
        const techStack =
            (threePData as Record<string, unknown>).tech_stack || [];
        const sumbleUrl =
            (threePData as Record<string, unknown>).sumble_profile_url || null;
        updatedSections.tech_stack = {
            data: {
                technologies: techStack,
                source: 'verified_3p_data',
                sumble_profile_url: sumbleUrl,
            },
            timestamp: now,
            source: '3p_data',
        };
    }

    // Build final result from all sections
    const finalResult = buildFinalResult(
        updatedSections,
        threePData as Record<string, unknown>,
        accountName,
    );
    const hasProfile = Boolean(
        updatedSections.company_profile?.data &&
            Object.keys(updatedSections.company_profile.data).length,
    );

    return {
        sections: updatedSections,
        threePData,
        finalResult,
        status: hasProfile ? 'success' : 'partial',
        errors,
    };
}

// =============================================================================
// Build Final Result
// =============================================================================

function buildFinalResult(
    sections: Record<string, SectionData>,
    threePData: Record<string, unknown>,
    accountName: string | undefined,
): Record<string, unknown> {
    const response: Record<string, unknown>[] = [];

    // Company Profile section
    const profile = sections.company_profile?.data || {};
    if (Object.keys(profile).length) {
        const attributes: Record<string, unknown>[] = [];
        if (profile.hq_city)
            attributes.push({
                label: 'Headquarters',
                value: profile.hq_city,
                type: 'string',
            });
        if (profile.founded_year)
            attributes.push({
                label: 'Founded',
                value: String(profile.founded_year),
                type: 'string',
            });
        if (profile.status)
            attributes.push({
                label: 'Status',
                value: profile.status,
                type: 'string',
            });
        if (threePData?.number_of_employees)
            attributes.push({
                label: 'Employees',
                value: String(threePData.number_of_employees),
                type: 'string',
            });
        if (threePData?.annual_revenue)
            attributes.push({
                label: 'Revenue',
                value: String(threePData.annual_revenue),
                type: 'string',
            });

        response.push({
            header: 'Company Profile',
            summary:
                profile.one_liner || `Research on ${accountName || 'company'}`,
            details: [
                {
                    header:
                        accountName || (profile.name as string) || 'Company',
                    content: profile.market_position || null,
                    attributes,
                },
            ],
        });
    }

    // Industry Overview section
    const industry = sections.industry_overview?.data || {};
    if (Object.keys(industry).length) {
        response.push({
            header: 'Industry Overview',
            summary: industry.industry_description || null,
            details: [],
        });
    }

    // Financial Overview section
    const financial = sections.financial_overview?.data || {};
    if (Object.keys(financial).length) {
        response.push({
            header: 'Financial Overview',
            summary: financial.market_cap_or_last_funding_round_summary || null,
            details: [],
        });
    }

    // Recent News section — disabled, requires live search provider
    // const news = sections.recent_news?.data || {};
    // if (Object.keys(news).length) {
    //     const articles = (news.articles as Record<string, unknown>[]) || [];
    //     response.push({
    //         header: "Recent News",
    //         summary: (news.combined_summary_all_news_articles as string) || null,
    //         details: articles.map((a) => ({
    //             header: a.title || "Article",
    //             content: a.source_publisher || null,
    //             attributes: [
    //                 ...(a.date_iso ? [{ label: "Date", value: a.date_iso, type: "string" }] : []),
    //                 ...(a.source_url ? [{ label: "URL", value: a.source_url, type: "link" }] : []),
    //             ],
    //         })),
    //     });
    // }

    // Competitors section
    const competitorsSection = sections.competitors?.data || {};
    const competitors =
        (competitorsSection.competitors as Record<string, unknown>[]) || [];
    if (competitors.length) {
        response.push({
            header: 'Competitors',
            summary: `${competitors.length} key competitors identified`,
            details: competitors.map((c) => ({
                header: c.company_name || 'Competitor',
                content:
                    c.description_and_competitive_position_against_company ||
                    null,
                attributes: c.hq_city
                    ? [{ label: 'HQ', value: c.hq_city, type: 'string' }]
                    : [],
            })),
        });
    }

    // Tech Stack section
    const techStack = sections.tech_stack?.data || {};
    const technologies = (techStack.technologies as string[]) || [];
    if (technologies.length) {
        response.push({
            header: 'Technology Stack',
            summary: `${technologies.length} technologies identified from verified third-party data`,
            details: technologies.map((t) => ({
                header: t,
                content: null,
                attributes: [],
            })),
        });
    }

    // Sources
    const groundingSources = sections._grounding_sources?.data?.sources || [];

    return { response, sources: groundingSources };
}

// =============================================================================
// Graph: START -> cache_check -> conditional_fetch -> extract_and_merge -> END
// =============================================================================

const workflow = new StateGraph(StateAnnotation)
    .addNode('cache_check', cacheCheck)
    .addNode('conditional_fetch', conditionalFetch)
    .addNode('extract_and_merge', extractAndMerge)
    .addEdge('__start__', 'cache_check')
    .addEdge('cache_check', 'conditional_fetch')
    .addEdge('conditional_fetch', 'extract_and_merge')
    .addEdge('extract_and_merge', '__end__');

const app = workflow.compile();

// =============================================================================
// Entry Point
// =============================================================================

export async function main(sdk: WorkflowSDK) {
    const params = sdk.getParameters();
    const accountName = params.account_name || '';
    const accountId = params.account_id || '';

    if (!accountName) {
        throw new Error("Parameter 'account_name' is required");
    }

    const result = await app.invoke({
        sdk,
        accountId,
        accountName,
        sections: {},
        threePData: null,
        staleSections: [],
        geminiCallsNeeded: [],
        threePStale: false,
        fetchResults: {},
        finalResult: null,
        status: 'pending',
        errors: [],
    });

    if (result.errors?.length) {
        console.error(`Workflow errors: ${result.errors.join('; ')}`);
    }
    console.log(`Workflow status: ${result.status}`);
    console.log(
        `Stale sections: ${result.staleSections?.join(', ') || 'none'}`,
    );
    console.log(
        `Gemini calls needed: ${result.geminiCallsNeeded?.join(', ') || 'none'}`,
    );
    console.log(
        `Fetch results keys: ${Object.keys(result.fetchResults || {}).join(', ') || 'none'}`,
    );

    if (result.status === 'failed') {
        throw new Error(`Company research failed: ${result.errors.join('; ')}`);
    }

    await sdk.close();

    return result.finalResult;
}
