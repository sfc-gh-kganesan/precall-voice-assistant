import { randomUUID } from 'node:crypto';
import { existsSync } from 'node:fs';
import { readdir } from 'node:fs/promises';
import { join } from 'node:path';
import type { PrismaClient, WorkflowWithOwner } from '@p67/db';
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

            await this.db.workflow.delete({
                where: { id: workflowId },
            });
        }
        const dest = join(this.localStoragePath, workflowId);
        const { dir } = await unzip(zipFileBuffer, dest);

        return this.db.workflow.create({
            data: {
                id: workflowId,
                storagePath: dir,
                ownerId: ownerId,
                visibility: 'Private',
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
}
