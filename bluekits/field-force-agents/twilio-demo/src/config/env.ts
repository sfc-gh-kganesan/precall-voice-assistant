import dotenv from 'dotenv';
import { logger } from '../utils/logger';

// Load environment variables
dotenv.config();

export interface Environment {
  OPENAI_API_KEY: string;
  OPENAI_MODEL?: string;
  PORT: number;
  NODE_ENV: string;
  LOG_LEVEL: string;
}

/**
 * Validate and return environment variables
 */
export function validateEnv(): Environment {
  const required = ['OPENAI_API_KEY'];

  const missing = required.filter((key) => !process.env[key]);

  if (missing.length > 0) {
    logger.error(`Missing required environment variables: ${missing.join(', ')}`);
    throw new Error(`Missing required environment variables: ${missing.join(', ')}`);
  }

  return {
    OPENAI_API_KEY: process.env.OPENAI_API_KEY!,
    OPENAI_MODEL: process.env.OPENAI_MODEL,
    PORT: parseInt(process.env.PORT || '3000', 10),
    NODE_ENV: process.env.NODE_ENV || 'development',
    LOG_LEVEL: process.env.LOG_LEVEL || 'info',
  };
}

export const env = validateEnv();
