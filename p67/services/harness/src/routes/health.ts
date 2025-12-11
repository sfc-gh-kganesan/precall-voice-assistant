import { Hono } from 'hono';
import type { Env } from '../middleware/env.js';

const health = new Hono<Env>();

health.get('/', (c) => {
  return c.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    localStoragePath: c.var.localStoragePath,
  });
});

export default health;
