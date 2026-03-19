import dotenv from 'dotenv';
import { logger } from '../utils/logger';

// Load environment variables
dotenv.config();

export interface Environment {
  OPENAI_API_KEY: string;
  OPENAI_MODEL?: string;
  TWILIO_ACCOUNT_SID: string;
  TWILIO_AUTH_TOKEN: string;
  PORT: number;
  NODE_ENV: string;
  LOG_LEVEL: string;
  DOMAIN?: string;
}

/**
 * Validate and return environment variables
 */
export function validateEnv(): Environment {
  const required = [
    'OPENAI_API_KEY',
    'TWILIO_ACCOUNT_SID',
    'TWILIO_AUTH_TOKEN',
  ];

  const missing = required.filter((key) => !process.env[key]);

  if (missing.length > 0) {
    logger.error(`Missing required environment variables: ${missing.join(', ')}`);
    throw new Error(`Missing required environment variables: ${missing.join(', ')}`);
  }

  return {
    OPENAI_API_KEY: process.env.OPENAI_API_KEY!,
    OPENAI_MODEL: process.env.OPENAI_MODEL,
    TWILIO_ACCOUNT_SID: process.env.TWILIO_ACCOUNT_SID!,
    TWILIO_AUTH_TOKEN: process.env.TWILIO_AUTH_TOKEN!,
    PORT: parseInt(process.env.PORT || '3000', 10),
    NODE_ENV: process.env.NODE_ENV || 'development',
    LOG_LEVEL: process.env.LOG_LEVEL || 'info',
    DOMAIN: process.env.DOMAIN,
  };
}

export const env = validateEnv();
