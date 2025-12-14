import { FastifyInstance } from 'fastify';
import { ZodTypeProvider } from 'fastify-type-provider-zod';
import { randomUUID } from 'crypto';
import { readdir } from 'fs/promises';
import { unzip } from '@controld/lib/zip.js';
import { join } from 'path';
import { existsSync } from 'fs';
import { Runner } from '@controld/lib/runner.js';
import {
  WorkflowCreateResponseSchema,
  WorkflowListResponseSchema,
  WorkflowRunResponseSchema,
  WorkflowRunParamsSchema,
  ErrorResponseSchema,
} from '@controld/schema.js';

const workflowRoutes = async (server: FastifyInstance) => {
  const fastify = server.withTypeProvider<ZodTypeProvider>();

  fastify.post(
    '/create',
    {
      schema: {
        description: 'Create a new workflow by uploading a ZIP file',
        tags: ['Workflow'],
        response: {
          200: WorkflowCreateResponseSchema,
          400: ErrorResponseSchema,
          500: ErrorResponseSchema,
        },
      },
    },
    async (request, reply) => {
      try {
        const data = await request.file();

        if (!data) {
          return reply.code(400).send({ error: 'No file uploaded' });
        }

        const { localStoragePath } = request.server.config;
        const workflowId = `wf-${randomUUID()}`;
        const buffer = await data.toBuffer();
        const dest = join(localStoragePath, workflowId);
        const { dir, files } = await unzip(buffer, dest);
        console.log('Dir:', dir);
        console.log('Files:', files);
        return reply.code(200).send({ workflowId });
      } catch (error) {
        console.error('Error creating workflow:', error);
        return reply.code(500).send({
          error: 'Internal server error',
          message: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    },
  );

  fastify.get(
    '/list',
    {
      schema: {
        description: 'List all workflows',
        tags: ['Workflow'],
        response: {
          200: WorkflowListResponseSchema,
          500: ErrorResponseSchema,
        },
      },
    },
    async (request, reply) => {
      const { localStoragePath } = request.server.config;
      try {
        if (!existsSync(localStoragePath)) {
          return reply.code(200).send({ workflows: [] });
        }

        const entries = await readdir(localStoragePath, { withFileTypes: true });

        const workflows = entries
          .filter((entry) => entry.isDirectory() && entry.name.startsWith('wf-'))
          .map((entry) => entry.name);

        return reply.code(200).send({ workflows });
      } catch (error) {
        console.error('Error listing workflows:', error);
        return reply.code(500).send({
          error: 'Internal server error',
          message: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    },
  );

  fastify.post(
    '/:workflowId/run',
    {
      schema: {
        description: 'Run a workflow',
        tags: ['Workflow'],
        params: WorkflowRunParamsSchema,
        response: {
          200: WorkflowRunResponseSchema,
          400: ErrorResponseSchema,
          500: ErrorResponseSchema,
        },
      },
    },
    async (request, reply) => {
      try {
        const { localStoragePath } = request.server.config;
        const { workflowId } = request.params as { workflowId: string };
        const wfdir = join(localStoragePath, workflowId);

        if (!existsSync(wfdir)) {
          return reply.code(400).send({
            error: 'Invalid request',
            message: `Workflow ${workflowId} does not exist`,
          });
        }

        const runnerInstance = new Runner(wfdir);
        const { stdout, stderr, exitCode } = await runnerInstance.start();

        return reply.code(200).send({
          exitCode,
          stdout,
          stderr,
          success: exitCode === 0,
        });
      } catch (error) {
        console.error('Error running workflow:', error);
        return reply.code(500).send({
          error: 'Internal server error',
          message: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    },
  );
};

export default workflowRoutes;
