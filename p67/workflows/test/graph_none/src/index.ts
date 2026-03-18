import type { WorkflowSDK } from './sdk';

export async function main(sdk: WorkflowSDK) {
    const message = sdk.getParameter('message') || 'ping';
    console.log(`[echo] Received: "${message}"`);

    return {
        echo: message,
        reversed: message.split('').reverse().join(''),
        length: message.length,
        timestamp: new Date().toISOString(),
    };
}
