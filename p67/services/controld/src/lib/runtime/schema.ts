import { P67ConfigValueSchema } from '@p67/workflow-sdk';
import { z } from 'zod';

// MessageType defines the full set of possible types of messages passed between Controld
// service and runtime host process.
enum MessageType {
    RunWorkflow = 'RunWorkflow',
    ThrowError = 'ThrowError',
}

// WorkflowError defines the set of possible errors that may be encountered
// durring workflow execution.
enum WorkflowError {
    ExecutionError = 'ExecutionError',
    IndexScriptImportError = 'IndexScriptImportError',
    IndexScriptInvalidContents = 'IndexScriptInvalidContents',
    IndexScriptNotFound = 'IndexScriptNotFound',
    ManifestLoadParseError = 'ManifestLoadParseError',
    ManifestNotFound = 'ManifestNotfound',
    MessageInvalidContents = 'MessageInvalidContents',
    MessageInvalidType = 'MessageInvalidType',
}

const BaseMessageSchema = z.object({
    type: z.nativeEnum(MessageType),
});

// Serialized config schema for IPC (Map serialized as Record)
const SerializedP67ConfigSchema = z.object({
    snowflakeConfig: z.record(z.string(), P67ConfigValueSchema),
    parameters: z.record(z.string(), z.string()),
});

export type SerializedP67Config = z.infer<typeof SerializedP67ConfigSchema>;

// RunWorkflowMessageSchema defines the messages which are sent from the Controld service
// process to the forked runtime process to invoke a Workflow. These messages includes
// information required for the runtime host to load and execute a workflow.
const RunWorkflowMessageSchema = BaseMessageSchema.extend({
    type: z.literal(MessageType.RunWorkflow),
    dir: z.string(),
    config: SerializedP67ConfigSchema,
});

// WorkflowErrorMessageSchema defines the messages which may be passed from the forked
// runtime process back to the parent Controld service process, in cases where the
// Workflow execution encounters an error.
const ThrowErrorMessageSchema = BaseMessageSchema.extend({
    type: z.literal(MessageType.ThrowError),
    error: z.nativeEnum(WorkflowError),
    message: z.string(),
});

// Union type for all messages
const MessageSchema = z.discriminatedUnion('type', [
    RunWorkflowMessageSchema,
    ThrowErrorMessageSchema,
]);

type RunWorkflowMessage = z.infer<typeof RunWorkflowMessageSchema>;
type ThrowErrorMessage = z.infer<typeof ThrowErrorMessageSchema>;
type Message = z.infer<typeof MessageSchema>;

function makeThrowErrorMessage(
    args: Omit<ThrowErrorMessage, 'type'>,
): ThrowErrorMessage {
    return {
        type: MessageType.ThrowError,
        ...args,
    };
}

function makeRunWorkflowMessage(
    args: Omit<RunWorkflowMessage, 'type'>,
): RunWorkflowMessage {
    return {
        type: MessageType.RunWorkflow,
        ...args,
    };
}

export {
    MessageSchema,
    RunWorkflowMessageSchema,
    ThrowErrorMessageSchema as WorkflowErrorMessageSchema,
    MessageType,
    WorkflowError,
    makeThrowErrorMessage,
    makeRunWorkflowMessage,
};

export type {
    ThrowErrorMessage as WorkflowErrorMessage,
    RunWorkflowMessage,
    Message,
};
