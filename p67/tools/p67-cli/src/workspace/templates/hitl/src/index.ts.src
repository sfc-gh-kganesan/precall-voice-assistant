export async function main(sdk) {
    console.log('Starting interrupt workflow...');

    console.log('Step 1: Doing some initial work...');
    console.log('Step 1 complete.');

    console.log('Step 2: Requesting human approval...');
    const response = await sdk.interrupt(
        {
            type: 'approval',
            question: 'Do you approve this workflow to continue?',
            context: {
                items: [
                    'Updated API endpoints',
                    'New dashboard features',
                    'Bug fixes for user auth',
                ],
                version: '2.1.0',
                environment: 'production',
            },
        },
        { nodeId: 'approval_node' },
    );

    console.log('Received human response:', JSON.stringify(response));

    console.log('Step 3: Completing workflow with response...');
    console.log('Workflow finished successfully!');

    return { approved: response, status: 'done' };
}
