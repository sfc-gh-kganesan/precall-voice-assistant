import { Annotation, StateGraph } from '@langchain/langgraph';
import type { WorkflowSDK } from './sdk';

const StateAnnotation = Annotation.Root({
    sdk: Annotation<WorkflowSDK>({ reducer: (_, r) => r }),
    reportTitle: Annotation<string>({ reducer: (_, r) => r }),
    reportBody: Annotation<string>({ reducer: (_, r) => r }),
    approved: Annotation<boolean>({ reducer: (_, r) => r }),
    approverComment: Annotation<string>({ reducer: (_, r) => r }),
    result: Annotation<Record<string, unknown> | null>({
        reducer: (_, r) => r,
    }),
});

async function prepareReport(state: typeof StateAnnotation.State) {
    const { reportTitle } = state;
    const body = `Auto-generated report for "${reportTitle}".\n\nThis report contains placeholder data for testing the HITL approval flow.\n\nGenerated at: ${new Date().toISOString()}`;
    console.log(`[prepare_report] Generated report: "${reportTitle}"`);
    return { reportBody: body };
}

async function requestApproval(state: typeof StateAnnotation.State) {
    const { sdk, reportTitle, reportBody } = state;

    console.log(`[request_approval] Requesting approval for: "${reportTitle}"`);

    const response = await sdk.interrupt<{
        approved: boolean;
        comment?: string;
    }>(
        {
            type: 'approval',
            question: `Do you approve publishing this report?`,
            context: { title: reportTitle, preview: reportBody.slice(0, 200) },
        },
        { nodeId: 'request_approval' },
    );

    const approved = response?.approved ?? false;
    const comment = response?.comment ?? '';
    console.log(`[request_approval] approved=${approved} comment="${comment}"`);

    return { approved, approverComment: comment };
}

async function finalizeReport(state: typeof StateAnnotation.State) {
    const { reportTitle, reportBody, approved, approverComment } = state;

    if (!approved) {
        console.log(`[finalize_report] Report rejected`);
        return {
            result: {
                status: 'rejected',
                title: reportTitle,
                reason: approverComment || 'No reason provided',
            },
        };
    }

    console.log(`[finalize_report] Report approved and published`);
    return {
        result: {
            status: 'published',
            title: reportTitle,
            body: reportBody,
            approverComment,
            publishedAt: new Date().toISOString(),
        },
    };
}

const workflow = new StateGraph(StateAnnotation)
    .addNode('prepare_report', prepareReport)
    .addNode('request_approval', requestApproval)
    .addNode('finalize_report', finalizeReport)
    .addEdge('__start__', 'prepare_report')
    .addEdge('prepare_report', 'request_approval')
    .addEdge('request_approval', 'finalize_report')
    .addEdge('finalize_report', '__end__');

const app = workflow.compile();

export async function main(sdk: WorkflowSDK) {
    const reportTitle = sdk.getParameter('report_title') || 'Untitled Report';

    const result = await app.invoke({
        sdk,
        reportTitle,
        reportBody: '',
        approved: false,
        approverComment: '',
        result: null,
    });

    return result.result;
}
