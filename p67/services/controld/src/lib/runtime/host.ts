import * as fs from 'node:fs';
import * as path from 'node:path';
import { type Manifest, parseManifest } from '@controld/lib/manifest.js';
import type {
    Message,
    RunWorkflowMessage,
    WorkflowErrorMessage,
} from '@controld/lib/runtime/schema.js';
import {
    MessageSchema,
    MessageType,
    makeThrowErrorMessage,
    WorkflowError,
} from '@controld/lib/runtime/schema.js';
import { hydrateConfig, WorkflowSDKImpl } from '@controld/lib/sdk-impl.js';
import { ValueManager } from '@controld/lib/value-manager.js';

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

async function handleMessage(message: Message) {
    const m = MessageSchema.safeParse(message);
    if (!m.success) {
        sendError(WorkflowError.MessageInvalidContents, m.error.toString());
        return;
    }

    if (m.data?.type !== MessageType.RunWorkflow) {
        sendError(
            WorkflowError.MessageInvalidType,
            `Invalid message type: ${m.data?.type}`,
        );
        return;
    }

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

    const manifestPath = path.resolve(data.dir, 'manifest.yaml');
    if (!fs.existsSync(manifestPath)) {
        sendError(
            WorkflowError.ManifestNotFound,
            `${manifestPath} does not exist`,
        );
    }

    let manifestStr = '';
    try {
        manifestStr = await fs.promises.readFile(manifestPath, 'utf-8');
    } catch (err) {
        sendError(WorkflowError.ManifestLoadParseError, err);
        return;
    }

    let manifest: Manifest;
    try {
        manifest = parseManifest(manifestStr);
    } catch (err) {
        sendError(WorkflowError.ManifestLoadParseError, err);
        return;
    }

    // TODO: Use a real thing here.
    const valueManager = new ValueManager();

    try {
        const config = await hydrateConfig(manifest, valueManager);
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
