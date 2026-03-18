import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import {
    ErrorResponseSchema,
    WorkflowGraphResponseSchema,
    WorkflowRunParamsSchema,
} from '@controld/schema.js';
import type { FastifyInstance } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';

export function registerGraphRoute(server: FastifyInstance) {
    const fastify = server.withTypeProvider<ZodTypeProvider>();

    fastify.get(
        '/:workflowId/graph',
        {
            schema: {
                description: 'Get workflow graph definition',
                tags: ['Workflow'],
                params: WorkflowRunParamsSchema,
                response: {
                    200: WorkflowGraphResponseSchema,
                    404: ErrorResponseSchema,
                    500: ErrorResponseSchema,
                },
            },
        },
        async (request, reply) => {
            try {
                const { workflowId } = request.params as { workflowId: string };

                const workflow =
                    await fastify.workflowService.findRunnableWorkflowByUser(
                        workflowId,
                        request.user.id,
                    );

                if (!workflow) {
                    return reply.code(404).send({
                        error: 'Not found',
                        message: `Workflow ${workflowId} not found or you do not have access`,
                    });
                }

                const graphJsonPath = join(workflow.storagePath, 'graph.json');
                if (existsSync(graphJsonPath)) {
                    try {
                        const graphStr = await readFile(graphJsonPath, 'utf-8');
                        const graphData = JSON.parse(graphStr);
                        return reply.code(200).send({
                            graph: graphData,
                        });
                    } catch {
                        // ignore parse errors
                    }
                }

                return reply.code(200).send({ graph: null });
            } catch (error) {
                console.error('Error getting workflow graph:', error);
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
