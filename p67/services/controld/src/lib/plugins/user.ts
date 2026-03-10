import type { UserModel } from '@p67/db';
import type { FastifyPluginAsync } from 'fastify';
import fp from 'fastify-plugin';

export interface UserPluginOptions {
    // Enable adding default user to request context.
    // WARNING: this should only be used in dev.
    setDefaultUser?: boolean;
    // Default value to set on SF_USER_HEADER request header if it
    // is not set on the incoming request. Will be used only if
    // setDefaultUser is set to true.
    defaultUser?: string;
}

declare module 'fastify' {
    interface FastifyRequest {
        user: UserModel;
    }

    interface FastifyContextConfig {
        skipAuth?: boolean;
    }
}

const SF_USER_HEADER = 'sf-context-current-user';

const userPlugin: FastifyPluginAsync<UserPluginOptions> = async (
    fastify,
    options,
) => {
    fastify.addHook('onRequest', async (request, _) => {
        // Skip auth for routes that opt out (e.g. webhooks)
        if (request.routeOptions.config?.skipAuth) {
            return;
        }

        const hasUserHeader = Object.hasOwn(request.headers, SF_USER_HEADER);

        if (!hasUserHeader && options.setDefaultUser && options.defaultUser) {
            request.headers[SF_USER_HEADER] = options.defaultUser;
        }
    });

    fastify.decorateRequest('user');
    fastify.addHook('onRequest', async (req, _) => {
        // Skip auth for routes that opt out (e.g. webhooks)
        if (req.routeOptions.config?.skipAuth) {
            return;
        }

        const userValue = req.headers[SF_USER_HEADER];
        if (!userValue) {
            throw new Error(`missing request header: ${SF_USER_HEADER}`);
        }

        let snowflakeUser: string;
        if (Array.isArray(userValue)) {
            snowflakeUser = userValue[0];
        } else {
            snowflakeUser = userValue;
        }

        let user = await fastify.db.user.findUnique({
            where: {
                snowflakeUser,
            },
        });

        if (!user) {
            user = await fastify.db.user.create({
                data: {
                    snowflakeUser: snowflakeUser,
                },
            });
            req.log.info(`Created user ${snowflakeUser} with id ${user.id}`);
        }

        req.log.info(`User ${snowflakeUser} added to request context`);
        req.user = user;
    });
};

// Use fastify-plugin to ensure plugin is registered at root level
export default fp(userPlugin, {
    name: 'user',
});
