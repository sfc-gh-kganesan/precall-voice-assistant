import * as fs from 'node:fs';
import { homedir } from 'node:os';
import * as path from 'node:path';
import * as toml from 'toml';
import { z } from 'zod';

const ConnectionSchema = z.object({
    endpoint: z.string().url('Endpoint must be a valid URL'),
    pat: z.string().describe('Snowflake Programmatic Access Token (PAT)'),
});

const ConnectionsConfigSchema = z.object({
    default_connection_name: z
        .string()
        .optional()
        .describe('Default connection name'),
    connections: z.record(z.string(), ConnectionSchema).default({}),
});

export type Connection = z.infer<typeof ConnectionSchema> & { name: string };
export type ConnectionsConfigData = z.infer<typeof ConnectionsConfigSchema>;

export class ConnectionConfig {
    private configPath: string;
    private configDir: string;
    private data: ConnectionsConfigData | null = null;

    constructor(configDir?: string) {
        this.configDir = configDir || path.join(homedir(), '.snowflake', 'p67');
        this.configPath = path.join(this.configDir, 'config.toml');
    }

    /**
     * Check if the config file exists
     */
    exists(): boolean {
        return fs.existsSync(this.configPath);
    }

    /**
     * Ensure the config directory exists
     */
    private ensureConfigDir(): void {
        if (!fs.existsSync(this.configDir)) {
            fs.mkdirSync(this.configDir, { recursive: true });
        }
    }

    /**
     * Load and parse the config.toml file
     */
    load(): ConnectionsConfigData {
        if (!this.exists()) {
            // Return default empty config
            this.data = { connections: {} };
            return this.data;
        }

        try {
            const fileContents = fs.readFileSync(this.configPath, 'utf8');
            const rawData = toml.parse(fileContents);

            // Validate with Zod schema
            const result = ConnectionsConfigSchema.safeParse(rawData);

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
                if (error.message.startsWith('Invalid configuration:')) {
                    throw error;
                }
                throw new Error(
                    `Failed to load configuration: ${error.message}`,
                );
            }
            throw error;
        }
    }

    /**
     * Write configuration to disk
     */
    write(): void {
        if (this.data === null) {
            throw new Error('Configuration data is null');
        }

        try {
            this.ensureConfigDir();
            const tomlContent = this.toTOML(this.data);
            fs.writeFileSync(this.configPath, tomlContent, 'utf8');
        } catch (error) {
            throw new Error(`Error writing configuration file: ${error}`);
        }
    }

    /**
     * Get the configuration data (loads if not already loaded)
     */
    get(): ConnectionsConfigData {
        if (!this.data) {
            this.load();
        }
        if (!this.data) {
            throw new Error('unable to load connection config');
        }
        return this.data;
    }

    /**
     * Get all connections
     */
    getConnections(): Connection[] {
        const config = this.get();
        return Object.entries(config.connections).map(([name, conn]) => ({
            name,
            ...conn,
        }));
    }

    /**
     * Get a specific connection by name
     */
    getConnection(name: string): Connection | undefined {
        const conn = this.get().connections[name];
        if (!conn) return undefined;
        return { name, ...conn };
    }

    /**
     * Get the default connection name
     */
    getDefault(): string | undefined {
        return this.get().default_connection_name;
    }

    /**
     * Set the default connection
     */
    setDefault(name: string): void {
        const config = this.get();
        const connection = this.getConnection(name);
        if (!connection) {
            throw new Error(`Connection '${name}' not found`);
        }
        config.default_connection_name = name;
        this.data = config;
    }

    /**
     * Add a new connection
     */
    addConnection(connection: Connection): void {
        const config = this.get();
        if (config.connections[connection.name]) {
            throw new Error(`Connection '${connection.name}' already exists`);
        }
        const { name, ...rest } = connection;
        config.connections[name] = rest;
        this.data = config;
    }

    /**
     * Remove a connection
     */
    removeConnection(name: string): void {
        const config = this.get();
        if (!config.connections[name]) {
            throw new Error(`Connection '${name}' not found`);
        }
        delete config.connections[name];
        // Clear default if it was the removed connection
        if (config.default_connection_name === name) {
            config.default_connection_name = undefined;
        }
        this.data = config;
    }

    /**
     * Convert config to TOML format with inline tables
     */
    private toTOML(config: ConnectionsConfigData): string {
        let toml = '# P67 Connection Configuration\n\n';

        if (config.default_connection_name) {
            toml += `default_connection_name = "${config.default_connection_name}"\n\n`;
        }

        for (const [name, conn] of Object.entries(config.connections)) {
            toml += `[connections.${name}]\n`;
            toml += `endpoint = "${conn.endpoint}"\n`;
            toml += `pat = "${conn.pat}"\n`;
            toml += '\n';
        }

        return toml;
    }

    /**
     * Get the configuration file path
     */
    getConfigPath(): string {
        return this.configPath;
    }
}
