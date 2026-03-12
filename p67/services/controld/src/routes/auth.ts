import { GoogleOAuthClient } from '@controld/lib/oauth/google-client.js';
import { pendingLinkTokens } from '@controld/lib/slack-commands.js';
import {
    OAuthCallbackQuerySchema,
    OAuthCallbackResponse,
} from '@controld/schema.js';
import type { FastifyInstance } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';
import { z } from 'zod';

const SlackLinkQuerySchema = z.object({
    token: z.string(),
    slack_user: z.string(),
    slack_team: z.string(),
});

const authRoutes = async (server: FastifyInstance) => {
    const fastify = server.withTypeProvider<ZodTypeProvider>();
    const { config } = fastify;

    const googleClient = new GoogleOAuthClient(config.oauth.google);

    // GET /api/auth/google/authorize
    fastify.get(
        '/google/authorize',
        {
            schema: {
                description: 'Initiate Google OAuth flow',
                tags: ['Auth'],
            },
        },
        async (_, reply) => {
            const authUrl = googleClient.buildAuthorizationUrl();
            return reply.redirect(authUrl);
        },
    );

    // GET /api/auth/google/callback
    fastify.get(
        '/google/callback',
        {
            schema: {
                description: 'Handle Google OAuth callback',
                tags: ['Auth'],
                querystring: OAuthCallbackQuerySchema,
                response: {
                    200: OAuthCallbackResponse,
                    400: OAuthCallbackResponse,
                },
            },
        },
        async (request, reply) => {
            try {
                const { code, error, error_description } = request.query as {
                    code?: string;
                    error?: string;
                    error_description?: string;
                };

                // Handle OAuth errors from Google
                if (error) {
                    reply.code(400).send({
                        error: `${error} (${error_description})`,
                    });
                }

                if (!code) {
                    return reply.code(400).send({
                        error: 'Missing authorization code',
                    });
                }

                // Exchange code for access token
                const { accessToken } =
                    await googleClient.exchangeCodeForTokens(code);

                // Fetch user info
                const userInfo = await googleClient.getUserInfo(accessToken);

                // Render success page with user info
                return reply.code(200).send({
                    name: userInfo.name,
                    email: userInfo.email,
                    picture: userInfo.picture,
                });
            } catch (error) {
                console.log('🦊 Uh oh:', error);
                return reply.code(400).send({
                    error:
                        error instanceof Error ? error.message : String(error),
                });
            }
        },
    );

    // GET /api/auth/slack/link
    // Complete the Slack account linking process
    // User clicks the link URL from /p67-workflow link command, Snowflake auth
    // identifies them via sf-context-current-user header, and we create the mapping.
    fastify.get(
        '/slack/link',
        {
            schema: {
                description: 'Complete Slack account linking',
                tags: ['Auth'],
                querystring: SlackLinkQuerySchema,
            },
        },
        async (request, reply) => {
            const htmlResponse = (
                title: string,
                message: string,
                success: boolean,
            ) => {
                const color = success ? '#2ea44f' : '#d1242f';
                return reply.type('text/html').send(`<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>${title}</title>
<style>body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;background:#f6f8fa}
.card{background:#fff;border:1px solid #d0d7de;border-radius:12px;padding:40px;max-width:480px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.1)}
h1{color:${color};margin:0 0 16px}p{color:#57606a;line-height:1.5}</style></head>
<body><div class="card"><h1>${title}</h1><p>${message}</p></div></body></html>`);
            };

            try {
                const { token, slack_user, slack_team } = request.query as {
                    token: string;
                    slack_user: string;
                    slack_team: string;
                };

                const pendingLink = pendingLinkTokens.get(token);
                if (!pendingLink) {
                    return htmlResponse(
                        'Link Expired',
                        'This link is invalid or has expired. Please run <code>/p67-workflow link</code> again in Slack.',
                        false,
                    );
                }

                if (
                    pendingLink.slackUserId !== slack_user ||
                    pendingLink.slackTeamId !== slack_team
                ) {
                    return htmlResponse(
                        'Link Error',
                        'Token mismatch. Please run <code>/p67-workflow link</code> again in Slack.',
                        false,
                    );
                }

                if (pendingLink.expiresAt < Date.now()) {
                    pendingLinkTokens.delete(token);
                    return htmlResponse(
                        'Link Expired',
                        'This link has expired. Please run <code>/p67-workflow link</code> again in Slack.',
                        false,
                    );
                }

                const userId = request.user?.id;
                if (!userId) {
                    return htmlResponse(
                        'Authentication Required',
                        'Could not identify your Snowflake user. Please ensure you are signed in.',
                        false,
                    );
                }

                await fastify.db.slackUser.upsert({
                    where: {
                        slackUserId_slackTeamId: {
                            slackUserId: slack_user,
                            slackTeamId: slack_team,
                        },
                    },
                    update: {
                        userId,
                        slackUsername: pendingLink.slackUsername,
                        updatedAt: new Date(),
                    },
                    create: {
                        slackUserId: slack_user,
                        slackTeamId: slack_team,
                        slackUsername: pendingLink.slackUsername,
                        userId,
                    },
                });

                pendingLinkTokens.delete(token);

                return htmlResponse(
                    'Account Linked!',
                    `Your Slack account (<strong>${pendingLink.slackUsername}</strong>) has been linked to your Snowflake identity (<strong>${request.user.snowflakeUser}</strong>). You can close this tab and return to Slack.`,
                    true,
                );
            } catch (error) {
                console.error('Error linking Slack account:', error);
                return htmlResponse(
                    'Error',
                    'Something went wrong. Please try again.',
                    false,
                );
            }
        },
    );
};

export default authRoutes;
