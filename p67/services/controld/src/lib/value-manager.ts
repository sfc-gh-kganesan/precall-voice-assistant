import type { PrismaClient } from '@p67/db';
import { decrypt } from './crypto.js';
import type { Value } from './manifest';
/**
 * ValueManager is a class that manages the values of the config, looking
 * references up in a KV store and decrypting secrets if necessary.
 */
export class ValueManager {
    private kvMap: Map<string, string>;
    private db: PrismaClient;
    private userId: string;

    constructor(db: PrismaClient, userId: string) {
        this.db = db;
        this.userId = userId;
        // TODO: populate.
        this.kvMap = new Map<string, string>();
    }

    async get(value?: Value): Promise<string | undefined> {
        if (!value) {
            return undefined;
        }
        if (value.value) {
            return value.value;
        }
        if (value.valueRef) {
            return this.getValue(value.valueRef);
        }
        if (value.secretRef) {
            const secret = await this.getSecret(value.secretRef);
            const decryptedSecret = await this.decryptSecret(secret);
            return decryptedSecret;
        }
        throw new Error(`Invalid value: ${JSON.stringify(value)}`);
    }

    async getValue(valueRef: string): Promise<string> {
        const value = this.kvMap.get(valueRef);
        if (!value) {
            throw new Error(`Value not found: ${valueRef}`);
        }
        return value;
    }

    async getSecret(secretRef: string): Promise<string> {
        const secret = await this.db.secret.findFirst({
            where: {
                ownerId: this.userId,
                OR: [{ name: secretRef }, { id: secretRef }],
            },
        });

        if (!secret) {
            throw new Error(`Secret not found: ${secretRef}`);
        }
        return secret.secret;
    }

    async decryptSecret(secret: string): Promise<string> {
        return decrypt(secret);
    }
}
