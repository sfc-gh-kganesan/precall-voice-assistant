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
});

export const WorkflowSchema = z.object({
    workflowId: z.string(),
    owner: z.string(),
    createdAt: z.string(),
    updatedAt: z.string(),
    visibility: z.string(),
});

export const WorkflowListResponseSchema = z.object({
    workflows: z.array(WorkflowSchema),
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
});

export const WorkflowRunParamsSchema = z.object({
    workflowId: z.string(),
});

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
export const SecretSaveBodySchema = z.object({
    name: z.string().min(1),
    secret: z.string().min(1),
});

export const SecretSaveResponseSchema = z.object({
    name: z.string(),
    created: z.boolean(),
});

export const SecretSchema = z.object({
    name: z.string(),
    createdAt: z.string(),
    updatedAt: z.string(),
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

export type SecretSaveBody = z.infer<typeof SecretSaveBodySchema>;
export type SecretSaveResponse = z.infer<typeof SecretSaveResponseSchema>;
export type SecretListResponse = z.infer<typeof SecretListResponseSchema>;
export type SecretDeleteResponse = z.infer<typeof SecretDeleteResponseSchema>;

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
