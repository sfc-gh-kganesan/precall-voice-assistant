import type { WorkflowSDK } from './sdk';

export async function main(sdk: WorkflowSDK) {
    const response = await sdk.cortexCode({
        prompt: '$secret-code What is the secret code?',
        profile: 'p67-test',
        allowAllToolCalls: true,
        timeout: 120,
    });

    if (!response.success) {
        console.error(`CoCo failed: ${response.error}`);
        return { success: false, error: response.error };
    }

    const skillLoaded = response.output.includes('AURORA-BOREALIS-42');
    console.log(
        skillLoaded
            ? 'SUCCESS: bundled skill was loaded correctly'
            : 'FAIL: bundled skill was not loaded — secret code not found in output',
    );

    return {
        success: skillLoaded,
        output: response.output,
        skillLoaded,
    };
}
