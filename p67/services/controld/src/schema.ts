import { z } from 'zod';

export const HealthResponseSchema = z.object({
    status: z.string(),
    timestamp: z.string(),
    localStoragePath: z.string(),
});

export const ErrorResponseSchema = z.object({
    error: z.string(),
    message: z.string().optional(),
});

export const WorkflowCreateResponseSchema = z.object({
    workflowId: z.string(),
    isNewVersion: z.boolean().optional(),
    versionNumber: z.number().optional(),
});

export const WorkflowSchema = z.object({
    workflowId: z.string(),
    name: z.string().nullable(),
    owner: z.string(),
    createdAt: z.string(),
    updatedAt: z.string(),
    visibility: z.string(),
    versionCount: z.number().optional(),
});

export const WorkflowListResponseSchema = z.object({
    workflows: z.array(WorkflowSchema),
});

export const RunStatusSchema = z.enum([
    'running',
    'completed',
    'interrupted',
    'failed',
]);

export const PendingInterruptSchema = z.object({
    interruptId: z.string(),
    value: z.unknown(),
    timestamp: z.string(),
    nodeId: z.string().optional(),
});

export const WorkflowRunResponseSchema = z.object({
    exitCode: z.number(),
    stdout: z.array(z.string()),
    stderr: z.array(z.string()),
    log: z.array(z.string()),
    success: z.boolean(),
    errors: z.array(
        z.object({
            error: z.string(),
            message: z.string(),
        }),
    ),
    status: RunStatusSchema.optional(),
    pendingInterrupt: PendingInterruptSchema.optional(),
    runId: z.string().optional(),
    result: z.unknown().optional(),
});

export const WorkflowRunAcceptedSchema = z.object({
    runId: z.string(),
    status: z.literal('running'),
});

export type WorkflowRunAccepted = z.infer<typeof WorkflowRunAcceptedSchema>;

export const WorkflowRunStatusParamsSchema = z.object({
    runId: z.string(),
});

export const WorkflowRunStatusResponseSchema = z.object({
    runId: z.string(),
    status: RunStatusSchema,
    exitCode: z.number().nullable(),
    result: z.unknown().optional(),
    stdout: z.array(z.string()).optional(),
    stderr: z.array(z.string()).optional(),
    log: z.array(z.string()).optional(),
    errors: z
        .array(
            z.object({
                error: z.string(),
                message: z.string(),
            }),
        )
        .optional(),
    pendingInterrupt: PendingInterruptSchema.optional(),
});

export type WorkflowRunStatusResponse = z.infer<
    typeof WorkflowRunStatusResponseSchema
>;

export const WorkflowRunParamsSchema = z.object({
    workflowId: z.string(),
});

export const WorkflowVisibilityParamsSchema = z.object({
    workflowId: z.string(),
});

export const WorkflowVisibilityBodySchema = z.object({
    visibility: z.enum(['Private', 'Public']),
});

export const WorkflowVisibilityResponseSchema = z.object({
    workflowId: z.string(),
    visibility: z.enum(['Private', 'Public']),
});

export type WorkflowVisibilityBody = z.infer<
    typeof WorkflowVisibilityBodySchema
>;
export type WorkflowVisibilityResponse = z.infer<
    typeof WorkflowVisibilityResponseSchema
>;

export const WorkflowRunBodySchema = z
    .object({
        params: z.record(z.string(), z.string()).optional(),
    })
    .optional();

export type WorkflowRunBody = z.infer<typeof WorkflowRunBodySchema>;

// Manifest param value - can be a literal value or reference
export const ManifestParamValueSchema = z.object({
    value: z.string().optional(),
    valueRef: z.string().optional(),
    secretRef: z.string().optional(),
    oauthRef: z.string().optional(),
    required: z.boolean().optional(),
    description: z.string().optional(),
});

export const WorkflowManifestResponseSchema = z.object({
    params: z.record(z.string(), ManifestParamValueSchema).optional(),
});

export const WorkflowGraphNodeSchema = z.object({
    id: z.string(),
    type: z.string(),
    name: z.string(),
    description: z.string().optional(),
    action_name: z.string().optional(),
    subgraph_name: z.string().optional(),
    question: z.string().optional(),
    human_role: z.string().optional(),
    human_task: z.string().optional(),
    end_type: z.string().optional(),
    branches: z
        .array(z.object({ label: z.string(), condition: z.string() }))
        .optional(),
});

export const WorkflowGraphEdgeSchema = z.object({
    id: z.string(),
    from_node: z.string(),
    to_node: z.string(),
    label: z.string().optional(),
});

