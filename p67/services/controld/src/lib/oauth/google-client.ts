import {
    GoogleTokenResponseSchema,
    GoogleUserInfoSchema,
} from '@controld/schema.js';

const GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth';
const GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token';
const GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v2/userinfo';

export type GoogleOAuthConfig = {
    clientId: string;
    clientSecret: string;
    redirectUri: string;
};

export class GoogleOAuthClient {
    constructor(private readonly config: GoogleOAuthConfig) {}

    buildAuthorizationUrl(): string {
        const params = new URLSearchParams({
            client_id: this.config.clientId,
            redirect_uri: this.config.redirectUri,
            response_type: 'code',
            scope: 'openid profile email',
            access_type: 'online',
        });

        return `${GOOGLE_AUTH_URL}?${params.toString()}`;
    }

    async exchangeCodeForTokens(
        code: string,
    ): Promise<{ accessToken: string }> {
        const params = new URLSearchParams({
            code,
            client_id: this.config.clientId,
            client_secret: this.config.clientSecret,
            redirect_uri: this.config.redirectUri,
            grant_type: 'authorization_code',
        });

        const response = await fetch(GOOGLE_TOKEN_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: params.toString(),
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(`Token exchange failed: ${error}`);
        }

        const data = GoogleTokenResponseSchema.parse(await response.json());

        return {
            accessToken: data.access_token,
        };
    }

    async getUserInfo(accessToken: string): Promise<{
        name: string;
        email: string;
        picture: string;
    }> {
        const response = await fetch(GOOGLE_USERINFO_URL, {
            method: 'GET',
            headers: {
                Authorization: `Bearer ${accessToken}`,
            },
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(`Failed to fetch user info: ${error}`);
        }

        const data = GoogleUserInfoSchema.parse(await response.json());
        return {
            name: data.name,
            email: data.email,
            picture: data.picture,
        };
    }
}
