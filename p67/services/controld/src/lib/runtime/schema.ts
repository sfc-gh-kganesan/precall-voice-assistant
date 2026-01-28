import { P67ConfigValueSchema } from '@p67/workflow-sdk';
import { z } from 'zod';

// MessageType defines the full set of possible types of messages passed between Controld
// service and runtime host process.
enum MessageType {
    RunWorkflow = 'RunWorkflow',
    ThrowError = 'ThrowError',
    Interrupt = 'Interrupt',
    ResumeInterrupt = 'ResumeInterrupt',
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

// InterruptMessageSchema defines messages sent from the child process to the parent
// when a workflow calls sdk.interrupt() to pause and wait for human input.
const InterruptMessageSchema = BaseMessageSchema.extend({
    type: z.literal(MessageType.Interrupt),
    interruptId: z.string().uuid(),
    payload: z.unknown(),
    nodeId: z.string().optional(),
    timestamp: z.string(),
});

// ResumeInterruptMessageSchema defines messages sent from the parent to the child
// to resume a paused workflow with human-provided input.
const ResumeInterruptMessageSchema = BaseMessageSchema.extend({
    type: z.literal(MessageType.ResumeInterrupt),
    interruptId: z.string(),
    response: z.unknown(),
});

// Union type for all messages
const MessageSchema = z.discriminatedUnion('type', [
    RunWorkflowMessageSchema,
    ThrowErrorMessageSchema,
    InterruptMessageSchema,
    ResumeInterruptMessageSchema,
]);

type RunWorkflowMessage = z.infer<typeof RunWorkflowMessageSchema>;
type ThrowErrorMessage = z.infer<typeof ThrowErrorMessageSchema>;
type InterruptMessage = z.infer<typeof InterruptMessageSchema>;
type ResumeInterruptMessage = z.infer<typeof ResumeInterruptMessageSchema>;
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

function makeInterruptMessage(
    args: Omit<InterruptMessage, 'type'>,
): InterruptMessage {
    return {
        type: MessageType.Interrupt,
        ...args,
    };
}

function makeResumeInterruptMessage(
    args: Omit<ResumeInterruptMessage, 'type'>,
): ResumeInterruptMessage {
    return {
        type: MessageType.ResumeInterrupt,
        ...args,
    };
}

export {
    MessageSchema,
    RunWorkflowMessageSchema,
    ThrowErrorMessageSchema as WorkflowErrorMessageSchema,
    InterruptMessageSchema,
    ResumeInterruptMessageSchema,
    MessageType,
    WorkflowError,
    makeThrowErrorMessage,
    makeRunWorkflowMessage,
    makeInterruptMessage,
    makeResumeInterruptMessage,
};

export type {
    ThrowErrorMessage as WorkflowErrorMessage,
    RunWorkflowMessage,
    InterruptMessage,
    ResumeInterruptMessage,
    Message,
};
