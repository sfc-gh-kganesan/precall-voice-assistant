import { type WhoamiResponse, WhoamiResponseSchema } from '@controld/schema.js';
import type { FastifyPluginAsync } from 'fastify';

const whoami: FastifyPluginAsync = async (fastify) => {
	fastify.get(
		'/',
		{
			schema: {
				tags: ['Auth'],
				summary: 'Get current user information',
				description: 'Returns information about the currently logged in user',
				response: {
					200: WhoamiResponseSchema,
				},
			},
		},
		async (req, _): Promise<WhoamiResponse> => {
			const user = req.user;

			const result: WhoamiResponse = {
				id: user.id,
				snowflakeUser: user.snowflakeUser,
			};

			return result;
		},
	);
};

export default whoami;
