import * as fs from 'node:fs';
import * as path from 'node:path';
import * as yaml from 'js-yaml';
import { z } from 'zod';

const ProjectConfigSchema = z.object({
	runtime: z.object({
		endpoint: z.string().url('Runtime endpoint must be a valid URL'),
	}),
	workflow: z.object({
		entrypoint: z.string().describe('Path to workflow entrypoint file'),
		buildTarget: z.string().describe('Path to built js file'),
	}),
});

export type ProjectConfigData = z.infer<typeof ProjectConfigSchema>;

export class ProjectConfig {
	private configPath: string;
	private data: ProjectConfigData | null = null;

	constructor(
		directory: string = process.cwd(),
		data: ProjectConfigData | null = null,
	) {
		this.configPath = path.join(directory, 'p67.yml');
		this.data = data;
	}

	/**
	 * Check if the p67.yml file exists
	 */
	exists(): boolean {
		return fs.existsSync(this.configPath);
	}

	/**
	 * Load and parse the p67.yml file
	 * @throws Error if file doesn't exist or is invalid
	 */
	load(): ProjectConfigData {
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
			const result = ProjectConfigSchema.safeParse(rawData);

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
				throw new Error(`Failed to load configuration: ${error.message}`);
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
	 * Get the configuration data (loads if not already loaded)
	 */
	get(): ProjectConfigData {
		if (!this.data) {
			this.load();
		}
		if (!this.data) {
			throw new Error('unable to load project config');
		}
		return this.data;
	}

	/**
	 * Get the runtime endpoint
	 */
	getRuntimeEndpoint(): string {
		return this.get().runtime.endpoint;
	}

	/**
	 * Get the entrypoint file path
	 */
	get entrypoint(): string {
		return this.get().workflow.entrypoint;
	}

	/**
	 * Get the entrypoint build target path
	 */
	get buildTarget(): string {
		return this.get().workflow.buildTarget;
	}

	/**
	 * Get the configuration file path
	 */
	getConfigPath(): string {
		return this.configPath;
	}
}
