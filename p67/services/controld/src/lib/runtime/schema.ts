import { P67ConfigValueSchema } from '@p67/workflow-sdk';
import { z } from 'zod';

// MessageType defines the full set of possible types of messages passed between Controld
// service and runtime host process.
enum MessageType {
    RunWorkflow = 'RunWorkflow',
    ThrowError = 'ThrowError',
    Interrupt = 'Interrupt',
    ResumeInterrupt = 'ResumeInterrupt',
    RequestOAuthToken = 'RequestOAuthToken',
    OAuthTokenResponse = 'OAuthTokenResponse',
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
    /**
     * Maps config field paths to environment variable names containing
     * Snowflake SECRET values mounted by SPCS. Only present when
     * SECRET_BACKEND=snowflake. The host resolves these from process.env
     * before creating the SDK.
     */
    secretEnvMappings: z.record(z.string(), z.string()).optional(),
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

// Slack Block Kit schemas for rich notification messages
const SlackTextObjectSchema = z.object({
    type: z.enum(['plain_text', 'mrkdwn']),
    text: z.string(),
    emoji: z.boolean().optional(),
});

const SlackButtonElementSchema = z.object({
    type: z.literal('button'),
    text: z.object({
        type: z.literal('plain_text'),
        text: z.string(),
        emoji: z.boolean().optional(),
    }),
    action_id: z.string().optional(),
    value: z.string().optional(),
    style: z.enum(['primary', 'danger']).optional(),
    url: z.string().optional(),
});

const SlackHeaderBlockSchema = z.object({
    type: z.literal('header'),
    text: z.object({
        type: z.literal('plain_text'),
        text: z.string(),
        emoji: z.boolean().optional(),
    }),
    block_id: z.string().optional(),
});

const SlackSectionBlockSchema = z.object({
    type: z.literal('section'),
    text: SlackTextObjectSchema.optional(),
    fields: z.array(SlackTextObjectSchema).optional(),
    accessory: SlackButtonElementSchema.optional(),
    block_id: z.string().optional(),
});

const SlackDividerBlockSchema = z.object({
    type: z.literal('divider'),
    block_id: z.string().optional(),
});

const SlackActionsBlockSchema = z.object({
    type: z.literal('actions'),
    elements: z.array(SlackButtonElementSchema),
    block_id: z.string().optional(),
});

const SlackContextElementSchema = z.union([
    SlackTextObjectSchema,
    z.object({
        type: z.literal('image'),
        image_url: z.string(),
        alt_text: z.string(),
    }),
]);

const SlackContextBlockSchema = z.object({
    type: z.literal('context'),
    elements: z.array(SlackContextElementSchema),
    block_id: z.string().optional(),
});

const SlackImageBlockSchema = z.object({
    type: z.literal('image'),
    image_url: z.string(),
    alt_text: z.string(),
    title: z
        .object({
            type: z.literal('plain_text'),
            text: z.string(),
        })
        .optional(),
    block_id: z.string().optional(),
});

const SlackBlockSchema = z.discriminatedUnion('type', [
    SlackHeaderBlockSchema,
    SlackSectionBlockSchema,
    SlackDividerBlockSchema,
    SlackActionsBlockSchema,
    SlackContextBlockSchema,
    SlackImageBlockSchema,
]);

const InterruptButtonSchema = z.object({
    label: z.string(),
    value: z.string(),
    style: z.enum(['primary', 'danger']).optional(),
});

const ButtonPresetSchema = z.enum([
    'approve_reject',
    'yes_no',
    'continue_cancel',
]);

const SlackNotifyConfigSchema = z.object({
    type: z.literal('slack'),
    oauthRef: z.string(),
    recipient: z.union([z.literal('self'), z.string()]).optional(),
    text: z.string().optional(),
    buttons: z.array(InterruptButtonSchema).optional(),
    buttonPreset: ButtonPresetSchema.optional(),
    blocks: z.array(SlackBlockSchema).optional(),
});

const NotifyConfigSchema = SlackNotifyConfigSchema;

// InterruptMessageSchema defines messages sent from the child process to the parent
// when a workflow calls sdk.interrupt() to pause and wait for human input.
const InterruptMessageSchema = BaseMessageSchema.extend({
    type: z.literal(MessageType.Interrupt),
    interruptId: z.string().uuid(),
    payload: z.unknown(),
    nodeId: z.string().optional(),
    timestamp: z.string(),
    notify: NotifyConfigSchema.optional(),
});

// ResumeInterruptMessageSchema defines messages sent from the parent to the child
// to resume a paused workflow with human-provided input.
const ResumeInterruptMessageSchema = BaseMessageSchema.extend({
    type: z.literal(MessageType.ResumeInterrupt),
    interruptId: z.string(),
    response: z.unknown(),
});

// RequestOAuthTokenMessageSchema defines messages sent from the child process to the parent
// when a workflow needs to resolve an OAuth token via oauthRef.
const RequestOAuthTokenMessageSchema = BaseMessageSchema.extend({
    type: z.literal(MessageType.RequestOAuthToken),
    requestId: z.string().uuid(),
    oauthRef: z.string(),
});

// OAuthTokenResponseMessageSchema defines messages sent from the parent to the child
// with the resolved OAuth access token (or error).
const OAuthTokenResponseMessageSchema = BaseMessageSchema.extend({
    type: z.literal(MessageType.OAuthTokenResponse),
    requestId: z.string().uuid(),
    accessToken: z.string().optional(),
    error: z.string().optional(),
});

// Union type for all messages
const MessageSchema = z.discriminatedUnion('type', [
    RunWorkflowMessageSchema,
    ThrowErrorMessageSchema,
    InterruptMessageSchema,
    ResumeInterruptMessageSchema,
    RequestOAuthTokenMessageSchema,
    OAuthTokenResponseMessageSchema,
]);

type RunWorkflowMessage = z.infer<typeof RunWorkflowMessageSchema>;
type ThrowErrorMessage = z.infer<typeof ThrowErrorMessageSchema>;
type InterruptMessage = z.infer<typeof InterruptMessageSchema>;
type ResumeInterruptMessage = z.infer<typeof ResumeInterruptMessageSchema>;
type RequestOAuthTokenMessage = z.infer<typeof RequestOAuthTokenMessageSchema>;
type OAuthTokenResponseMessage = z.infer<
    typeof OAuthTokenResponseMessageSchema
>;
type Message = z.infer<typeof MessageSchema>;
type NotifyConfig = z.infer<typeof NotifyConfigSchema>;

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

function makeRequestOAuthTokenMessage(
    args: Omit<RequestOAuthTokenMessage, 'type'>,
): RequestOAuthTokenMessage {
    return {
        type: MessageType.RequestOAuthToken,
        ...args,
    };
}

function makeOAuthTokenResponseMessage(
    args: Omit<OAuthTokenResponseMessage, 'type'>,
): OAuthTokenResponseMessage {
    return {
        type: MessageType.OAuthTokenResponse,
        ...args,
    };
}

export {
    MessageSchema,
    RunWorkflowMessageSchema,
    ThrowErrorMessageSchema as WorkflowErrorMessageSchema,
    InterruptMessageSchema,
    ResumeInterruptMessageSchema,
    RequestOAuthTokenMessageSchema,
    OAuthTokenResponseMessageSchema,
    NotifyConfigSchema,
    MessageType,
    WorkflowError,
    makeThrowErrorMessage,
    makeRunWorkflowMessage,
    makeInterruptMessage,
    makeResumeInterruptMessage,
    makeRequestOAuthTokenMessage,
    makeOAuthTokenResponseMessage,
};

export type {
    ThrowErrorMessage as WorkflowErrorMessage,
    RunWorkflowMessage,
    InterruptMessage,
    ResumeInterruptMessage,
    RequestOAuthTokenMessage,
    OAuthTokenResponseMessage,
    NotifyConfig,
    Message,
};
