import type {
	Connection,
	ConnectionConfig,
} from '@p67-cli/config/ConnectionConfig';
import type { ProjectConfig } from '@p67-cli/config/ProjectConfig';

export class Context {
	private _values = new Map<string, unknown>();

	private setOnce<T>(key: string, value: T): void {
		if (this._values.has(key)) {
			throw new Error(`Context value ${key} has already been assigned`);
		}
		this._values.set(key, value);
	}

	private mustGet<T>(key: string): T {
		const v = this._values.get(key) as T | undefined;
		if (!v) {
			throw new Error(`Context value ${key} is undefined`);
		}
		return v;
	}

	set connection(value: Connection) {
		this.setOnce('connection', value);
	}

	get connection(): Connection {
		return this.mustGet<Connection>('connection');
	}

	set connectionConfig(value: ConnectionConfig) {
		this.setOnce('connectionConfig', value);
	}

	get connectionConfig(): ConnectionConfig {
		return this.mustGet<ConnectionConfig>('connectionConfig');
	}

	set projectConfig(value: ProjectConfig) {
		this.setOnce('projectConfig', value);
	}

	get projectConfig(): ProjectConfig {
		return this.mustGet<ProjectConfig>('projectConfig');
	}
}

let context: Context | null = null;

export const ctx = (): Context => {
	if (!context) {
		context = new Context();
	}
	return context;
};
