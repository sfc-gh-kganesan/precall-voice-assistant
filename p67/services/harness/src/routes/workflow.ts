import { Hono } from 'hono';
import type { Env } from '../middleware/env';
import { randomUUID } from 'crypto';
import { rm, writeFile, rename, readdir } from 'fs/promises';
import { unzipToTemp } from '../lib/zip.js';
import { join } from 'path';
import { existsSync } from 'fs';
import { Runner } from '../runner.js';

const workflow = new Hono<Env>();

workflow.post('/create', async (c) => {
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

  return c.json({
    workflowId,
  });
});

workflow.get('/list', async (c) => {
  try {
    const localStoragePath = c.var.localStoragePath;

    if (!existsSync(localStoragePath)) {
      return c.json({ workflows: [] });
    }

    const entries = await readdir(localStoragePath, { withFileTypes: true });

    const workflows = entries
      .filter((entry) => entry.isDirectory() && entry.name.startsWith('wf-'))
      .map((entry) => entry.name);

    return c.json({ workflows });
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

workflow.post('/:wfid/run', async (c) => {
  const wfid = c.req.param('wfid');
  const wfdir = join(c.var.localStoragePath, wfid);
  if (!existsSync(wfdir)) {
    return c.json({ error: 'Invalid request', message: `Workflow ${wfid} does not exist` }, 400);
  }
  const runnerInstance = new Runner(wfdir);
  const { stdout, stderr, exitCode } = await runnerInstance.start();

  return c.json({
    exitCode,
    stdout,
    stderr,
    success: exitCode === 0,
  });
});

export default workflow;
