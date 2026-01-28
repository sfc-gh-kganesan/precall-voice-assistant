import * as fs from 'node:fs';
import * as path from 'node:path';
import type {
    Message,
    RunWorkflowMessage,
    SerializedP67Config,
    WorkflowErrorMessage,
} from '@controld/lib/runtime/schema.js';
import {
    MessageSchema,
    MessageType,
    makeThrowErrorMessage,
    WorkflowError,
} from '@controld/lib/runtime/schema.js';
import { WorkflowSDKImpl } from '@controld/lib/sdk-impl.js';
import type { P67Config } from '@p67/workflow-sdk';

// Track if we've started the workflow (RunWorkflow only processed once)
let workflowStarted = false;

function sendError(error: WorkflowError, message: string | Error | unknown) {
    if (message instanceof Error) {
        message = message.message;
    }

    if (typeof message !== 'string') {
        message = 'unknown error';
    }

    const m: WorkflowErrorMessage = makeThrowErrorMessage({
        error,
        message: message as string,
    });

    if (process.send) {
        process.send(m);
    }

    process.exit(1);
}

/**
 * Deserializes a SerializedP67Config (plain object) back to P67Config (with Map).
 */
function deserializeConfig(serialized: SerializedP67Config): P67Config {
    return {
        snowflakeConfig: new Map(Object.entries(serialized.snowflakeConfig)),
    };
}

async function handleMessage(message: Message) {
    const m = MessageSchema.safeParse(message);
    if (!m.success) {
        sendError(WorkflowError.MessageInvalidContents, m.error.toString());
        return;
    }

    // ResumeInterrupt messages are handled by the SDK's listener, not here
    if (m.data?.type === MessageType.ResumeInterrupt) {
        // SDK handles this via its setupResumeListener()
        return;
    }

    if (m.data?.type !== MessageType.RunWorkflow) {
        sendError(
            WorkflowError.MessageInvalidType,
            `Invalid message type: ${m.data?.type}`,
        );
        return;
    }

    // Prevent processing RunWorkflow multiple times
    if (workflowStarted) {
        console.warn('RunWorkflow already processed, ignoring duplicate');
        return;
    }
    workflowStarted = true;

    const data = m.data as RunWorkflowMessage;

    const scriptPath = path.resolve(data.dir, 'index.js');
    if (!fs.existsSync(scriptPath)) {
        sendError(
            WorkflowError.IndexScriptNotFound,
            `${scriptPath} does not exist, exiting.`,
        );
        return;
    }

    // biome-ignore lint/suspicious/noExplicitAny: Dynamic import
    let script: Record<string, any> = {};
    try {
        console.log(`loading script ${scriptPath}`);
        script = await import(scriptPath);
        console.log(`Loaded script!`);
    } catch (error) {
        sendError(WorkflowError.IndexScriptImportError, error);
        return;
    }

    if (typeof script.main !== 'function') {
        sendError(
            WorkflowError.IndexScriptInvalidContents,
            'Script does not export a main function',
        );
        return;
    }

    try {
        // Deserialize the config from the message and create the SDK
        const config = deserializeConfig(data.config);
        const sdk = new WorkflowSDKImpl(config);
        const result = await script.main(sdk);
        process.send?.({ type: 'result', data: result });
        process.exit(0);
    } catch (err) {
        sendError(WorkflowError.ExecutionError, err);
        return;
    }
}

process.on('message', handleMessage);
