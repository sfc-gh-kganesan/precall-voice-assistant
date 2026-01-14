import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { Runner } from '@controld/lib/runner.js';
import {
    ErrorResponseSchema,
    WorkflowRunParamsSchema,
    WorkflowRunResponseSchema,
} from '@controld/schema.js';
import type { FastifyInstance } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';

export function registerRunRoute(server: FastifyInstance) {
    const fastify = server.withTypeProvider<ZodTypeProvider>();

    fastify.post(
        '/:workflowId/run',
        {
            schema: {
                description: 'Run a workflow',
                tags: ['Workflow'],
                params: WorkflowRunParamsSchema,
                response: {
                    200: WorkflowRunResponseSchema,
                    400: ErrorResponseSchema,
                    500: ErrorResponseSchema,
                },
            },
        },
        async (request, reply) => {
            try {
                const { localStoragePath } = request.server.config;
                const { workflowId } = request.params as { workflowId: string };
                const wfdir = join(localStoragePath, workflowId);

                if (!existsSync(wfdir)) {
                    return reply.code(400).send({
                        error: 'Invalid request',
                        message: `Workflow ${workflowId} does not exist`,
                    });
                }

                const runnerInstance = new Runner(wfdir);
                const { stdout, stderr, exitCode, errors, log } =
                    await runnerInstance.start();

                return reply.code(200).send({
                    exitCode,
                    stdout,
                    stderr,
                    errors,
                    log,
                    success: exitCode === 0,
                });
            } catch (error) {
                console.error('Error running workflow:', error);
                return reply.code(500).send({
                    error: 'Internal server error',
                    message:
                        error instanceof Error
                            ? error.message
                            : 'Unknown error',
                });
            }
        },
    );
}
