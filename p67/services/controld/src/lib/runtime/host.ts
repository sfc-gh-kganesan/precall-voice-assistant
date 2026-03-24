/**
 * TypeScript workflow runtime host.
 *
 * Receives RunWorkflow messages via NDJSON on stdin, executes TypeScript
 * workflows, and communicates results back via NDJSON on stdout.
 *
 * stdout is reserved for IPC — all console.log/warn/info output is
 * redirected to stderr so it doesn't pollute the message stream.
 */

import { randomUUID } from 'node:crypto';
import * as fs from 'node:fs';
import * as path from 'node:path';
import * as readline from 'node:readline';
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

// ── Redirect console to stderr (stdout is the IPC channel) ──────────
const stderrWrite = (...args: unknown[]) => {
    process.stderr.write(`${args.map(String).join(' ')}\n`);
};
console.log = stderrWrite;
console.info = stderrWrite;
console.warn = stderrWrite;

// ── NDJSON helpers ──────────────────────────────────────────────────

function send(msg: unknown): Promise<void> {
    return new Promise<void>((resolve, reject) => {
        process.stdout.write(`${JSON.stringify(msg)}\n`, (err) => {
            if (err) reject(err);
            else resolve();
        });
    });
}

function onMessage(handler: (msg: unknown) => void): void {
    const rl = readline.createInterface({ input: process.stdin });
    rl.on('line', (line) => {
        if (!line.trim()) return;
        try {
            handler(JSON.parse(line));
        } catch {
            console.error(`[host] failed to parse message: ${line}`);
        }
    });
}

// ── Workflow state ──────────────────────────────────────────────────

let workflowStarted = false;

const pendingOAuthRequests = new Map<
    string,
    {
        resolve: (token: string) => void;
        reject: (error: Error) => void;
    }
>();

// ── OAuth ───────────────────────────────────────────────────────────

function createIPCOAuthTokenResolver(): (oauthRef: string) => Promise<string> {
    return (oauthRef: string): Promise<string> => {
        return new Promise((resolve, reject) => {
            const requestId = randomUUID();
            pendingOAuthRequests.set(requestId, { resolve, reject });

            const message = makeRequestOAuthTokenMessage({
                requestId,
                oauthRef,
            });

            send(message);

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

// ── Error handling ──────────────────────────────────────────────────

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

    send(m);

    process.exit(1);
}

// ── Config ──────────────────────────────────────────────────────────

function deserializeConfig(serialized: SerializedP67Config): P67Config {
    return {
        snowflakeConfig: new Map(Object.entries(serialized.snowflakeConfig)),
    };
}

// ── Message handler ─────────────────────────────────────────────────

async function handleMessage(message: Message) {
    const m = MessageSchema.safeParse(message);
    if (!m.success) {
        sendError(WorkflowError.MessageInvalidContents, m.error.toString());
        return;
    }

    // ResumeInterrupt messages are handled by the SDK's listener, not here
    if (m.data?.type === MessageType.ResumeInterrupt) {
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

    if (workflowStarted) {
        console.warn('RunWorkflow already processed, ignoring duplicate');
        return;
    }
    workflowStarted = true;

    const data = m.data as RunWorkflowMessage;

    // Inside the runner container the workflow is bind-mounted at /workflow.
    // The dir in the message is controld's internal path which doesn't exist here.
    const workflowDir = fs.existsSync('/workflow') ? '/workflow' : data.dir;

    const scriptPath = path.resolve(workflowDir, 'index.js');
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
        const config = deserializeConfig(data.config);

        // When SECRET_BACKEND=snowflake, secrets are mounted as env vars by SPCS.
        // Resolve the env var references into the config before creating the SDK.
        if (data.config.secretEnvMappings) {
            for (const [fieldPath, envVarName] of Object.entries(
                data.config.secretEnvMappings,
            )) {
                const value = process.env[envVarName];
                if (!value) {
                    console.warn(
                        `Warning: Secret env var ${envVarName} for ${fieldPath} is not set`,
                    );
                    continue;
                }

                // fieldPath is like "config.snowflake.token" or
                // "config.snowflake.parameters.MY_SECRET"
                // Inject resolved secret value into the snowflakeConfig map
                const parts = fieldPath.split('.');
                if (parts[0] === 'config' && parts.length >= 3) {
                    const configName = parts[1];
                    const configEntry = config.snowflakeConfig.get(configName);
                    if (configEntry && typeof configEntry === 'object') {
                        const entry = configEntry as Record<string, unknown>;
                        if (parts.length === 3) {
                            // config.<name>.<field> → direct field set
                            entry[parts[2]] = value;
                        } else if (
                            parts.length === 4 &&
                            parts[2] === 'parameters'
                        ) {
                            // config.<name>.parameters.<key> → nested set
                            if (!entry.parameters) {
                                entry.parameters = {};
                            }
                            (entry.parameters as Record<string, string>)[
                                parts[3]
                            ] = value;
                        }
                    }
                }
            }
        }

        const sdk = new WorkflowSDKImpl({
            config,
            oauthTokenResolver: createIPCOAuthTokenResolver(),
        });
        const result = await script.main(sdk);
        await send({ type: 'result', data: result });
        process.exit(0);
    } catch (err) {
        sendError(WorkflowError.ExecutionError, err);
        return;
    }
}

onMessage((msg) => handleMessage(msg as Message));
