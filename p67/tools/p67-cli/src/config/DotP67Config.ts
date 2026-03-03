import * as fs from 'node:fs';
import * as path from 'node:path';
import * as yaml from 'js-yaml';
import { z } from 'zod';

const DotP67ConfigSchema = z.object({
    workflowId: z.string().describe('Last deployed workflow ID'),
});

export type DotP67ConfigData = z.infer<typeof DotP67ConfigSchema>;

export class DotP67Config {
    private configPath: string;
    private configDir: string;
    private data: DotP67ConfigData | null = null;

    constructor(configDir: string) {
        this.configDir = configDir;
        this.configPath = path.join(this.configDir, '.p67');
        if (fs.existsSync(this.configPath)) {
            this.load();
        }
    }

    /**
     * Check if the .p67 file exists
     */
    exists(): boolean {
        return fs.existsSync(this.configPath);
    }

    /**
     * Load and parse the .p67 file
     * @throws Error if file doesn't exist or is invalid
     */
    load(): DotP67ConfigData {
        if (!this.exists()) {
            throw new Error(`Configuration file not found: ${this.configPath}`);
        }

        try {
            const fileContents = fs.readFileSync(this.configPath, 'utf8');
            const rawData = yaml.load(fileContents);

            if (!rawData) {
                throw new Error('Configuration file is empty');
            }

            // Validate with Zod schema
            const result = DotP67ConfigSchema.safeParse(rawData);

            if (!result.success) {
                const errors = result.error.issues
                    .map((e) => `${e.path.join('.') || 'config'}: ${e.message}`)
                    .join('; ');
                throw new Error(`Invalid configuration: ${errors}`);
            }

            this.data = result.data;
            return this.data;
        } catch (error) {
            if (error instanceof Error) {
                // Don't wrap if it's already our formatted error
                if (
                    error.message.startsWith('Invalid configuration:') ||
                    error.message.startsWith('Configuration file is empty')
                ) {
                    throw error;
                }
                throw new Error(
                    `Failed to load configuration: ${error.message}`,
                );
            }
            throw error;
        }
    }

    write(): void {
        if (this.data === null) {
            throw new Error('Configuration data is null');
        }

        try {
            const yamlContent = yaml.dump(this.data, {
                indent: 2,
                lineWidth: -1,
            });
            fs.writeFileSync(this.configPath, yamlContent, 'utf8');
        } catch (error) {
            throw new Error(`Error writing configuration file: ${error}`);
        }
    }

    /**
     * Get the configuration data, or null if no .p67 file exists
     */
    get(): DotP67ConfigData | null {
        return this.data;
    }

    setWorkflowId(workflowId: string): void {
        this.data = {
            workflowId,
        };
        this.write();
    }
}
