import { WorkflowLockedError } from '@controld/lib/WorkflowService.js';
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
                    409: ErrorResponseSchema,
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

                const overwriteField = data.fields.overwriteWorkflowId;
                let overwriteWorkflowId: string | undefined;
                if (overwriteField && 'value' in overwriteField) {
                    overwriteWorkflowId = overwriteField.value?.toString();
                }

                const fileBuffer = await data.toBuffer();
                const result = await fastify.workflowService.create(
                    request.user.id /* ownerId */,
                    fileBuffer /* zip file buffer */,
                    overwriteWorkflowId /* overwriteWorkflowId */,
                );
                return reply.code(200).send({
                    workflowId: result.workflowId,
                    isNewVersion: result.isNewVersion || undefined,
                    versionNumber: result.isNewVersion
                        ? result.versionNumber
                        : undefined,
                });
            } catch (error) {
                console.error('Error creating workflow:', error);

                // Handle workflow locked error with 409 Conflict
                if (error instanceof WorkflowLockedError) {
                    return reply.code(409).send({
                        error: 'WorkflowLocked',
                        message: error.message,
                    });
                }

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
