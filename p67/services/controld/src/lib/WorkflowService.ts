import { randomUUID } from 'node:crypto';
import { existsSync } from 'node:fs';
import { readdir, readFile, rm } from 'node:fs/promises';
import { join } from 'node:path';
import type { PrismaClient, WorkflowWithOwner } from '@p67/db';
import { parseManifest } from './manifest.js';
import { unzip } from './zip.js';

export interface WorkflowServiceConfig {
    db: PrismaClient;
    localStoragePath: string;
}

export interface CreateWorkflowInput {
    ownerId: string;
    fileBuffer: Buffer;
    overwriteWorkflowId?: string;
}

export interface CreateWorkflowResult {
    workflowId: string;
    storagePath: string;
}

export class WorkflowLockedError extends Error {
    constructor(
        public readonly workflowId: string,
        public readonly activeRunId: string,
        public readonly startedAt: Date,
    ) {
        const elapsed = Math.round(
            (Date.now() - startedAt.getTime()) / 1000 / 60,
        );
        super(
            `Cannot overwrite workflow ${workflowId} while it is executing. Active run: ${activeRunId} (started ${elapsed} minute(s) ago)`,
        );
        this.name = 'WorkflowLockedError';
    }
}

export class WorkflowService {
    private db: PrismaClient;
    private localStoragePath: string;

    constructor(config: WorkflowServiceConfig) {
        this.db = config.db;
        this.localStoragePath = config.localStoragePath;
    }

    async create(
        ownerId: string,
        zipFileBuffer: Buffer,
        overwriteWorkflowId?: string,
    ): Promise<WorkflowWithOwner> {
        let workflowId = `wf-${randomUUID()}`;

        if (overwriteWorkflowId) {
            // Delete the old implementation, if one exists, otherwise throw an error.
            workflowId = overwriteWorkflowId;

            const existingWorkflow = await this.findRunnableWorkflowByUser(
                workflowId,
                ownerId,
            );
            if (!existingWorkflow) {
                throw new Error(`Workflow ${overwriteWorkflowId} not found`);
            }

            // Check if the workflow is currently executing
            const activeRun = await this.findActiveRun(workflowId);
            if (activeRun) {
                throw new WorkflowLockedError(
                    workflowId,
                    activeRun.id,
                    activeRun.startedAt,
                );
            }

            await this.db.workflow.delete({
                where: { id: workflowId },
            });
        }
        const dest = join(this.localStoragePath, workflowId);
        const { dir } = await unzip(zipFileBuffer, dest);

        // Extract workflow name and visibility from manifest if present
        let workflowName: string | undefined;
        let workflowVisibility: 'Private' | 'Public' = 'Private';
        const manifestPath = join(dir, 'manifest.yaml');
        if (existsSync(manifestPath)) {
            try {
                const manifestStr = await readFile(manifestPath, 'utf-8');
                const manifest = parseManifest(manifestStr);
                workflowName = manifest.name;
                workflowVisibility = manifest.visibility ?? 'Private';
            } catch (err) {
                console.debug(
                    `[WorkflowService] Failed to parse manifest for name extraction: ${err}`,
                );
            }
        }

        return this.db.workflow.create({
            data: {
                id: workflowId,
                name: workflowName,
                storagePath: dir,
                ownerId: ownerId,
                visibility: workflowVisibility,
            },
            include: {
                owner: true,
            },
        });
    }

    async listAll(): Promise<WorkflowWithOwner[]> {
        return this.db.workflow.findMany({
            include: {
                owner: true,
            },
        });
    }

    async listFromDisk(): Promise<string[]> {
        if (!existsSync(this.localStoragePath)) {
            return [];
        }

        const entries = await readdir(this.localStoragePath, {
            withFileTypes: true,
        });

        return entries
            .filter(
                (entry) => entry.isDirectory() && entry.name.startsWith('wf-'),
            )
            .map((entry) => entry.name);
    }

    async findById(workflowId: string): Promise<WorkflowWithOwner | null> {
        const wf = this.db.workflow.findUnique({
            where: { id: workflowId },
            include: {
                owner: true,
            },
        });
        return wf;
    }

    // Lookup workflow by ID and enforce RBAC constraints before returning
    async findRunnableWorkflowByUser(
        workflowId: string,
        userId: string,
    ): Promise<WorkflowWithOwner | null> {
        const wf = await this.findById(workflowId);

        // Workflow does not exist
        if (!wf) {
            return null;
        }

        // Workflow is not runnable by user
        if (!this.rbacUserCanRun(userId, wf)) {
            return null;
        }

        return wf;
    }

