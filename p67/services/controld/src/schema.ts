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
