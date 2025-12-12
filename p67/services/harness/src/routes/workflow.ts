import { createRoute, OpenAPIHono, z } from '@hono/zod-openapi';
import type { Env } from '../middleware/env';
import { randomUUID } from 'crypto';
import { rm, writeFile, rename, readdir } from 'fs/promises';
import { unzipToTemp } from '../lib/zip.js';
import { join } from 'path';
import { existsSync } from 'fs';
import { Runner } from '../runner.js';
import {
  WorkflowCreateResponseSchema,
  WorkflowListResponseSchema,
  WorkflowRunResponseSchema,
  ErrorResponseSchema,
} from '../schema.js';

const workflow = new OpenAPIHono<Env>();

const createWorkflowRoute = createRoute({
  method: 'post',
  path: '/create',
  tags: ['Workflow'],
  summary: 'Create a new workflow',
  description: 'Upload a zip file to create a new workflow',
  request: {
    body: {
      content: {
        'multipart/form-data': {
          schema: z.object({
            file: z.instanceof(File).openapi({ type: 'string', format: 'binary' }),
          }),
        },
      },
    },
  },
  responses: {
    200: {
      description: 'Workflow created successfully',
      content: {
        'application/json': {
          schema: WorkflowCreateResponseSchema,
        },
      },
    },
    400: {
      description: 'Bad request',
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
    },
    500: {
      description: 'Internal server error',
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
    },
  },
});

workflow.openapi(createWorkflowRoute, async (c) => {
  const body = await c.req.parseBody();
  const file = body['file'];

  if (!file || !(file instanceof File)) {
    return c.json({ error: 'No file uploaded' }, 400);
  }

  const workflowId = `wf-${randomUUID()}`;
  const uploadedZipPath = join(c.var.localStoragePath, `upload-${workflowId}.zip`);
  const buffer = await file.arrayBuffer();
  await writeFile(uploadedZipPath, Buffer.from(buffer));

  const { tempDir, files } = await unzipToTemp(uploadedZipPath);
  console.log(tempDir);
  console.log(files);
  try {
    await rm(uploadedZipPath, { force: true });
    console.log(`cleaned up ${uploadedZipPath}`);
  } catch (err) {
    console.error(err);
  }

  try {
    const newPath = join(c.var.localStoragePath, workflowId);
    await rename(tempDir, newPath);
    console.log(`renamed ${tempDir} to ${newPath}`);
  } catch (error) {
    console.error('Error processing request:', error);
    return c.json(
      {
        error: 'Internal server error',
        message: error instanceof Error ? error.message : 'Unknown error',
      },
      500,
    );
  }

  return c.json(
    {
      workflowId,
    },
    200,
  );
});

const listWorkflowsRoute = createRoute({
  method: 'get',
  path: '/list',
  tags: ['Workflow'],
  summary: 'List all workflows',
  description: 'Get a list of all available workflows',
  responses: {
    200: {
      description: 'List of workflows',
      content: {
        'application/json': {
          schema: WorkflowListResponseSchema,
        },
      },
    },
    500: {
      description: 'Internal server error',
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
    },
  },
});

workflow.openapi(listWorkflowsRoute, async (c) => {
  try {
    const localStoragePath = c.var.localStoragePath;

    if (!existsSync(localStoragePath)) {
      return c.json({ workflows: [] }, 200);
    }

    const entries = await readdir(localStoragePath, { withFileTypes: true });

    const workflows = entries
      .filter((entry) => entry.isDirectory() && entry.name.startsWith('wf-'))
      .map((entry) => entry.name);

    return c.json({ workflows }, 200);
  } catch (error) {
    console.error('Error listing workflows:', error);
    return c.json(
      {
        error: 'Internal server error',
        message: error instanceof Error ? error.message : 'Unknown error',
      },
      500,
    );
  }
});

const runWorkflowRoute = createRoute({
  method: 'post',
  path: '/{wfid}/run',
  tags: ['Workflow'],
  summary: 'Run a workflow',
  description: 'Execute a workflow by its ID',
  request: {
    params: z.object({
      wfid: z.string().openapi({ example: 'wf-123e4567-e89b-12d3-a456-426614174000' }),
    }),
  },
  responses: {
    200: {
      description: 'Workflow executed',
      content: {
        'application/json': {
          schema: WorkflowRunResponseSchema,
        },
      },
    },
    400: {
      description: 'Bad request - workflow not found',
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
    },
  },
});

workflow.openapi(runWorkflowRoute, async (c) => {
  const wfid = c.req.param('wfid');
  const wfdir = join(c.var.localStoragePath, wfid);
  if (!existsSync(wfdir)) {
    return c.json({ error: 'Invalid request', message: `Workflow ${wfid} does not exist` }, 400);
  }
  const runnerInstance = new Runner(wfdir);
  const { stdout, stderr, exitCode } = await runnerInstance.start();

  return c.json(
    {
      exitCode,
      stdout,
      stderr,
      success: exitCode === 0,
    },
    200,
  );
});

export default workflow;