    // Find all workflows a user can run (either the user is the owner, or the workflow is set to public visibility)
    async findAllRunnableWorkflowsByUser(
        userId: string,
    ): Promise<WorkflowWithOwner[]> {
        return this.db.workflow.findMany({
            where: {
                OR: [{ ownerId: userId }, { visibility: 'Public' }],
            },
            include: {
                owner: true,
            },
        });
    }

    /**
     * Find the latest workflow version by name that a user can run.
     * Returns the most recently created workflow with the given name.
     */
    async findLatestByName(
        name: string,
        userId: string,
    ): Promise<WorkflowWithOwner | null> {
        const wf = await this.db.workflow.findFirst({
            where: {
                name,
                OR: [{ ownerId: userId }, { visibility: 'Public' }],
            },
            orderBy: {
                createdAt: 'desc',
            },
            include: {
                owner: true,
            },
        });
        return wf;
    }

    /**
     * Find all versions of a workflow by name that a user can access.
     * Returns workflows sorted by createdAt descending (newest first).
     */
    async findAllVersionsByName(
        name: string,
        userId: string,
    ): Promise<WorkflowWithOwner[]> {
        return this.db.workflow.findMany({
            where: {
                name,
                OR: [{ ownerId: userId }, { visibility: 'Public' }],
            },
            orderBy: {
                createdAt: 'desc',
            },
            include: {
                owner: true,
            },
        });
    }

    /**
     * Get unique workflow names for a user (for listing available workflows by name).
     */
    async getUniqueWorkflowNames(userId: string): Promise<string[]> {
        const workflows = await this.db.workflow.findMany({
            where: {
                name: { not: null },
                OR: [{ ownerId: userId }, { visibility: 'Public' }],
            },
            select: {
                name: true,
            },
            distinct: ['name'],
        });
        return workflows
            .map((w) => w.name)
            .filter((n): n is string => n !== null);
    }

    async setVisibility(
        workflowId: string,
        visibility: 'Private' | 'Public',
    ): Promise<WorkflowWithOwner> {
        return this.db.workflow.update({
            where: { id: workflowId },
            data: { visibility },
            include: { owner: true },
        });
    }

    rbacUserCanRun(userId: string, workflow: WorkflowWithOwner): boolean {
        return (
            this.rbacUserCanUpdate(userId, workflow) ||
            workflow.visibility === 'Public'
        );
    }

    rbacUserCanUpdate(userId: string, workflow: WorkflowWithOwner): boolean {
        return workflow.ownerId === userId;
    }

    getWorkflowPath(workflowId: string): string {
        return join(this.localStoragePath, workflowId);
    }

    workflowExistsOnDisk(workflowId: string): boolean {
        return existsSync(this.getWorkflowPath(workflowId));
    }

    /**
     * Find an active (running) workflow run for the given workflow.
     * Returns the active run if one exists, null otherwise.
     *
     * A run is considered active if:
     * - status is 'Running' AND
     * - completedAt is null (hasn't finished yet)
     */
    async findActiveRun(workflowId: string) {
        return this.db.workflowRun.findFirst({
            where: {
                workflowId,
                status: 'Running',
                completedAt: null,
            },
            orderBy: {
                startedAt: 'desc',
            },
        });
    }

    /**
     * Delete a workflow by ID.
     * Only the owner can delete. Rejects if the workflow has an active run.
     * Prisma cascades handle cleanup of runs, logs, and interrupts.
     * Disk files are removed after the DB record is deleted.
     */
    async delete(workflowId: string, userId: string): Promise<boolean> {
        const workflow = await this.findById(workflowId);
        if (!workflow) {
            return false;
        }

        if (!this.rbacUserCanUpdate(userId, workflow)) {
            return false;
        }

        const activeRun = await this.findActiveRun(workflowId);
        if (activeRun) {
            throw new WorkflowLockedError(
                workflowId,
                activeRun.id,
                activeRun.startedAt,
            );
        }

        await this.db.workflow.delete({
            where: { id: workflowId },
        });

        const diskPath = this.getWorkflowPath(workflowId);
        if (existsSync(diskPath)) {
            await rm(diskPath, { recursive: true, force: true });
        }

        return true;
    }
}
