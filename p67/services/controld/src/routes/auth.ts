import { FastifyInstance } from 'fastify';
import { ZodTypeProvider } from 'fastify-type-provider-zod';
import { OAuthCallbackQuerySchema, OAuthCallbackResponse } from '@controld/schema.js';
import { GoogleOAuthClient } from '@controld/lib/oauth/google-client.js';

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
        const { accessToken } = await googleClient.exchangeCodeForTokens(code);

        // Fetch user info
        const userInfo = await googleClient.getUserInfo(accessToken);

        // Render success page with user info
        return reply.code(200).send({
          name: userInfo.name,
          email: userInfo.email,
          picture: userInfo.picture,
        });
      } catch (error) {
        return reply
          .code(400)
          .send({ error: error instanceof Error ? error.message : String(error) });
      }
    },
  );
};

export default authRoutes;