export const WorkflowGraphResponseSchema = z.object({
    graph: z
        .object({
            name: z.string().optional(),
            description: z.string().optional(),
            nodes: z.array(WorkflowGraphNodeSchema),
            edges: z.array(WorkflowGraphEdgeSchema),
            variables: z
                .array(
                    z.object({
                        name: z.string(),
                        data_type: z.string(),
                        description: z.string(),
                    }),
                )
                .optional(),
        })
        .nullable(),
});

export type WorkflowManifestResponse = z.infer<
    typeof WorkflowManifestResponseSchema
>;

export type HealthResponse = z.infer<typeof HealthResponseSchema>;
export type ErrorResponse = z.infer<typeof ErrorResponseSchema>;

// OAuth Schemas
export const OAuthCallbackQuerySchema = z.object({
    code: z.string().optional(),
    error: z.string().optional(),
    error_description: z.string().optional(),
});

export const OAuthCallbackResponse = z.object({
    error: z.string().optional(),
    name: z.string().optional(),
    email: z.string().optional(),
    picture: z.string().optional(),
});

export const GoogleTokenResponseSchema = z.object({
    access_token: z.string(),
    expires_in: z.number(),
    scope: z.string(),
    token_type: z.string(),
    id_token: z.string().optional(),
});

export const GoogleUserInfoSchema = z.object({
    sub: z.string().optional(),
    name: z.string(),
    email: z.string(),
    picture: z.string(),
    email_verified: z.boolean().optional(),
});

export type OAuthCallbackQuery = z.infer<typeof OAuthCallbackQuerySchema>;
export type GoogleTokenResponse = z.infer<typeof GoogleTokenResponseSchema>;
export type GoogleUserInfo = z.infer<typeof GoogleUserInfoSchema>;

// Whoami Schema
export const WhoamiResponseSchema = z.object({
    id: z.string(),
    snowflakeUser: z.string(),
});

export type WhoamiResponse = z.infer<typeof WhoamiResponseSchema>;

// Secret Schemas
// Workflow Delete Schemas
export const WorkflowDeleteParamsSchema = z.object({
    workflowId: z.string(),
});

export const WorkflowDeleteResponseSchema = z.object({
    deleted: z.boolean(),
    workflowId: z.string(),
});

export type WorkflowDeleteResponse = z.infer<
    typeof WorkflowDeleteResponseSchema
>;

export const SecretTypeSchema = z.enum(['Secret', 'OAuth']);

export const SecretSaveBodySchema = z.object({
    name: z.string().min(1),
    secret: z.string().min(1),
    type: SecretTypeSchema.optional().default('Secret'),
});

export const SecretSaveResponseSchema = z.object({
    name: z.string(),
    created: z.boolean(),
});

export const SecretSchema = z.object({
    name: z.string(),
    type: SecretTypeSchema,
    createdAt: z.string(),
    updatedAt: z.string(),
});

export const SecretListQuerySchema = z.object({
    type: SecretTypeSchema.optional(),
});

export const SecretListResponseSchema = z.object({
    secrets: z.array(SecretSchema),
});

export const SecretDeleteParamsSchema = z.object({
    name: z.string(),
});

export const SecretDeleteResponseSchema = z.object({
    deleted: z.boolean(),
    name: z.string(),
});

export const SecretGetParamsSchema = z.object({
    name: z.string(),
});

export const SecretGetResponseSchema = z.object({
    name: z.string(),
    value: z.string(),
    createdAt: z.string(),
    updatedAt: z.string(),
});

export const OAuthRefreshBodySchema = z.object({
    name: z.string().min(1),
    clientId: z.string().min(1),
    clientSecret: z.string().min(1),
});

export const OAuthRefreshResponseSchema = z.object({
    name: z.string(),
    provider: z.string(),
    expiresAt: z.string().nullable(),
    refreshed: z.boolean(),
});

export type SecretSaveBody = z.infer<typeof SecretSaveBodySchema>;
export type SecretSaveResponse = z.infer<typeof SecretSaveResponseSchema>;
export type SecretListResponse = z.infer<typeof SecretListResponseSchema>;
export type SecretDeleteResponse = z.infer<typeof SecretDeleteResponseSchema>;
export type SecretGetResponse = z.infer<typeof SecretGetResponseSchema>;
export type OAuthRefreshBody = z.infer<typeof OAuthRefreshBodySchema>;
export type OAuthRefreshResponse = z.infer<typeof OAuthRefreshResponseSchema>;

// Log Schemas
export const LogSourceSchema = z.enum([
    'RuntimeHost',
    'WorkflowNode',
    'ToolCall',
]);
export type LogSourceType = z.infer<typeof LogSourceSchema>;

export const LogListQuerySchema = z.object({
    workflowId: z.string().optional(),
    runId: z.string().optional(),
    source: LogSourceSchema.optional(),
    limit: z.coerce.number().optional().default(100),
    offset: z.coerce.number().optional().default(0),
});

