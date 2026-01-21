import type {
    Log,
    LogSource,
    PrismaClient,
    WorkflowRun,
    WorkflowRunStatus,
} from '@p67/db';

export interface LogServiceConfig {
    db: PrismaClient;
}

export interface CreateLogInput {
    runId: string;
    workflowId: string;
    userId: string;
    source: LogSource;
    message: string;
    attributes?: Record<string, unknown>;
}

export interface LogFilter {
    workflowId?: string;
    runId?: string;
    source?: LogSource;
    startTime?: Date;
    endTime?: Date;
    limit?: number;
    offset?: number;
}

export interface RunWithLogCount extends WorkflowRun {
    _count: {
        logs: number;
    };
}

export class LogService {
    private db: PrismaClient;

    constructor(config: LogServiceConfig) {
        this.db = config.db;
    }

    async createRun(workflowId: string, userId: string): Promise<WorkflowRun> {
        return this.db.workflowRun.create({
            data: {
                workflowId,
                userId,
            },
        });
    }

    async completeRun(runId: string, exitCode: number): Promise<WorkflowRun> {
        const status: WorkflowRunStatus =
            exitCode === 0 ? 'Completed' : 'Failed';
        return this.db.workflowRun.update({
            where: { id: runId },
            data: {
                completedAt: new Date(),
                exitCode,
                status,
            },
        });
    }

    async writeLog(input: CreateLogInput): Promise<Log> {
        return this.db.log.create({
            data: {
                runId: input.runId,
                workflowId: input.workflowId,
                userId: input.userId,
                source: input.source,
                message: input.message,
                // biome-ignore lint/suspicious/noExplicitAny: Prisma JSON type requires flexible input
                attributes: (input.attributes ?? {}) as any,
            },
        });
    }

    async writeLogs(inputs: CreateLogInput[]): Promise<number> {
        const result = await this.db.log.createMany({
            data: inputs.map((input) => ({
                runId: input.runId,
                workflowId: input.workflowId,
                userId: input.userId,
                source: input.source,
                message: input.message,
                // biome-ignore lint/suspicious/noExplicitAny: Prisma JSON type requires flexible input
                attributes: (input.attributes ?? {}) as any,
            })),
        });
        return result.count;
    }

    async findLogsByUser(userId: string, filter: LogFilter): Promise<Log[]> {
        // First get all workflows the user can access (owned or public)
        const accessibleWorkflows = await this.db.workflow.findMany({
            where: {
                OR: [{ ownerId: userId }, { visibility: 'Public' }],
            },
            select: { id: true },
        });

        const workflowIds = accessibleWorkflows.map((w) => w.id);

        // Build where clause
        const where: {
            workflowId: { in: string[] } | string;
            runId?: string;
            source?: LogSource;
            timestamp?: { gte?: Date; lte?: Date };
        } = {
            workflowId: filter.workflowId
                ? filter.workflowId
                : { in: workflowIds },
        };

        // If filtering by specific workflow, verify access
        if (filter.workflowId && !workflowIds.includes(filter.workflowId)) {
            return [];
        }

        if (filter.runId) {
            where.runId = filter.runId;
        }

        if (filter.source) {
            where.source = filter.source;
        }

        if (filter.startTime || filter.endTime) {
            where.timestamp = {};
            if (filter.startTime) {
                where.timestamp.gte = filter.startTime;
            }
            if (filter.endTime) {
                where.timestamp.lte = filter.endTime;
            }
        }

        return this.db.log.findMany({
            where,
            orderBy: { timestamp: 'asc' },
            take: filter.limit ?? 100,
            skip: filter.offset ?? 0,
        });
    }

    async countLogsByUser(userId: string, filter: LogFilter): Promise<number> {
        // First get all workflows the user can access
        const accessibleWorkflows = await this.db.workflow.findMany({
            where: {
                OR: [{ ownerId: userId }, { visibility: 'Public' }],
            },
            select: { id: true },
        });

        const workflowIds = accessibleWorkflows.map((w) => w.id);

        // Build where clause
        const where: {
            workflowId: { in: string[] } | string;
            runId?: string;
            source?: LogSource;
            timestamp?: { gte?: Date; lte?: Date };
        } = {
            workflowId: filter.workflowId
                ? filter.workflowId
                : { in: workflowIds },
        };

        if (filter.workflowId && !workflowIds.includes(filter.workflowId)) {
            return 0;
        }

        if (filter.runId) {
            where.runId = filter.runId;
        }

        if (filter.source) {
            where.source = filter.source;
        }

        if (filter.startTime || filter.endTime) {
            where.timestamp = {};
            if (filter.startTime) {
                where.timestamp.gte = filter.startTime;
            }
            if (filter.endTime) {
                where.timestamp.lte = filter.endTime;
            }
        }

        return this.db.log.count({ where });
    }

    async findRunsByWorkflowAndUser(
        workflowId: string,
        userId: string,
        options?: { limit?: number; offset?: number },
    ): Promise<RunWithLogCount[]> {
        // Verify user can access this workflow
        const workflow = await this.db.workflow.findFirst({
            where: {
                id: workflowId,
                OR: [{ ownerId: userId }, { visibility: 'Public' }],
            },
        });

        if (!workflow) {
            return [];
        }

        return this.db.workflowRun.findMany({
            where: { workflowId },
            orderBy: { startedAt: 'desc' },
            take: options?.limit ?? 20,
            skip: options?.offset ?? 0,
            include: {
                _count: {
                    select: { logs: true },
                },
            },
        });
    }

    async countRunsByWorkflowAndUser(
        workflowId: string,
        userId: string,
    ): Promise<number> {
        // Verify user can access this workflow
        const workflow = await this.db.workflow.findFirst({
            where: {
                id: workflowId,
                OR: [{ ownerId: userId }, { visibility: 'Public' }],
            },
        });

        if (!workflow) {
            return 0;
        }

        return this.db.workflowRun.count({
            where: { workflowId },
        });
    }
}
