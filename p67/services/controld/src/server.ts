import { loadConfig, type ServerConfig } from '@controld/config.js';
import { initCrypto } from '@controld/lib/crypto.js';
import { LogService } from '@controld/lib/LogService.js';
import userPlugin from '@controld/lib/plugins/user.js';
import { SecretService } from '@controld/lib/SecretService.js';
import { WorkflowService } from '@controld/lib/WorkflowService.js';
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
        workflowService: WorkflowService;
        secretService: SecretService;
        logService: LogService;
    }
}

export async function buildServer(): Promise<FastifyInstance> {
    const config = loadConfig();

    // Initialize encryption for secrets
    if (config.encryption.key) {
        initCrypto(config.encryption.key);
    } else {
        console.warn(
            '⚠️  ENCRYPTION_KEY not set - secret encryption/decryption will fail',
        );
    }

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

    // Register workflow service
    server.decorate(
        'workflowService',
        new WorkflowService({
            db: server.db,
            localStoragePath: server.config.localStoragePath,
        }),
    );

    // Register secret service
    server.decorate(
        'secretService',
        new SecretService({
            db: server.db,
        }),
    );

    // Register log service
    server.decorate(
        'logService',
        new LogService({
            db: server.db,
        }),
    );

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