export const LogEntrySchema = z.object({
    id: z.string(),
    runId: z.string(),
    workflowId: z.string(),
    source: LogSourceSchema,
    message: z.string(),
    attributes: z.record(z.unknown()),
    timestamp: z.string(),
});

export const LogListResponseSchema = z.object({
    logs: z.array(LogEntrySchema),
    total: z.number(),
});

export const RunListQuerySchema = z.object({
    workflowId: z.string(),
    limit: z.coerce.number().optional().default(20),
    offset: z.coerce.number().optional().default(0),
});

export const RunEntrySchema = z.object({
    id: z.string(),
    workflowId: z.string(),
    status: z.enum(['running', 'completed', 'failed', 'interrupted']),
    startedAt: z.string(),
    completedAt: z.string().nullable(),
    exitCode: z.number().nullable(),
    logCount: z.number(),
});

export const RunListResponseSchema = z.object({
    runs: z.array(RunEntrySchema),
    total: z.number(),
});

export type LogListQuery = z.infer<typeof LogListQuerySchema>;
export type LogEntry = z.infer<typeof LogEntrySchema>;
export type LogListResponse = z.infer<typeof LogListResponseSchema>;
export type RunListQuery = z.infer<typeof RunListQuerySchema>;
export type RunEntry = z.infer<typeof RunEntrySchema>;
export type RunListResponse = z.infer<typeof RunListResponseSchema>;

// Interrupt Schemas
export const InterruptStatusSchema = z.enum(['Pending', 'Resumed', 'Expired']);
export type InterruptStatusType = z.infer<typeof InterruptStatusSchema>;

export const InterruptSchema = z.object({
    id: z.string(),
    runId: z.string(),
    workflowId: z.string(),
    payload: z.unknown(),
    nodeId: z.string().nullable(),
    status: InterruptStatusSchema,
    response: z.unknown().nullable(),
    createdAt: z.string(),
    resumedAt: z.string().nullable(),
});

export const InterruptListQuerySchema = z.object({
    workflowId: z.string().optional(),
    runId: z.string().optional(),
    status: InterruptStatusSchema.optional(),
    limit: z.coerce.number().optional().default(20),
    offset: z.coerce.number().optional().default(0),
});

export const InterruptListResponseSchema = z.object({
    interrupts: z.array(InterruptSchema),
    total: z.number(),
});

export const InterruptGetParamsSchema = z.object({
    interruptId: z.string(),
});

export const InterruptResumeParamsSchema = z.object({
    interruptId: z.string(),
});

export const InterruptResumeBodySchema = z.object({
    response: z.unknown(),
});

export const InterruptResumeResponseSchema = z.object({
    success: z.boolean(),
    interruptId: z.string(),
    resumedAt: z.string(),
    nextInterrupt: PendingInterruptSchema.optional(),
    status: RunStatusSchema.optional(),
});

export type Interrupt = z.infer<typeof InterruptSchema>;
export type InterruptListQuery = z.infer<typeof InterruptListQuerySchema>;
export type InterruptListResponse = z.infer<typeof InterruptListResponseSchema>;
export type InterruptResumeBody = z.infer<typeof InterruptResumeBodySchema>;
export type InterruptResumeResponse = z.infer<
    typeof InterruptResumeResponseSchema
>;

// Slack Schemas
export const SlackSlashCommandBodySchema = z.object({
    command: z.string(), // e.g., "/workflow"
    text: z.string(), // Everything after the command
    user_id: z.string(), // Slack user ID
    user_name: z.string(), // Slack username
    team_id: z.string(), // Slack workspace ID
    team_domain: z.string(), // Slack workspace domain
    channel_id: z.string(), // Channel where command was issued
    channel_name: z.string(), // Channel name
    response_url: z.string(), // URL for async responses
    trigger_id: z.string(), // For opening modals
});

export const SlackCommandResponseSchema = z.object({
    response_type: z.enum(['ephemeral', 'in_channel']).optional(),
    text: z.string(),
    blocks: z.array(z.unknown()).optional(),
});

export const SlackUserSchema = z.object({
    id: z.string(),
    slackUserId: z.string(),
    slackTeamId: z.string(),
    slackUsername: z.string().nullable(),
    userId: z.string(),
    createdAt: z.string(),
    updatedAt: z.string(),
});

export const SlackUserListResponseSchema = z.object({
    slackUsers: z.array(SlackUserSchema),
});

export type SlackSlashCommandBody = z.infer<typeof SlackSlashCommandBodySchema>;
export type SlackCommandResponse = z.infer<typeof SlackCommandResponseSchema>;
export type SlackUser = z.infer<typeof SlackUserSchema>;
export type SlackUserListResponse = z.infer<typeof SlackUserListResponseSchema>;
