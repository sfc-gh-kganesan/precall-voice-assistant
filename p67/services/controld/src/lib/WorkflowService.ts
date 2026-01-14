import { randomUUID } from 'node:crypto';
import { existsSync } from 'node:fs';
import { readdir } from 'node:fs/promises';
import { join } from 'node:path';
import type { PrismaClient, Workflow } from '@p67/db';
import { unzip } from './zip.js';

export interface WorkflowServiceConfig {
    db: PrismaClient;
    localStoragePath: string;
}

export interface CreateWorkflowInput {
    ownerId: string;
    fileBuffer: Buffer;
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

    async create(ownerId: string, zipFileBuffer: Buffer): Promise<Workflow> {
        const workflowId = `wf-${randomUUID()}`;
        const dest = join(this.localStoragePath, workflowId);
        const { dir } = await unzip(zipFileBuffer, dest);

        return this.db.workflow.create({
            data: {
                id: workflowId,
                storagePath: dir,
                ownerId: ownerId,
                visibility: 'Private',
            },
        });
    }

    async listAll(): Promise<Workflow[]> {
        return this.db.workflow.findMany();
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

    async findById(workflowId: string): Promise<Workflow | null> {
        return this.db.workflow.findUnique({
            where: { id: workflowId },
        });
    }

    async findByOwner(ownerId: string): Promise<Workflow[]> {
        return this.db.workflow.findMany({
            where: { ownerId },
        });
    }

    getWorkflowPath(workflowId: string): string {
        return join(this.localStoragePath, workflowId);
    }

    workflowExistsOnDisk(workflowId: string): boolean {
        return existsSync(this.getWorkflowPath(workflowId));
    }
}
