import {
    type OAuthProviderConfig,
    type OAuthToken,
    OAuthTokenResponseSchema,
    OAuthTokenSchema,
    type RefreshTokenRequest,
} from './types.js';

/**
 * Refresh an OAuth token using the refresh token
 */
export async function refreshOAuthToken(
    request: RefreshTokenRequest,
): Promise<OAuthToken> {
    const params = new URLSearchParams({
        grant_type: 'refresh_token',
        refresh_token: request.refreshToken,
        client_id: request.clientId,
        client_secret: request.clientSecret,
    });

    const response = await fetch(request.tokenUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            Accept: 'application/json',
        },
        body: params.toString(),
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
            `Token refresh failed: ${response.status} ${errorText}`,
        );
    }

    const data = OAuthTokenResponseSchema.parse(await response.json());

    // Calculate expires_at from expires_in
    let expiresAt: string | undefined;
    if (data.expires_in) {
        const expiresAtDate = new Date(Date.now() + data.expires_in * 1000);
        expiresAt = expiresAtDate.toISOString();
    }

    return {
        access_token: data.access_token,
        refresh_token: data.refresh_token || request.refreshToken, // Keep old refresh token if not provided
        token_type: data.token_type || 'bearer',
        expires_at: expiresAt,
        scopes: data.scope?.split(' '),
        provider: 'unknown', // Caller should set this
    };
}

/**
 * Check if a token is expired or expiring soon
 * @param expiresAt ISO 8601 timestamp
 * @param bufferMs Buffer time in milliseconds (default 5 minutes)
 */
export function isTokenExpiringSoon(
    expiresAt: string | undefined,
    bufferMs: number = 5 * 60 * 1000,
): boolean {
    if (!expiresAt) {
        return false; // No expiry means it doesn't expire
    }

    const expiresAtMs = new Date(expiresAt).getTime();
    const nowMs = Date.now();

    return expiresAtMs - nowMs < bufferMs;
}

/**
 * Parse and validate an OAuth token from JSON string
 */
export function parseOAuthToken(json: string): OAuthToken {
    const data = JSON.parse(json);
    return OAuthTokenSchema.parse(data);
}

/**
 * Serialize an OAuth token to JSON string
 */
export function serializeOAuthToken(token: OAuthToken): string {
    return JSON.stringify(token);
}

/**
 * Exchange authorization code for tokens
 */
export async function exchangeCodeForTokens(
    code: string,
    provider: OAuthProviderConfig,
    clientId: string,
    clientSecret: string,
    redirectUri: string,
): Promise<OAuthToken> {
    const params = new URLSearchParams({
        grant_type: 'authorization_code',
        code,
        client_id: clientId,
        client_secret: clientSecret,
        redirect_uri: redirectUri,
        ...provider.extraTokenParams,
    });

    const response = await fetch(provider.tokenUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            Accept: 'application/json',
        },
        body: params.toString(),
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
            `Token exchange failed: ${response.status} ${errorText}`,
        );
    }

    const data = OAuthTokenResponseSchema.parse(await response.json());

    // Calculate expires_at from expires_in
    let expiresAt: string | undefined;
    if (data.expires_in) {
        const expiresAtDate = new Date(Date.now() + data.expires_in * 1000);
        expiresAt = expiresAtDate.toISOString();
    }

    return {
        access_token: data.access_token,
        refresh_token: data.refresh_token,
        token_type: data.token_type || 'bearer',
        expires_at: expiresAt,
        scopes: data.scope?.split(' ') || provider.defaultScopes,
        provider: provider.name.toLowerCase(),
    };
}

/**
 * Build the authorization URL for OAuth flow
 */
export function buildAuthorizationUrl(
    provider: OAuthProviderConfig,
    clientId: string,
    redirectUri: string,
    scopes: string[],
    state: string,
): string {
    const params = new URLSearchParams({
        client_id: clientId,
        redirect_uri: redirectUri,
        response_type: 'code',
        scope: scopes.join(' '),
        state,
        ...provider.extraAuthParams,
    });

    return `${provider.authorizationUrl}?${params.toString()}`;
}
