import { z } from 'zod';

export const ExecuteMessageSchema = z.object({
  dir: z.string(),
  action: z.literal('run'),
});

export type ExecuteMessage = z.infer<typeof ExecuteMessageSchema>;

// Health check schemas
export const HealthResponseSchema = z.object({
  status: z.string().openapi({ example: 'ok' }),
  timestamp: z.string().openapi({ example: '2025-12-12T10:00:00.000Z' }),
  localStoragePath: z.string().openapi({ example: '/tmp/storage' }),
});

// Workflow schemas
export const WorkflowCreateResponseSchema = z.object({
  workflowId: z.string().openapi({ example: 'wf-123e4567-e89b-12d3-a456-426614174000' }),
});

export const WorkflowListResponseSchema = z.object({
  workflows: z.array(z.string()).openapi({ example: ['wf-123', 'wf-456'] }),
});

export const WorkflowRunResponseSchema = z.object({
  exitCode: z.number().openapi({ example: 0 }),
  stdout: z.string().openapi({ example: 'Task completed successfully' }),
  stderr: z.string().openapi({ example: '' }),
  success: z.boolean().openapi({ example: true }),
});

export const ErrorResponseSchema = z.object({
  error: z.string(),
  message: z.string().optional(),
});
