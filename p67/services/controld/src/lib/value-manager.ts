import type { PrismaClient } from '@p67/db';
import { decrypt, encrypt } from './crypto.js';
import type { Value } from './manifest';
import {
    getKnownProvider,
    isTokenExpiringSoon,
    type OAuthToken,
    parseOAuthToken,
    refreshOAuthToken,
    serializeOAuthToken,
} from './oauth/index.js';

/**
 * Configuration for OAuth token refresh
 * Required when using oauthRef values
 */
export interface OAuthRefreshConfig {
    clientId: string;
    clientSecret: string;
}

/**
 * ValueManager is a class that manages the values of the config, looking
 * references up in a KV store and decrypting secrets if necessary.
 */
export class ValueManager {
    private kvMap: Map<string, string>;
    private db: PrismaClient;
    private userId: string;
    private oauthRefreshConfigs: Map<string, OAuthRefreshConfig>;

    constructor(db: PrismaClient, userId: string) {
        this.db = db;
        this.userId = userId;
        // TODO: populate.
        this.kvMap = new Map<string, string>();
        this.oauthRefreshConfigs = new Map<string, OAuthRefreshConfig>();
    }

    /**
     * Register OAuth refresh credentials for a provider
     * Required for automatic token refresh to work
     */
    setOAuthRefreshConfig(provider: string, config: OAuthRefreshConfig): void {
        this.oauthRefreshConfigs.set(provider.toLowerCase(), config);
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
        if (value.oauthRef) {
            return this.getOAuthToken(value.oauthRef);
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

    /**
     * Get an OAuth access token, refreshing if necessary
     */
    async getOAuthToken(oauthRef: string): Promise<string> {
        const encryptedSecret = await this.getSecret(oauthRef);
        const decrypted = await this.decryptSecret(encryptedSecret);

        let oauth: OAuthToken;
        try {
            oauth = parseOAuthToken(decrypted);
        } catch {
            throw new Error(
                `Invalid OAuth token format for "${oauthRef}". ` +
                    `Expected JSON with access_token field. ` +
                    `Run "p67 oauth connect" to set up OAuth credentials.`,
            );
        }

        // Check if token is expired or expiring soon
        if (isTokenExpiringSoon(oauth.expires_at)) {
            if (oauth.refresh_token) {
                try {
                    oauth = await this.refreshAndSaveToken(oauthRef, oauth);
                } catch (error) {
                    throw new Error(
                        `Failed to refresh OAuth token "${oauthRef}": ${error instanceof Error ? error.message : String(error)}. ` +
                            `Run "p67 oauth connect" to re-authenticate.`,
                    );
                }
            } else {
                throw new Error(
                    `OAuth token "${oauthRef}" has expired and no refresh token is available. ` +
                        `Run "p67 oauth connect" to re-authenticate.`,
                );
            }
        }

        return oauth.access_token;
    }

    /**
     * Refresh an OAuth token and save it back to the database
     */
    private async refreshAndSaveToken(
        secretName: string,
        currentToken: OAuthToken,
    ): Promise<OAuthToken> {
        if (!currentToken.refresh_token) {
            throw new Error('No refresh token available');
        }

        // Get provider config for token URL
        const provider = getKnownProvider(currentToken.provider);
        if (!provider) {
            throw new Error(
                `Unknown OAuth provider "${currentToken.provider}". Cannot refresh token.`,
            );
        }

        // Get client credentials for this provider
        const refreshConfig = this.oauthRefreshConfigs.get(
            currentToken.provider.toLowerCase(),
        );
        if (!refreshConfig) {
            throw new Error(
                `No OAuth refresh credentials configured for provider "${currentToken.provider}". ` +
                    `Token refresh is not available.`,
            );
        }

        // Refresh the token
        const refreshed = await refreshOAuthToken({
            refreshToken: currentToken.refresh_token,
            clientId: refreshConfig.clientId,
            clientSecret: refreshConfig.clientSecret,
            tokenUrl: provider.tokenUrl,
        });

        // Preserve provider and scopes from original token
        refreshed.provider = currentToken.provider;
        refreshed.scopes = refreshed.scopes || currentToken.scopes;

        // Save back to database
        const encryptedToken = encrypt(serializeOAuthToken(refreshed));
        await this.db.secret.update({
            where: {
                ownerId_name: { ownerId: this.userId, name: secretName },
            },
            data: {
                secret: encryptedToken,
                updatedAt: new Date(),
            },
        });

        return refreshed;
    }

    /**
     * Get the full OAuth token object (not just access_token)
     * Useful for inspecting token metadata
     */
    async getOAuthTokenData(oauthRef: string): Promise<OAuthToken> {
        const encryptedSecret = await this.getSecret(oauthRef);
        const decrypted = await this.decryptSecret(encryptedSecret);
        return parseOAuthToken(decrypted);
    }
}
