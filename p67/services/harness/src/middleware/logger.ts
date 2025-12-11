import pino from 'pino';
import { pinoLogger } from 'hono-pino';
import { MiddlewareHandler } from 'hono';
import { DebugLogOptions } from 'hono-pino/debug-log';
import type { Config } from '../config.js';

const options: DebugLogOptions = {
  colorEnabled: true,
};

export const initLogger = (config: Config): MiddlewareHandler => {
  const level = config.nodeEnv === 'development' ? 'trace' : 'debug';
  return pinoLogger({
    pino: pino({
      base: null,
      level: level,
      transport: {
        target: 'hono-pino/debug-log',
        options,
      },
      timestamp: pino.stdTimeFunctions.unixTime,
    }),
  });
};
