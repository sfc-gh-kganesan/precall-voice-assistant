import cors from '@fastify/cors';
import Fastify from 'fastify';
import { join } from 'path';
import { tmpdir } from 'os';
import multipart from '@fastify/multipart';
import { unzipToTemp } from './zip.js';
import { randomUUID } from 'crypto';
import { pipeline } from 'stream/promises';
import { createWriteStream } from 'fs';
import { rm } from 'fs/promises';
import { Runner } from './runner.js';

const fastify = Fastify({
  logger: true,
});

// Register multipart plugin for file uploads
fastify.register(multipart, {
  limits: {
    fileSize: 10 * 1024 * 1024, // 10MB limit - adjust as needed
  },
});

// Register CORS
await fastify.register(cors, {
  origin: true,
});

// Routes
fastify.get('/api/health', async () => {
  return { status: 'ok', timestamp: new Date().toISOString() };
});

fastify.post('/run', async (request, reply) => {
  try {
    const data = await request.file();

    if (!data) {
      return reply.code(400).send({ error: 'No file uploaded' });
    }

    // Validate file type
    // if (data.mimetype !== 'application/zip' &&
    //     data.mimetype !== 'application/x-zip-compressed') {
    //     return reply.code(400).send({ error: 'File must be a zip archive' });
    // }

    // Save uploaded file to temporary location
    const uploadedZipPath = join(tmpdir(), `upload-${randomUUID()}.zip`);
    await pipeline(data.file, createWriteStream(uploadedZipPath));

    // Unzip to temporary directory
    const { tempDir, files } = await unzipToTemp(uploadedZipPath);
    console.log(JSON.stringify({ tempDir, files }, null, 2));

    // Clean up the uploaded zip file
    await rm(uploadedZipPath, { force: true });

    const runner = new Runner(tempDir);
    runner.start();

    //////
    const exitCode = 0;
    const output = 'ok';
    const errorOutput = 'all good';

    // Clean up temporary file
    try {
      await rm(tempDir, { force: true });
    } catch (err) {
      console.error('Failed to delete temp file:', err);
    }

    // Return the execution results
    return reply.send({
      exitCode,
      stdout: output,
      stderr: errorOutput,
      success: exitCode === 0,
    });
  } catch (error) {
    console.error('Error processing request:', error);
    return reply.code(500).send({
      error: 'Internal server error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
});

// Start server
const start = async () => {
  try {
    const port = process.env.PORT ? Number.parseInt(process.env.PORT) : 3000;
    await fastify.listen({ port, host: '0.0.0.0' });
    console.log(`Server listening on port ${port}`);
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();
