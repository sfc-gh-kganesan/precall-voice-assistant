import { Annotation, StateGraph } from '@langchain/langgraph';
import type { WorkflowSDK } from './sdk';

const StateAnnotation = Annotation.Root({
    sdk: Annotation<WorkflowSDK>({ reducer: (_, r) => r }),
    input: Annotation<string>({ reducer: (_, r) => r }),
    category: Annotation<string>({ reducer: (_, r) => r }),
    response: Annotation<string>({ reducer: (_, r) => r }),
    result: Annotation<Record<string, unknown> | null>({
        reducer: (_, r) => r,
    }),
});

async function classifyInput(state: typeof StateAnnotation.State) {
    const { input } = state;
    const lower = input.toLowerCase().trim();

    let category: string;
    if (lower.match(/^(hi|hello|hey|howdy|greetings)/)) {
        category = 'greeting';
    } else if (
        lower.endsWith('?') ||
        lower.startsWith('what') ||
        lower.startsWith('how') ||
        lower.startsWith('why') ||
        lower.startsWith('when') ||
        lower.startsWith('where') ||
        lower.startsWith('who')
    ) {
        category = 'question';
    } else {
        category = 'statement';
    }

    console.log(`[classify_input] "${input}" -> category="${category}"`);
    return { category };
}

function routeByCategory(state: typeof StateAnnotation.State): string {
    switch (state.category) {
        case 'greeting':
            return 'handle_greeting';
        case 'question':
            return 'handle_question';
        default:
            return 'handle_statement';
    }
}

async function handleGreeting(state: typeof StateAnnotation.State) {
    console.log(`[handle_greeting] Responding to greeting`);
    return { response: `Hello! You said: "${state.input}". Nice to meet you!` };
}

async function handleQuestion(state: typeof StateAnnotation.State) {
    console.log(`[handle_question] Responding to question`);
    return {
        response: `Great question! You asked: "${state.input}". I'd need more context to answer that properly.`,
    };
}

async function handleStatement(state: typeof StateAnnotation.State) {
    console.log(`[handle_statement] Responding to statement`);
    return {
        response: `Noted. You stated: "${state.input}". That's been recorded.`,
    };
}

async function formatResponse(state: typeof StateAnnotation.State) {
    return {
        result: {
            input: state.input,
            category: state.category,
            response: state.response,
            timestamp: new Date().toISOString(),
        },
    };
}

const workflow = new StateGraph(StateAnnotation)
    .addNode('classify_input', classifyInput)
    .addNode('handle_greeting', handleGreeting)
    .addNode('handle_question', handleQuestion)
    .addNode('handle_statement', handleStatement)
    .addNode('format_response', formatResponse)
    .addEdge('__start__', 'classify_input')
    .addConditionalEdges('classify_input', routeByCategory, {
        handle_greeting: 'handle_greeting',
        handle_question: 'handle_question',
        handle_statement: 'handle_statement',
    })
    .addEdge('handle_greeting', 'format_response')
    .addEdge('handle_question', 'format_response')
    .addEdge('handle_statement', 'format_response')
    .addEdge('format_response', '__end__');

const app = workflow.compile();

export async function main(sdk: WorkflowSDK) {
    const input = sdk.getParameter('input') || '';

    const result = await app.invoke({
        sdk,
        input,
        category: '',
        response: '',
        result: null,
    });

    return result.result;
}
