import * as fs from 'node:fs';
import * as path from 'node:path';
import type { WorkflowLanguage } from '@controld/lib/runtime/adapter.js';
import yaml from 'yaml';
import { z } from 'zod';

// ValueSchema is a sum-type. It can be one of a value, a valueRef, a
// secretRef, or an oauthRef.
const ValueSchema = z.object({
    value: z.string().optional(),
    valueRef: z.string().optional(),
    secretRef: z.string().optional(),
    oauthRef: z.string().optional(), // Reference to an OAuth token secret
    required: z.boolean().optional(), // If true, param must be provided at runtime
    description: z.string().optional(), // Description shown in interactive prompt
});

export type Value = z.infer<typeof ValueSchema>;

/**
 * Language schema for workflow language specification
 */
const LanguageSchema = z.enum(['typescript', 'python']).optional();

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
    // Optional workflow name - used for version management
    name: z
        .string()
        .min(1)
        .max(128)
        .regex(/^[a-zA-Z0-9_-]+$/)
        .optional(),
    // Optional language field - if not specified, will be detected from files
    language: LanguageSchema,
    // Top-level workflow parameters - can be overridden at runtime via POST body
    params: z.record(z.string(), ValueSchema).optional(),
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
            email_integration: ValueSchema.optional(),
            parameters: z.record(z.string(), ValueSchema).optional(),
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

/**
 * Detects the workflow language from manifest or file structure.
 *
 * Priority:
 * 1. Explicit `language` field in manifest
 * 2. File-based detection (main.py → python, index.js → typescript)
 *
 * @param workflowDir - Directory containing the workflow files
 * @param manifest - Optional parsed manifest (will be loaded if not provided)
 * @returns The detected workflow language
 * @throws Error if language cannot be determined
 */
export function detectLanguage(
    workflowDir: string,
    manifest?: Manifest,
): WorkflowLanguage {
    // If manifest has explicit language, use it
    if (manifest?.language) {
        return manifest.language;
    }

    // Try to load manifest if not provided
    if (!manifest) {
        const manifestPath = path.join(workflowDir, 'manifest.yaml');
        if (fs.existsSync(manifestPath)) {
            try {
                const manifestStr = fs.readFileSync(manifestPath, 'utf-8');
                const parsed = parseManifest(manifestStr);
                if (parsed.language) {
                    return parsed.language;
                }
            } catch {
                // Ignore manifest parse errors for language detection
            }
        }
    }

    // File-based detection
    const pythonEntry = path.join(workflowDir, 'main.py');
    const typescriptEntry = path.join(workflowDir, 'index.js');

    const hasPython = fs.existsSync(pythonEntry);
    const hasTypeScript = fs.existsSync(typescriptEntry);

    if (hasPython && hasTypeScript) {
        throw new Error(
            'Ambiguous workflow language: both main.py and index.js exist. ' +
                'Please specify language in manifest.yaml',
        );
    }

    if (hasPython) {
        return 'python';
    }

    if (hasTypeScript) {
        return 'typescript';
    }

    throw new Error(
        'Cannot detect workflow language: neither main.py nor index.js found in ' +
            workflowDir,
    );
}
