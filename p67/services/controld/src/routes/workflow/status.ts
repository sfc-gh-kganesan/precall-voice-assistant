import {
    ErrorResponseSchema,
    WorkflowRunStatusParamsSchema,
    WorkflowRunStatusResponseSchema,
} from '@controld/schema.js';
import type { FastifyInstance } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';

export function registerStatusRoute(server: FastifyInstance) {
    const fastify = server.withTypeProvider<ZodTypeProvider>();

    fastify.get(
        '/runs/:runId',
        {
            schema: {
                description:
                    'Get the status of a workflow run (polling endpoint)',
                tags: ['Workflow'],
                params: WorkflowRunStatusParamsSchema,
                response: {
                    200: WorkflowRunStatusResponseSchema,
                    404: ErrorResponseSchema,
                    500: ErrorResponseSchema,
                },
            },
        },
        async (request, reply) => {
            try {
                const { runId } = request.params as { runId: string };

                const run = await fastify.db.workflowRun.findFirst({
                    where: {
                        id: runId,
                        userId: request.user.id,
                    },
                    include: {
                        logs: {
                            orderBy: { timestamp: 'asc' },
                        },
                        interrupts: {
                            where: { status: 'Pending' },
                            orderBy: { createdAt: 'desc' },
                            take: 1,
                        },
                    },
                });

                if (!run) {
                    return reply.code(404).send({
                        error: 'Not found',
                        message: `Run ${runId} not found or you do not have access`,
                    });
                }

                // Map Prisma PascalCase status to lowercase RunStatus
                const statusMap: Record<string, string> = {
                    Running: 'running',
                    Completed: 'completed',
                    Interrupted: 'interrupted',
                    Failed: 'failed',
                };
                const status = statusMap[run.status] ?? 'running';

                // Extract log lines by source
                const stdout: string[] = [];
                const stderr: string[] = [];
                const log: string[] = [];
                for (const entry of run.logs) {
                    const msg = entry.message;
                    if (entry.source === 'RuntimeHost') {
                        log.push(msg);
                    } else if (entry.source === 'ToolCall') {
                        stdout.push(msg);
                    } else {
                        stdout.push(msg);
                    }
                }

                // Build pending interrupt if any
                const pendingInterrupt =
                    run.interrupts.length > 0
                        ? {
                              interruptId: run.interrupts[0].id,
                              value: run.interrupts[0].payload,
                              timestamp:
                                  run.interrupts[0].createdAt.toISOString(),
                              nodeId: run.interrupts[0].nodeId ?? undefined,
                          }
                        : undefined;

                // Build response — always include all fields for type safety
                return reply.code(200).send({
                    runId: run.id,
                    status: status as
                        | 'running'
                        | 'completed'
                        | 'interrupted'
                        | 'failed',
                    exitCode: run.exitCode,
                    result:
                        status !== 'running'
                            ? (run.result ?? undefined)
                            : undefined,
                    stdout: status !== 'running' ? stdout : undefined,
                    stderr: status !== 'running' ? stderr : undefined,
                    log: status !== 'running' ? log : undefined,
                    errors: status !== 'running' ? [] : undefined,
                    pendingInterrupt: pendingInterrupt ?? undefined,
                });
            } catch (error) {
                console.error('Error fetching run status:', error);
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
