import { z } from 'zod';

export const HealthResponseSchema = z.object({
  status: z.string(),
  timestamp: z.string(),
});

export const ErrorResponseSchema = z.object({
  error: z.string(),
  message: z.string().optional(),
});

export type HealthResponse = z.infer<typeof HealthResponseSchema>;
export type ErrorResponse = z.infer<typeof ErrorResponseSchema>;
