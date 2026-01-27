import { z } from 'zod';

/**
 * OAuth token data stored in secrets
 */
export const OAuthTokenSchema = z.object({
    access_token: z.string(),
    refresh_token: z.string().optional(),
    token_type: z.string().default('bearer'),
    expires_at: z.string().optional(), // ISO 8601 timestamp
    scopes: z.array(z.string()).optional(),
    provider: z.string(),
    // Provider-specific metadata
    metadata: z.record(z.string(), z.unknown()).optional(),
});

export type OAuthToken = z.infer<typeof OAuthTokenSchema>;

/**
 * Provider configuration for known OAuth providers
 */
export interface OAuthProviderConfig {
    name: string;
    authorizationUrl: string;
    tokenUrl: string;
    defaultScopes: string[];
    supportsRefresh: boolean;
    // Extra params to include in authorization URL
    extraAuthParams?: Record<string, string>;
    // Extra params to include in token request
    extraTokenParams?: Record<string, string>;
}

/**
 * Known OAuth providers with pre-configured settings
 */
export const KNOWN_PROVIDERS: Record<string, OAuthProviderConfig> = {
    github: {
        name: 'GitHub',
        authorizationUrl: 'https://github.com/login/oauth/authorize',
        tokenUrl: 'https://github.com/login/oauth/access_token',
        defaultScopes: ['repo', 'read:user'],
        supportsRefresh: false, // GitHub OAuth apps don't support refresh tokens
    },
    google: {
        name: 'Google',
        authorizationUrl: 'https://accounts.google.com/o/oauth2/v2/auth',
        tokenUrl: 'https://oauth2.googleapis.com/token',
        defaultScopes: ['openid', 'email', 'profile'],
        supportsRefresh: true,
        extraAuthParams: {
            access_type: 'offline',
            prompt: 'consent',
        },
    },
    slack: {
        name: 'Slack',
        authorizationUrl: 'https://slack.com/oauth/v2/authorize',
        tokenUrl: 'https://slack.com/api/oauth.v2.access',
        defaultScopes: ['chat:write', 'users:read'],
        supportsRefresh: true,
    },
    microsoft: {
        name: 'Microsoft',
        authorizationUrl:
            'https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
        tokenUrl: 'https://login.microsoftonline.com/common/oauth2/v2.0/token',
        defaultScopes: ['openid', 'profile', 'email', 'offline_access'],
        supportsRefresh: true,
    },
    linear: {
        name: 'Linear',
        authorizationUrl: 'https://linear.app/oauth/authorize',
        tokenUrl: 'https://api.linear.app/oauth/token',
        defaultScopes: ['read', 'write'],
        supportsRefresh: true,
    },
    notion: {
        name: 'Notion',
        authorizationUrl: 'https://api.notion.com/v1/oauth/authorize',
        tokenUrl: 'https://api.notion.com/v1/oauth/token',
        defaultScopes: [], // Notion doesn't use traditional scopes
        supportsRefresh: false,
    },
};

/**
 * Get a known provider config by name
 */
export function getKnownProvider(
    name: string,
): OAuthProviderConfig | undefined {
    return KNOWN_PROVIDERS[name.toLowerCase()];
}

/**
 * Check if a provider is known
 */
export function isKnownProvider(name: string): boolean {
    return name.toLowerCase() in KNOWN_PROVIDERS;
}

/**
 * List all known provider names
 */
export function listKnownProviders(): string[] {
    return Object.keys(KNOWN_PROVIDERS);
}

/**
 * OAuth token refresh request
 */
export interface RefreshTokenRequest {
    refreshToken: string;
    clientId: string;
    clientSecret: string;
    tokenUrl: string;
}

/**
 * OAuth token response from provider
 */
export const OAuthTokenResponseSchema = z.object({
    access_token: z.string(),
    refresh_token: z.string().optional(),
    token_type: z.string().optional(),
    expires_in: z.number().optional(), // seconds until expiry
    scope: z.string().optional(), // space-separated scopes
});

export type OAuthTokenResponse = z.infer<typeof OAuthTokenResponseSchema>;
