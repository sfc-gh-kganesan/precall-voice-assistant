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

export const WorkflowListResponseSchema = z.object({
  workflows: z.array(z.string()),
});

export const WorkflowRunResponseSchema = z.object({
  exitCode: z.number(),
  stdout: z.string(),
  stderr: z.string(),
  success: z.boolean(),
});

export const WorkflowRunParamsSchema = z.object({
  workflowId: z.string(),
});

export type HealthResponse = z.infer<typeof HealthResponseSchema>;
export type ErrorResponse = z.infer<typeof ErrorResponseSchema>;
