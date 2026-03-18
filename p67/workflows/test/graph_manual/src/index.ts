import type { WorkflowSDK } from './sdk';

export async function main(sdk: WorkflowSDK) {
    const text = sdk.getParameter('text') || '';
    const operation = sdk.getParameter('operation') || 'uppercase';

    console.log(`[parse_input] text="${text}" operation="${operation}"`);

    let transformed: string;
    switch (operation) {
        case 'lowercase':
            transformed = text.toLowerCase();
            break;
        case 'reverse':
            transformed = text.split('').reverse().join('');
            break;
        default:
            transformed = text.toUpperCase();
            break;
    }

    console.log(`[transform] "${text}" -> "${transformed}"`);

    const result = {
        original: text,
        operation,
        transformed,
        length: transformed.length,
        timestamp: new Date().toISOString(),
    };

    console.log(`[format_result] ${JSON.stringify(result)}`);
    return result;
}
