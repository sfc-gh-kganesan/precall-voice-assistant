import { createMiddleware } from 'hono/factory';
import type { Config } from '../config.js';

export type Env = {
  Variables: {
    localStoragePath: string;
  };
};

export const env = (config: Config) =>
  createMiddleware<Env>(async (c, next) => {
    c.set('localStoragePath', config.localStoragePath);
    await next();
  });
