// Re-export existing Google client for backwards compatibility
export { GoogleOAuthClient, type GoogleOAuthConfig } from './google-client.js';

export {
    buildAuthorizationUrl,
    exchangeCodeForTokens,
    isTokenExpiringSoon,
    parseOAuthToken,
    refreshOAuthToken,
    serializeOAuthToken,
} from './oauth-client.js';
export {
    getKnownProvider,
    isKnownProvider,
    KNOWN_PROVIDERS,
    listKnownProviders,
    type OAuthProviderConfig,
    type OAuthToken,
    type OAuthTokenResponse,
    OAuthTokenResponseSchema,
    OAuthTokenSchema,
    type RefreshTokenRequest,
} from './types.js';
