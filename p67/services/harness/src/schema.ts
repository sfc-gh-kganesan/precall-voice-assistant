import { z } from 'zod';

export const ExecuteMessageSchema = z.object({
  dir: z.string(),
  action: z.literal('run'),
});

export type ExecuteMessage = z.infer<typeof ExecuteMessageSchema>;
