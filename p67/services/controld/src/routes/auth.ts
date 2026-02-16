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

const SlackLinkResponseSchema = z.object({
    success: z.boolean(),
    message: z.string(),
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

    // POST /api/auth/slack/link
    // Complete the Slack account linking process
    // Called when user clicks the link URL from /workflow link command
    fastify.post(
        '/slack/link',
        {
            schema: {
                description: 'Complete Slack account linking',
                tags: ['Auth'],
                querystring: SlackLinkQuerySchema,
                response: {
                    200: SlackLinkResponseSchema,
                    400: SlackLinkResponseSchema,
                },
            },
        },
        async (request, reply) => {
            try {
                const { token, slack_user, slack_team } = request.query as {
                    token: string;
                    slack_user: string;
                    slack_team: string;
                };

                // Validate the link token
                const pendingLink = pendingLinkTokens.get(token);
                if (!pendingLink) {
                    return reply.code(400).send({
                        success: false,
                        message:
                            'Invalid or expired link token. Please run /workflow link again.',
                    });
                }

                // Verify the token matches the Slack user info
                if (
                    pendingLink.slackUserId !== slack_user ||
                    pendingLink.slackTeamId !== slack_team
                ) {
                    return reply.code(400).send({
                        success: false,
                        message:
                            'Link token mismatch. Please run /workflow link again.',
                    });
                }

                // Check if token has expired
                if (pendingLink.expiresAt < Date.now()) {
                    pendingLinkTokens.delete(token);
                    return reply.code(400).send({
                        success: false,
                        message:
                            'Link token has expired. Please run /workflow link again.',
                    });
                }

                // Get the authenticated user from the request
                const userId = request.user?.id;
                if (!userId) {
                    return reply.code(400).send({
                        success: false,
                        message:
                            'You must be logged in to link your Slack account.',
                    });
                }

                // Check if this Slack user is already linked to a different P67 user
                const existingLink = await fastify.db.slackUser.findUnique({
                    where: {
                        slackUserId_slackTeamId: {
                            slackUserId: slack_user,
                            slackTeamId: slack_team,
                        },
                    },
                });

                if (existingLink && existingLink.userId !== userId) {
                    return reply.code(400).send({
                        success: false,
                        message:
                            'This Slack account is already linked to a different P67 user.',
                    });
                }

                // Create or update the link
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

                // Clean up the pending token
                pendingLinkTokens.delete(token);

                return reply.code(200).send({
                    success: true,
                    message:
                        'Your Slack account has been linked successfully! You can now use /workflow commands.',
                });
            } catch (error) {
                console.error('Error linking Slack account:', error);
                return reply.code(400).send({
                    success: false,
                    message:
                        error instanceof Error
                            ? error.message
                            : 'Failed to link account',
                });
            }
        },
    );
};

export default authRoutes;
