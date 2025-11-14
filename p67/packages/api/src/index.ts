import cors from '@fastify/cors';
import Fastify from 'fastify';

const fastify = Fastify({
    logger: true,
});

// Register CORS
await fastify.register(cors, {
    origin: true,
});

// Routes
fastify.get('/api/health', async () => {
    return { status: 'ok', timestamp: new Date().toISOString() };
});

// Start server
const start = async () => {
    try {
        const port = process.env.PORT ? Number.parseInt(process.env.PORT) : 3001;
        await fastify.listen({ port, host: '0.0.0.0' });
        console.log(`Server listening on port ${port}`);
    } catch (err) {
        fastify.log.error(err);
        process.exit(1);
    }
};

start();
