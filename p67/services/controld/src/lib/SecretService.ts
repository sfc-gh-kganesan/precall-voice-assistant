import type { PrismaClient, Secret } from '@p67/db';

export interface SecretServiceConfig {
    db: PrismaClient;
}

export interface SaveSecretResult {
    name: string;
    created: boolean;
}

export interface SecretMetadata {
    name: string;
    createdAt: Date;
    updatedAt: Date;
}

export class SecretService {
    private db: PrismaClient;

    constructor(config: SecretServiceConfig) {
        this.db = config.db;
    }

    async save(
        ownerId: string,
        name: string,
        secret: string,
    ): Promise<SaveSecretResult> {
        const existing = await this.findByName(ownerId, name);

        if (existing) {
            await this.db.secret.update({
                where: {
                    ownerId_name: { ownerId, name },
                },
                data: {
                    secret,
                    updatedAt: new Date(),
                },
            });
            return { name, created: false };
        }

        await this.db.secret.create({
            data: {
                name,
                secret,
                ownerId,
            },
        });
        return { name, created: true };
    }

    async list(ownerId: string): Promise<SecretMetadata[]> {
        const secrets = await this.db.secret.findMany({
            where: { ownerId },
            select: {
                name: true,
                createdAt: true,
                updatedAt: true,
            },
            orderBy: { name: 'asc' },
        });
        return secrets;
    }

    async delete(ownerId: string, name: string): Promise<boolean> {
        const existing = await this.findByName(ownerId, name);

        if (!existing) {
            return false;
        }

        await this.db.secret.delete({
            where: {
                ownerId_name: { ownerId, name },
            },
        });
        return true;
    }

    async findByName(ownerId: string, name: string): Promise<Secret | null> {
        return this.db.secret.findUnique({
            where: {
                ownerId_name: { ownerId, name },
            },
        });
    }
}
