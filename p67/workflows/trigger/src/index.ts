import { Annotation, StateGraph } from '@langchain/langgraph';
import type { WorkflowSDK } from './sdk';

function reverseString(s: string): string {
    return s.split('').reverse().join('');
}

// State: holds the raw params and the reversed output
const StateAnnotation = Annotation.Root({
    sdk: Annotation<WorkflowSDK>({
        reducer: (_, right) => right,
    }),
    id: Annotation<string>({
        reducer: (_, right) => right,
    }),
    name: Annotation<string>({
        reducer: (_, right) => right,
    }),
    email: Annotation<string>({
        reducer: (_, right) => right,
    }),
    reversedName: Annotation<string>({
        reducer: (_, right) => right,
    }),
    reversedEmail: Annotation<string>({
        reducer: (_, right) => right,
    }),
});

// Read params from the webhook trigger
async function readParams(state: typeof StateAnnotation.State) {
    const params = state.sdk.getParameters();
    console.log('Received params:', JSON.stringify(params));
    return {
        id: params.ID ?? '',
        name: params.NAME ?? '',
        email: params.EMAIL ?? '',
    };
}

// Reverse all string fields
async function reverseFields(state: typeof StateAnnotation.State) {
    const reversedName = reverseString(state.name);
    const reversedEmail = reverseString(state.email);
    console.log(`Reversed NAME: ${state.name} -> ${reversedName}`);
    console.log(`Reversed EMAIL: ${state.email} -> ${reversedEmail}`);
    return {
        reversedName,
        reversedEmail,
    };
}

// Build the graph
const workflow = new StateGraph(StateAnnotation)
    .addNode('readParams', readParams)
    .addNode('reverseFields', reverseFields)
    .addEdge('__start__', 'readParams')
    .addEdge('readParams', 'reverseFields')
    .addEdge('reverseFields', '__end__');

const app = workflow.compile();

export async function main(sdk: WorkflowSDK) {
    console.log('NEW_USER workflow triggered\n');

    const result = await app.invoke({
        sdk,
        id: '',
        name: '',
        email: '',
        reversedName: '',
        reversedEmail: '',
    });

    const output = {
        ID: result.id,
        NAME: result.name,
        EMAIL: result.email,
        REVERSED_NAME: result.reversedName,
        REVERSED_EMAIL: result.reversedEmail,
    };

    console.log('\n=== Result ===');
    console.log(JSON.stringify(output, null, 2));

    return output;
}
