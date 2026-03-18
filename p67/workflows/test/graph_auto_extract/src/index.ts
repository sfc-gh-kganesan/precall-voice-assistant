import { Annotation, StateGraph } from '@langchain/langgraph';
import type { WorkflowSDK } from './sdk';

const StateAnnotation = Annotation.Root({
    sdk: Annotation<WorkflowSDK>({ reducer: (_, r) => r }),
    input: Annotation<string>({ reducer: (_, r) => r }),
    validated: Annotation<boolean>({ reducer: (_, r) => r }),
    processed: Annotation<string>({ reducer: (_, r) => r }),
    result: Annotation<Record<string, unknown> | null>({
        reducer: (_, r) => r,
    }),
});

async function validateInput(state: typeof StateAnnotation.State) {
    const { input } = state;
    const valid = typeof input === 'string' && input.trim().length > 0;
    console.log(`[validate_input] input="${input}" valid=${valid}`);
    return { validated: valid };
}

async function processData(state: typeof StateAnnotation.State) {
    const { input, validated } = state;
    if (!validated) {
        return { processed: '' };
    }
    const processed = input.trim().toUpperCase().split('').reverse().join('');
    console.log(`[process_data] "${input}" -> "${processed}"`);
    return { processed };
}

async function formatOutput(state: typeof StateAnnotation.State) {
    const { input, processed, validated } = state;
    return {
        result: {
            original: input,
            processed,
            valid: validated,
            timestamp: new Date().toISOString(),
        },
    };
}

const workflow = new StateGraph(StateAnnotation)
    .addNode('validate_input', validateInput)
    .addNode('process_data', processData)
    .addNode('format_output', formatOutput)
    .addEdge('__start__', 'validate_input')
    .addEdge('validate_input', 'process_data')
    .addEdge('process_data', 'format_output')
    .addEdge('format_output', '__end__');

const app = workflow.compile();

export async function main(sdk: WorkflowSDK) {
    const input = sdk.getParameter('input') || '';
    const result = await app.invoke({
        sdk,
        input,
        validated: false,
        processed: '',
        result: null,
    });
    return result.result;
}
