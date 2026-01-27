import { randomBytes } from 'node:crypto';
import { createServer, type Server } from 'node:http';
import { Command } from '@p67-cli/Command.ts';
import { ControldClient } from '@p67-cli/clients/ControldClient.ts';
import { ctx } from '@p67-cli/context';

/**
 * Known OAuth provider configurations
 */
const KNOWN_PROVIDERS: Record<
    string,
    {
        name: string;
        authorizationUrl: string;
        tokenUrl: string;
        defaultScopes: string[];
        extraAuthParams?: Record<string, string>;
    }
> = {
    github: {
        name: 'GitHub',
        authorizationUrl: 'https://github.com/login/oauth/authorize',
        tokenUrl: 'https://github.com/login/oauth/access_token',
        defaultScopes: ['repo', 'read:user'],
    },
    google: {
        name: 'Google',
        authorizationUrl: 'https://accounts.google.com/o/oauth2/v2/auth',
        tokenUrl: 'https://oauth2.googleapis.com/token',
        defaultScopes: ['openid', 'email', 'profile'],
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
    },
    microsoft: {
        name: 'Microsoft',
        authorizationUrl:
            'https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
        tokenUrl: 'https://login.microsoftonline.com/common/oauth2/v2.0/token',
        defaultScopes: ['openid', 'profile', 'email', 'offline_access'],
    },
    linear: {
        name: 'Linear',
        authorizationUrl: 'https://linear.app/oauth/authorize',
        tokenUrl: 'https://api.linear.app/oauth/token',
        defaultScopes: ['read', 'write'],
    },
};

interface OAuthTokenResponse {
    access_token: string;
    refresh_token?: string;
    token_type?: string;
    expires_in?: number;
    scope?: string;
}

/**
 * Exchange authorization code for tokens
 */
