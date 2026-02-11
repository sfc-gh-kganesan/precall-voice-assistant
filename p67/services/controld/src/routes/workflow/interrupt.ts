import {
    ErrorResponseSchema,
    InterruptGetParamsSchema,
    InterruptListQuerySchema,
    InterruptListResponseSchema,
    InterruptResumeBodySchema,
    InterruptResumeParamsSchema,
    InterruptResumeResponseSchema,
    InterruptSchema,
} from '@controld/schema.js';
import type { InterruptStatus, WorkflowInterrupt } from '@p67/db';
import type { FastifyInstance } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';

export function registerInterruptRoutes(server: FastifyInstance) {
    const fastify = server.withTypeProvider<ZodTypeProvider>();

    // List interrupts (with optional filters)
    fastify.get(
        '/interrupts',
        {
            schema: {
                description: 'List workflow interrupts',
                tags: ['Interrupt'],
                querystring: InterruptListQuerySchema,
                response: {
                    200: InterruptListResponseSchema,
                    500: ErrorResponseSchema,
                },
            },
        },
        async (request, reply) => {
            try {
                const { workflowId, runId, status, limit, offset } =
                    request.query;

                const where: {
                    workflowId?: string;
                    runId?: string;
                    status?: InterruptStatus;
                    run?: { userId: string };
                } = {
                    run: { userId: request.user.id },
                };

                if (workflowId) where.workflowId = workflowId;
                if (runId) where.runId = runId;
                if (status) where.status = status as InterruptStatus;

                const [interrupts, total] = await Promise.all([
                    fastify.db.workflowInterrupt.findMany({
                        where,
                        orderBy: { createdAt: 'desc' },
                        take: limit,
                        skip: offset,
                    }),
                    fastify.db.workflowInterrupt.count({ where }),
                ]);

                return reply.code(200).send({
                    interrupts: interrupts.map((i: WorkflowInterrupt) => ({
                        id: i.id,
                        runId: i.runId,
                        workflowId: i.workflowId,
                        payload: i.payload,
                        nodeId: i.nodeId,
                        status: i.status as 'Pending' | 'Resumed' | 'Expired',
                        response: i.response,
                        createdAt: i.createdAt.toISOString(),
                        resumedAt: i.resumedAt?.toISOString() ?? null,
                    })),
                    total,
                });
            } catch (error) {
                console.error('Error listing interrupts:', error);
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

    // Get a specific interrupt
    fastify.get(
        '/interrupts/:interruptId',
        {
            schema: {
                description: 'Get a specific interrupt',
                tags: ['Interrupt'],
                params: InterruptGetParamsSchema,
                response: {
                    200: InterruptSchema,
                    404: ErrorResponseSchema,
                    500: ErrorResponseSchema,
                },
            },
        },
        async (request, reply) => {
            try {
                const { interruptId } = request.params;

                const interrupt = await fastify.db.workflowInterrupt.findFirst({
                    where: {
                        id: interruptId,
                        run: { userId: request.user.id },
                    },
                });

                if (!interrupt) {
                    return reply.code(404).send({
                        error: 'Not found',
                        message: `Interrupt ${interruptId} not found`,
                    });
                }

                return reply.code(200).send({
                    id: interrupt.id,
                    runId: interrupt.runId,
                    workflowId: interrupt.workflowId,
                    payload: interrupt.payload,
                    nodeId: interrupt.nodeId,
                    status: interrupt.status as
                        | 'Pending'
                        | 'Resumed'
                        | 'Expired',
                    response: interrupt.response,
                    createdAt: interrupt.createdAt.toISOString(),
                    resumedAt: interrupt.resumedAt?.toISOString() ?? null,
                });
            } catch (error) {
                console.error('Error getting interrupt:', error);
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

    // Resume an interrupt
    fastify.post(
        '/interrupts/:interruptId/resume',
        {
            schema: {
                description: 'Resume a paused workflow with human input',
                tags: ['Interrupt'],
                params: InterruptResumeParamsSchema,
                body: InterruptResumeBodySchema,
                response: {
                    200: InterruptResumeResponseSchema,
                    400: ErrorResponseSchema,
                    404: ErrorResponseSchema,
                    409: ErrorResponseSchema,
                    500: ErrorResponseSchema,
                },
            },
        },
        async (request, reply) => {
            try {
                const { interruptId } = request.params;
                const { response } = request.body;

                // Find the interrupt
                const interrupt = await fastify.db.workflowInterrupt.findFirst({
                    where: {
                        id: interruptId,
                        run: { userId: request.user.id },
                    },
                });

                if (!interrupt) {
                    return reply.code(404).send({
                        error: 'Not found',
                        message: `Interrupt ${interruptId} not found`,
                    });
                }

                if (interrupt.status !== 'Pending') {
                    return reply.code(400).send({
                        error: 'Invalid state',
                        message: `Interrupt ${interruptId} is not pending (status: ${interrupt.status})`,
                    });
                }

                // Get the runner from the registry (if available)
                const runner = fastify.runnerRegistry?.get(interrupt.runId);
                if (!runner) {
                    return reply.code(409).send({
                        error: 'Conflict',
                        message:
                            'Workflow process no longer active. The workflow may have timed out or crashed.',
                    });
                }

                // Resume the workflow and wait for next event (interrupt or completion)
                runner.resume(interruptId, response);
                const nextResult = await runner.waitForNextEvent();

                // Update the interrupt record
                const resumedAt = new Date();
                await fastify.db.workflowInterrupt.update({
                    where: { id: interruptId },
                    data: {
                        status: 'Resumed',
                        response: response as object,
                        resumedAt,
                    },
                });

                // Handle the next state
                if (
                    nextResult.status === 'interrupted' &&
                    nextResult.pendingInterrupt
                ) {
                    // Workflow hit another interrupt - save it to database
                    await fastify.db.workflowInterrupt.create({
                        data: {
                            id: nextResult.pendingInterrupt.interruptId,
                            runId: interrupt.runId,
                            workflowId: interrupt.workflowId,
                            payload: nextResult.pendingInterrupt
                                .value as object,
                            nodeId: nextResult.pendingInterrupt.nodeId,
                            status: 'Pending',
                        },
                    });

                    // Update run status to Interrupted
                    await fastify.db.workflowRun.update({
                        where: { id: interrupt.runId },
                        data: { status: 'Interrupted' },
                    });

                    return reply.code(200).send({
                        success: true,
                        interruptId,
                        resumedAt: resumedAt.toISOString(),
                        nextInterrupt: nextResult.pendingInterrupt,
                        status: 'interrupted',
                    });
                } else {
                    // Workflow completed or failed
                    await fastify.db.workflowRun.update({
                        where: { id: interrupt.runId },
                        data: {
                            status:
                                nextResult.status === 'completed'
                                    ? 'Completed'
                                    : 'Failed',
                            completedAt: new Date(),
                        },
                    });

                    // Clean up runner from registry
                    fastify.runnerRegistry.delete(interrupt.runId);

                    return reply.code(200).send({
                        success: true,
                        interruptId,
                        resumedAt: resumedAt.toISOString(),
                        status: nextResult.status,
                    });
                }
            } catch (error) {
                console.error('Error resuming interrupt:', error);
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
