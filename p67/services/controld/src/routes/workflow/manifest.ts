import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { parseManifest, type Value } from '@controld/lib/manifest.js';
import {
    ErrorResponseSchema,
    WorkflowManifestResponseSchema,
    WorkflowRunParamsSchema,
} from '@controld/schema.js';
import type { FastifyInstance } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';

export function registerManifestRoute(server: FastifyInstance) {
    const fastify = server.withTypeProvider<ZodTypeProvider>();

    fastify.get(
        '/:workflowId/manifest',
        {
            schema: {
                description: 'Get workflow manifest params',
                tags: ['Workflow'],
                params: WorkflowRunParamsSchema,
                response: {
                    200: WorkflowManifestResponseSchema,
                    400: ErrorResponseSchema,
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

                const manifestPath = join(
                    workflow.storagePath,
                    'manifest.yaml',
                );

                if (!existsSync(manifestPath)) {
                    return reply.code(200).send({
                        params: undefined,
                    });
                }

                const manifestStr = await readFile(manifestPath, 'utf-8');
                const manifest = parseManifest(manifestStr);

                // Merge top-level params and config[].parameters
                const allParams: Record<string, Value> = {};

                // Add top-level params first
                if (manifest.params) {
                    Object.assign(allParams, manifest.params);
                }

                // Add config[].parameters second - these override top-level params if same key exists
                for (const config of manifest.config) {
                    if (config.parameters) {
                        Object.assign(allParams, config.parameters);
                    }
                }

                return reply.code(200).send({
                    params:
                        Object.keys(allParams).length > 0
                            ? allParams
                            : undefined,
                });
            } catch (error) {
                console.error('Error getting workflow manifest:', error);
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
