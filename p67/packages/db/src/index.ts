export type {
    Log,
    LogSource,
    PrismaClient,
    Secret,
    Workflow,
    WorkflowRun,
} from './generated/prisma/client.js';
export { SecretModel } from './generated/prisma/models/Secret.js';
export { UserModel } from './generated/prisma/models/User.js';
export { WorkflowModel } from './generated/prisma/models/Workflow.js';
export type { DatabasePluginOptions } from './plugin.js';
export { databasePlugin } from './plugin.js';

import type { Prisma } from './generated/prisma/client.js';

type WorkflowWithOwner = Prisma.WorkflowGetPayload<{
    include: { owner: true };
}>;
export type { WorkflowWithOwner };

type WorkflowRunWithLogs = Prisma.WorkflowRunGetPayload<{
    include: { logs: true };
}>;
export type { WorkflowRunWithLogs };
