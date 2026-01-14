import {
    ErrorResponseSchema,
    WorkflowCreateResponseSchema,
} from '@controld/schema.js';
import type { FastifyInstance } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';

export function registerCreateRoute(server: FastifyInstance) {
    const fastify = server.withTypeProvider<ZodTypeProvider>();

    fastify.post(
        '/create',
        {
            schema: {
                description: 'Create a new workflow by uploading a ZIP file',
                tags: ['Workflow'],
                response: {
                    200: WorkflowCreateResponseSchema,
                    400: ErrorResponseSchema,
                    500: ErrorResponseSchema,
                },
            },
        },
        async (request, reply) => {
            try {
                const data = await request.file();

                if (!data) {
                    return reply.code(400).send({ error: 'No file uploaded' });
                }

                const fileBuffer = await data.toBuffer();
                const wf = await fastify.workflowService.create(
                    request.user.id /* ownerId */,
                    fileBuffer /* zip file buffer */,
                );
                return reply.code(200).send({ workflowId: wf.id });
            } catch (error) {
                console.error('Error creating workflow:', error);
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
