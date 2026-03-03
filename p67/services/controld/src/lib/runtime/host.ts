import { randomUUID } from 'node:crypto';
import * as fs from 'node:fs';
import * as path from 'node:path';
import type {
    Message,
    OAuthTokenResponseMessage,
    RunWorkflowMessage,
    SerializedP67Config,
    WorkflowErrorMessage,
} from '@controld/lib/runtime/schema.js';
import {
    MessageSchema,
    MessageType,
    makeRequestOAuthTokenMessage,
    makeThrowErrorMessage,
    WorkflowError,
} from '@controld/lib/runtime/schema.js';
import { WorkflowSDKImpl } from '@controld/lib/sdk-impl.js';
import type { P67Config } from '@p67/workflow-sdk';

// Track if we've started the workflow (RunWorkflow only processed once)
let workflowStarted = false;

// Pending OAuth token requests (requestId -> { resolve, reject })
const pendingOAuthRequests = new Map<
    string,
    {
        resolve: (token: string) => void;
        reject: (error: Error) => void;
    }
>();

/**
 * Create an OAuth token resolver that uses IPC to request tokens from the parent process
 */
function createIPCOAuthTokenResolver(): (oauthRef: string) => Promise<string> {
    return (oauthRef: string): Promise<string> => {
        return new Promise((resolve, reject) => {
            if (!process.send) {
                reject(
                    new Error(
                        'Cannot request OAuth token: not running as child process',
                    ),
                );
                return;
            }

            const requestId = randomUUID();
            pendingOAuthRequests.set(requestId, { resolve, reject });

            const message = makeRequestOAuthTokenMessage({
                requestId,
                oauthRef,
            });

            process.send(message);

            // Timeout after 30 seconds
            setTimeout(() => {
                if (pendingOAuthRequests.has(requestId)) {
                    pendingOAuthRequests.delete(requestId);
                    reject(
                        new Error(
                            `OAuth token request timed out for: ${oauthRef}`,
                        ),
                    );
                }
            }, 30000);
        });
    };
}

/**
 * Handle OAuthTokenResponse messages from the parent process
 */
function handleOAuthTokenResponse(message: OAuthTokenResponseMessage): void {
    const pending = pendingOAuthRequests.get(message.requestId);
    if (!pending) {
        console.warn(
            `Received OAuthTokenResponse for unknown requestId: ${message.requestId}`,
        );
        return;
    }

    pendingOAuthRequests.delete(message.requestId);

    if (message.error) {
        pending.reject(new Error(message.error));
    } else if (message.accessToken) {
        pending.resolve(message.accessToken);
    } else {
        pending.reject(
            new Error('Invalid OAuthTokenResponse: no token or error'),
        );
    }
}

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

    // OAuthTokenResponse messages are handled by the pending requests map
    if (m.data?.type === MessageType.OAuthTokenResponse) {
        handleOAuthTokenResponse(m.data as OAuthTokenResponseMessage);
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
        // Deserialize the config from the message and create the SDK with OAuth support
        const config = deserializeConfig(data.config);
        const sdk = new WorkflowSDKImpl({
            config,
            oauthTokenResolver: createIPCOAuthTokenResolver(),
        });
        const result = await script.main(sdk);
        // Wait for the IPC message to be flushed before exiting, otherwise
        // process.exit(0) can kill the process before the parent receives it.
        await new Promise<void>((resolve, reject) => {
            if (!process.send) {
                resolve();
                return;
            }
            process.send(
                { type: 'result', data: result },
                undefined,
                undefined,
                (err: Error | null) => {
                    if (err) reject(err);
                    else resolve();
                },
            );
        });
        process.exit(0);
    } catch (err) {
        sendError(WorkflowError.ExecutionError, err);
        return;
    }
}

process.on('message', handleMessage);
