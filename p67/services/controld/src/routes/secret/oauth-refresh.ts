import { decrypt, encrypt } from '@controld/lib/crypto.js';
import {
    getKnownProvider,
    isTokenExpiringSoon,
    type OAuthToken,
    OAuthTokenSchema,
    refreshOAuthToken,
    serializeOAuthToken,
} from '@controld/lib/oauth/index.js';
import {
    ErrorResponseSchema,
    OAuthRefreshBodySchema,
    OAuthRefreshResponseSchema,
} from '@controld/schema.js';
import type { FastifyInstance } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';

export function registerOAuthRefreshRoute(server: FastifyInstance) {
    const fastify = server.withTypeProvider<ZodTypeProvider>();

    fastify.post(
        '/oauth/refresh',
        {
            schema: {
                description: 'Refresh an OAuth token stored as a secret',
                tags: ['Secret', 'OAuth'],
                body: OAuthRefreshBodySchema,
                response: {
                    200: OAuthRefreshResponseSchema,
                    400: ErrorResponseSchema,
                    404: ErrorResponseSchema,
                    500: ErrorResponseSchema,
                },
            },
        },
        async (request, reply) => {
            try {
                const { name, clientId, clientSecret } = request.body;

                // Get the secret
                const secret = await fastify.secretService.findByName(
                    request.user.id,
                    name,
                );

                if (!secret) {
                    return reply.code(404).send({
                        error: 'Not found',
                        message: `Secret '${name}' not found`,
                    });
                }

                // Decrypt and parse as OAuth token
                const decryptedValue = decrypt(secret.secret);
                let oauthToken: OAuthToken;

                try {
                    oauthToken = OAuthTokenSchema.parse(
                        JSON.parse(decryptedValue),
                    );
                } catch {
                    return reply.code(400).send({
                        error: 'Invalid OAuth token',
                        message: `Secret '${name}' is not a valid OAuth token`,
                    });
                }

                // Check if refresh is needed
                if (!isTokenExpiringSoon(oauthToken.expires_at, 0)) {
                    // Token is still valid, return without refreshing
                    return reply.code(200).send({
                        name,
                        provider: oauthToken.provider,
                        expiresAt: oauthToken.expires_at || null,
                        refreshed: false,
                    });
                }

                // Check if we have a refresh token
                if (!oauthToken.refresh_token) {
                    return reply.code(400).send({
                        error: 'Cannot refresh',
                        message:
                            'Token has no refresh_token. Re-authenticate with "p67 oauth connect".',
                    });
                }

                // Get provider config
                const provider = getKnownProvider(oauthToken.provider);
                if (!provider) {
                    return reply.code(400).send({
                        error: 'Unknown provider',
                        message: `Cannot refresh token for unknown provider '${oauthToken.provider}'`,
                    });
                }

                // Refresh the token
                const refreshed = await refreshOAuthToken({
                    refreshToken: oauthToken.refresh_token,
                    clientId,
                    clientSecret,
                    tokenUrl: provider.tokenUrl,
                });

                // Preserve provider and scopes
                refreshed.provider = oauthToken.provider;
                refreshed.scopes = refreshed.scopes || oauthToken.scopes;

                // Save the refreshed token
                const encryptedToken = encrypt(serializeOAuthToken(refreshed));
                await fastify.db.secret.update({
                    where: {
                        ownerId_name: {
                            ownerId: request.user.id,
                            name,
                        },
                    },
                    data: {
                        secret: encryptedToken,
                        updatedAt: new Date(),
                    },
                });

                return reply.code(200).send({
                    name,
                    provider: refreshed.provider,
                    expiresAt: refreshed.expires_at || null,
                    refreshed: true,
                });
            } catch (error) {
                console.error('Error refreshing OAuth token:', error);
                return reply.code(500).send({
                    error: 'Refresh failed',
                    message:
                        error instanceof Error
                            ? error.message
                            : 'Unknown error',
                });
            }
        },
    );
}
