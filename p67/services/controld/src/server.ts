import { loadConfig, type ServerConfig } from '@controld/config.js';
import userPlugin from '@controld/lib/plugins/user';
import cors from '@fastify/cors';
import multipart from '@fastify/multipart';
import swagger from '@fastify/swagger';
import swaggerUi from '@fastify/swagger-ui';
import { databasePlugin } from '@p67/db';
import Fastify, { type FastifyInstance } from 'fastify';
import {
	serializerCompiler,
	validatorCompiler,
	type ZodTypeProvider,
} from 'fastify-type-provider-zod';

declare module 'fastify' {
	interface FastifyInstance {
		config: ServerConfig;
	}
}

export async function buildServer(): Promise<FastifyInstance> {
	const config = loadConfig();

	const server = Fastify({
		logger: {
			level: 'debug',
			transport: {
				target: 'pino-pretty',
				options: {
					translateTime: 'SYS:standard',
					singleLine: false,
				},
			},
		},
	}).withTypeProvider<ZodTypeProvider>();

	server.decorate('config', config);
	server.setValidatorCompiler(validatorCompiler);
	server.setSerializerCompiler(serializerCompiler);

	// Register database plugin
	await server.register(databasePlugin, {
		databaseUrl: config.database.url,
	});

	await server.register(multipart);

	await server.register(cors, {
		origin: true,
	});

	await server.register(swagger, {
		openapi: {
			info: {
				title: 'P67 Controld API',
				description: 'Control plane service API',
				version: '1.0.0',
			},
			servers: [
				{
					url: `http://localhost:${config.port}`,
					description: 'Development server',
				},
			],
		},
	});

	await server.register(swaggerUi, {
		routePrefix: '/docs',
	});

	await server.register(userPlugin, {
		setDefaultUser: config.debug.enableDefaultUser,
		defaultUser: config.debug.defaultUser,
	});

	return server;
}