async function exchangeCodeForTokens(
    code: string,
    tokenUrl: string,
    clientId: string,
    clientSecret: string,
    redirectUri: string,
): Promise<OAuthTokenResponse> {
    const params = new URLSearchParams({
        grant_type: 'authorization_code',
        code,
        client_id: clientId,
        client_secret: clientSecret,
        redirect_uri: redirectUri,
    });

    const response = await fetch(tokenUrl, {
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

    return (await response.json()) as OAuthTokenResponse;
}

/**
 * Build the authorization URL
 */
function buildAuthorizationUrl(
    authorizationUrl: string,
    clientId: string,
    redirectUri: string,
    scopes: string[],
    state: string,
    extraParams?: Record<string, string>,
): string {
    const params = new URLSearchParams({
        client_id: clientId,
        redirect_uri: redirectUri,
        response_type: 'code',
        scope: scopes.join(' '),
        state,
        ...extraParams,
    });

    return `${authorizationUrl}?${params.toString()}`;
}

/**
 * Get the callback server port
 */
function getServerPort(server: Server): number {
    const address = server.address();
    if (typeof address === 'object' && address) {
        return address.port;
    }
    throw new Error('Failed to get server port');
}

/**
 * Open URL in browser (cross-platform)
 */
async function openBrowser(url: string): Promise<void> {
    const { exec } = await import('node:child_process');
    const { promisify } = await import('node:util');
    const execAsync = promisify(exec);

    const platform = process.platform;
    let command: string;

    if (platform === 'darwin') {
        command = `open "${url}"`;
    } else if (platform === 'win32') {
        command = `start "${url}"`;
    } else {
        command = `xdg-open "${url}"`;
    }

    await execAsync(command);
}

export const connectCommand = new Command('connect')
    .description('Connect to an OAuth provider and store credentials')
    .argument(
        '<provider>',
        'OAuth provider (github, google, slack, microsoft, linear, or custom)',
    )
    .requiredOption('--secret-name <name>', 'Name to store the OAuth token as')
    .option(
        '--client-id <id>',
        'OAuth client ID (or set P67_OAUTH_CLIENT_ID env var)',
    )
    .option(
        '--client-secret <secret>',
        'OAuth client secret (or set P67_OAUTH_CLIENT_SECRET env var)',
    )
    .option(
        '--scopes <scopes>',
        'Comma-separated list of scopes (uses provider defaults if not specified)',
    )
    .option(
        '--port <port>',
        'Port for OAuth callback server (default: random available port)',
        parseInt,
    )
    .option(
        '--authorization-url <url>',
        'Authorization URL (required for custom provider)',
    )
    .option('--token-url <url>', 'Token URL (required for custom provider)')
    .action(
        async (
            provider: string,
            options: {
                secretName: string;
                clientId?: string;
                clientSecret?: string;
                scopes?: string;
                port?: number;
                authorizationUrl?: string;
                tokenUrl?: string;
            },
        ) => {
            try {
                const { connection } = ctx();
                const providerLower = provider.toLowerCase();

                // Resolve client credentials
                const clientId =
                    options.clientId || process.env.P67_OAUTH_CLIENT_ID;
                const clientSecret =
                    options.clientSecret || process.env.P67_OAUTH_CLIENT_SECRET;

                if (!clientId) {
                    throw new Error(
                        'Client ID is required. Provide --client-id or set P67_OAUTH_CLIENT_ID env var.',
                    );
                }

                if (!clientSecret) {
                    throw new Error(
                        'Client secret is required. Provide --client-secret or set P67_OAUTH_CLIENT_SECRET env var.',
                    );
                }

                // Get provider configuration
                let authorizationUrl: string;
                let tokenUrl: string;
                let scopes: string[];
                let extraAuthParams: Record<string, string> | undefined;
                let providerName: string;

                if (providerLower === 'custom') {
                    if (!options.authorizationUrl || !options.tokenUrl) {
                        throw new Error(
                            'Custom provider requires --authorization-url and --token-url',
                        );
                    }
                    authorizationUrl = options.authorizationUrl;
                    tokenUrl = options.tokenUrl;
                    scopes =
                        options.scopes?.split(',').map((s) => s.trim()) || [];
                    providerName = 'custom';
                } else {
                    const knownProvider = KNOWN_PROVIDERS[providerLower];
                    if (!knownProvider) {
                        const available =
                            Object.keys(KNOWN_PROVIDERS).join(', ');
                        throw new Error(
                            `Unknown provider: ${provider}. Available providers: ${available}, custom`,
                        );
                    }
                    authorizationUrl = knownProvider.authorizationUrl;
                    tokenUrl = knownProvider.tokenUrl;
                    scopes = options.scopes
                        ? options.scopes.split(',').map((s) => s.trim())
                        : knownProvider.defaultScopes;
                    extraAuthParams = knownProvider.extraAuthParams;
                    providerName = providerLower;
                }

                // Generate CSRF state token
                const state = randomBytes(32).toString('hex');

                // Start the callback server first to get the port
                console.log('Starting OAuth flow...');

                // Create a promise that will be resolved when we get the callback
                let resolveCallback: (result: {
                    code: string;
                    server: Server;
                }) => void;
                let rejectCallback: (error: Error) => void;
                const callbackPromise = new Promise<{
                    code: string;
                    server: Server;
                }>((resolve, reject) => {
                    resolveCallback = resolve;
                    rejectCallback = reject;
                });

                // Start the server
                const server = createServer((req, res) => {
                    const url = new URL(req.url || '', `http://localhost`);

                    if (url.pathname === '/callback') {
                        const code = url.searchParams.get('code');
                        const receivedState = url.searchParams.get('state');
                        const error = url.searchParams.get('error');

                        if (error) {
                            res.writeHead(400, { 'Content-Type': 'text/html' });
                            res.end(`
                                <html>
                                    <head><title>OAuth Error</title></head>
                                    <body style="font-family: system-ui; padding: 40px; text-align: center;">
                                        <h1>❌ Authorization Failed</h1>
                                        <p>Error: ${error}</p>
                                        <p style="color: #666;">You can close this window.</p>
                                    </body>
                                </html>
                            `);
                            rejectCallback(new Error(`OAuth error: ${error}`));
                            return;
                        }

                        if (receivedState !== state) {
                            res.writeHead(400, { 'Content-Type': 'text/html' });
                            res.end(`
                                <html>
                                    <head><title>OAuth Error</title></head>
                                    <body style="font-family: system-ui; padding: 40px; text-align: center;">
                                        <h1>❌ Authorization Failed</h1>
                                        <p>Invalid state parameter. Possible CSRF attack.</p>
                                        <p style="color: #666;">You can close this window.</p>
                                    </body>
                                </html>
                            `);
                            rejectCallback(
                                new Error('Invalid state parameter'),
                            );
                            return;
                        }

                        if (!code) {
                            res.writeHead(400, { 'Content-Type': 'text/html' });
                            res.end(`
                                <html>
                                    <head><title>OAuth Error</title></head>
                                    <body style="font-family: system-ui; padding: 40px; text-align: center;">
                                        <h1>❌ Authorization Failed</h1>
                                        <p>No authorization code received.</p>
                                        <p style="color: #666;">You can close this window.</p>
                                    </body>
                                </html>
                            `);
                            rejectCallback(
                                new Error('No authorization code received'),
                            );
                            return;
                        }

                        res.writeHead(200, { 'Content-Type': 'text/html' });
                        res.end(`
                            <html>
                                <head><title>OAuth Success</title></head>
                                <body style="font-family: system-ui; padding: 40px; text-align: center;">
                                    <h1>✅ Authorization Successful!</h1>
                                    <p>You can close this window and return to the terminal.</p>
                                    <script>setTimeout(() => window.close(), 2000);</script>
                                </body>
                            </html>
                        `);

                        resolveCallback({ code, server });
                    } else {
                        res.writeHead(404, { 'Content-Type': 'text/plain' });
                        res.end('Not found');
                    }
                });

                // Start listening - use specified port or 0 for random
                await new Promise<void>((resolve, reject) => {
                    server.on('error', (err: NodeJS.ErrnoException) => {
                        if (err.code === 'EADDRINUSE') {
                            reject(
                                new Error(
                                    `Port ${options.port} is already in use. Try a different port.`,
                                ),
                            );
                        } else {
                            reject(err);
                        }
                    });
                    server.listen(options.port || 0, '127.0.0.1', () =>
                        resolve(),
                    );
                });

                const port = getServerPort(server);
                const redirectUri = `http://localhost:${port}/callback`;

                if (options.port) {
                    console.log(`\nUsing callback URL: ${redirectUri}`);
                    console.log(
                        'Make sure this URL is registered in your OAuth app settings.\n',
                    );
                }

                // Build authorization URL
                const authUrl = buildAuthorizationUrl(
                    authorizationUrl,
                    clientId,
                    redirectUri,
                    scopes,
                    state,
                    extraAuthParams,
                );

                console.log(
                    `\nOpening browser for ${KNOWN_PROVIDERS[providerLower]?.name || 'OAuth'} authorization...`,
                );
                console.log(
                    `If the browser doesn't open, visit:\n${authUrl}\n`,
                );

                // Open browser
                await openBrowser(authUrl);

                // Set timeout
                const timeoutId = setTimeout(
                    () => {
                        server.close();
                        rejectCallback(
                            new Error(
                                'OAuth timeout: no callback received within 5 minutes',
                            ),
                        );
                    },
                    5 * 60 * 1000,
                );

                // Wait for callback
                console.log('Waiting for authorization...');
                const { code } = await callbackPromise;
                clearTimeout(timeoutId);

                console.log(
                    'Authorization code received. Exchanging for tokens...',
                );

                // Exchange code for tokens
                const tokenResponse = await exchangeCodeForTokens(
                    code,
                    tokenUrl,
                    clientId,
                    clientSecret,
                    redirectUri,
                );

                // Close the server
                server.close();

                // Build OAuth token object
                const oauthToken = {
                    access_token: tokenResponse.access_token,
                    refresh_token: tokenResponse.refresh_token,
                    token_type: tokenResponse.token_type || 'bearer',
                    expires_at: tokenResponse.expires_in
                        ? new Date(
                              Date.now() + tokenResponse.expires_in * 1000,
                          ).toISOString()
                        : undefined,
                    scopes: tokenResponse.scope?.split(' ') || scopes,
                    provider: providerName,
                };

                // Save to secrets
                const client = new ControldClient({
                    baseUrl: connection.endpoint,
                    pat: connection.pat,
                });

                const tokenJson = JSON.stringify(oauthToken);
                const result = await client.saveSecret(
                    options.secretName,
                    tokenJson,
                    'OAuth',
                );

                if (result.created) {
                    console.log(
                        `\n✓ OAuth token saved as secret '${result.name}'`,
                    );
                } else {
                    console.log(
                        `\n✓ OAuth token updated in secret '${result.name}'`,
                    );
                }

                console.log(`\nYou can now use this in your manifest:`);
                console.log(`  parameters:`);
                console.log(`    my_token:`);
                console.log(`      oauthRef: ${options.secretName}`);
                console.log(`\nOr in SDK:`);
                console.log(
                    `  sdk.httpRequest({ url: '...', oauthRef: '${options.secretName}' })`,
                );
            } catch (error) {
                console.error('OAuth connection failed');
                throw error;
            }
        },
    );
