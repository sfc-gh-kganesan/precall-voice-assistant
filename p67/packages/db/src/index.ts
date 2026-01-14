export type {
    PrismaClient,
    Workflow,
} from './generated/prisma/client.js';
export { UserModel } from './generated/prisma/models/User.js';
export { WorkflowModel } from './generated/prisma/models/Workflow.js';
export type { DatabasePluginOptions } from './plugin.js';
export { databasePlugin } from './plugin.js';

import type { Prisma } from './generated/prisma/client.js';

type WorkflowWithOwner = Prisma.WorkflowGetPayload<{
    include: { owner: true };
}>;
export type { WorkflowWithOwner };
