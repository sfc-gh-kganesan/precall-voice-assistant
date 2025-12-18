import yaml from 'yaml';
import { z } from 'zod';

/**
 * Manifest schema
 * Example:
 *  - config_name: snowflake
 *    account: snowflake_account
 *    username: snowflake_username
 *    token: secret_name
 *    database: snowflake_database
 *    schema: snowflake_schema
 */
const ManifestSchema = z.object({
  config: z.array(
    z.object({
      config_name: z.string(),
      account: z.string().optional(),
      username: z.string().optional(),
      authenticator: z.string().optional(),
      accessUrl: z.string().optional(),
      token: z.string().optional(),
      password: z.string().optional(),
      warehouse: z.string().optional(),
      database: z.string().optional(),
      schema: z.string().optional(),
    }),
  ),
});

export type Manifest = z.infer<typeof ManifestSchema>;

export function parseManifest(manifestStr: string): Manifest {
  const manifest = yaml.parse(manifestStr);
  const result = ManifestSchema.safeParse(manifest);
  if (!result.success) {
    throw new Error(`Invalid manifest: ${result.error.message}`);
  }

  return result.data;
}
