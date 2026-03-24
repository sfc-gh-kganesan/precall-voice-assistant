import type { PrismaClient, Secret, SecretType } from '@p67/db';
import { encrypt } from './crypto.js';

export interface SecretServiceConfig {
    db: PrismaClient;
}

export interface SaveSecretResult {
    name: string;
    created: boolean;
}

export interface SecretMetadata {
    name: string;
    type: SecretType;
    createdAt: Date;
    updatedAt: Date;
}

/**
 * @deprecated Use SECRET_BACKEND=snowflake with Snowflake SECRET objects.
 * This service stores user secrets in Postgres with AES-256-GCM encryption.
 * It will be removed once all deployments migrate to the Snowflake secret backend.
 */
export class SecretService {
    private db: PrismaClient;

    constructor(config: SecretServiceConfig) {
        this.db = config.db;
    }

    async save(
        ownerId: string,
        name: string,
        secret: string,
        type: SecretType = 'Secret',
    ): Promise<SaveSecretResult> {
        const existing = await this.findByName(ownerId, name);

        const encryptedSecret = encrypt(secret);

        if (existing) {
            await this.db.secret.update({
                where: {
                    ownerId_name: { ownerId, name },
                },
                data: {
                    secret: encryptedSecret,
                    type,
                    updatedAt: new Date(),
                },
            });
            return { name, created: false };
        }

        await this.db.secret.create({
            data: {
                name,
                secret: encryptedSecret,
                type,
                ownerId,
            },
        });
        return { name, created: true };
    }

    async list(ownerId: string, type?: SecretType): Promise<SecretMetadata[]> {
        const secrets = await this.db.secret.findMany({
            where: {
                ownerId,
                ...(type ? { type } : {}),
            },
            select: {
                name: true,
                type: true,
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
