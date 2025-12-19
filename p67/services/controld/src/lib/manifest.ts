import yaml from 'yaml';
import { z } from 'zod';

// ValueSchema is a sum-type. It can be one of a value, a valueRef, or a
// secretRef.
const ValueSchema = z.object({
  value: z.string().optional(),
  valueRef: z.string().optional(),
  secretRef: z.string().optional(),
});

export type Value = z.infer<typeof ValueSchema>;

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
      account: ValueSchema.optional(),
      username: ValueSchema.optional(),
      authenticator: ValueSchema.optional(),
      accessUrl: ValueSchema.optional(),
      token: ValueSchema.optional(),
      password: ValueSchema.optional(),
      warehouse: ValueSchema.optional(),
      database: ValueSchema.optional(),
      schema: ValueSchema.optional(),
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
