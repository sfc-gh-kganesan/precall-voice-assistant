export interface HealthResponse {
    status: string;
    timestamp: string;
    localStoragePath: string;
}

export interface WorkflowCreateResponse {
    workflowId: string;
}

export interface Workflow {
    workflowId: string;
    name: string | null;
    owner: string;
    createdAt: string;
    updatedAt: string;
    visibility: string;
}

export interface WorkflowListResponse {
    workflows: Workflow[];
}

export interface WorkflowRunResponse {
    exitCode: number;
    stdout: string[];
    stderr: string[];
    success: boolean;
    errors: Array<{ error: string; message: string }>;
    log: string[];
}

export interface ManifestParamValue {
    value?: string;
    valueRef?: string;
    secretRef?: string;
    oauthRef?: string;
    required?: boolean;
    description?: string;
}

export interface WorkflowManifestResponse {
    params?: Record<string, ManifestParamValue>;
}

export interface ErrorResponse {
    error: string;
    message?: string;
}

// Secret types
export type SecretType = 'Secret' | 'OAuth';

export interface Secret {
    name: string;
    type: SecretType;
    createdAt: string;
    updatedAt: string;
}

export interface SecretSaveResponse {
    name: string;
    created: boolean;
}

export interface SecretListResponse {
    secrets: Secret[];
}

export interface SecretDeleteResponse {
    deleted: boolean;
    name: string;
}

export interface SecretGetResponse {
    name: string;
    value: string;
    createdAt: string;
    updatedAt: string;
}

export interface OAuthRefreshResponse {
    name: string;
    provider: string;
    expiresAt: string | null;
    refreshed: boolean;
}

// Log types
export type LogSource = 'RuntimeHost' | 'WorkflowNode' | 'ToolCall';

export interface LogEntry {
    id: string;
    runId: string;
    workflowId: string;
    source: LogSource;
    message: string;
    attributes: Record<string, unknown>;
    timestamp: string;
}

export interface LogListResponse {
    logs: LogEntry[];
    total: number;
}

export interface LogListOptions {
    workflowId?: string;
    runId?: string;
    source?: LogSource;
    limit?: number;
    offset?: number;
}

export interface RunEntry {
    id: string;
    workflowId: string;
    startedAt: string;
    completedAt: string | null;
    exitCode: number | null;
    logCount: number;
}

export interface RunListResponse {
    runs: RunEntry[];
    total: number;
}

export interface ControldClientConfig {
    baseUrl: string;
    pat: string;
    timeout?: number;
}

export class ControldClient {
    private _baseUrl: string;
    private _timeout: number;
    private _pat: string;

    constructor(config: ControldClientConfig) {
        this._baseUrl = config.baseUrl.replace(/\/$/, '');
        this._timeout = config.timeout || 600000;
        this._pat = config.pat;
    }

    public get baseUrl(): string {
        return this._baseUrl;
    }

    public get timeout(): number {
        return this._timeout;
    }

    async fetch(path: string, options: RequestInit = {}): Promise<Response> {
        const cleanPath = path.startsWith('/') ? path.substring(1) : path;
        const url = `${this._baseUrl}/${cleanPath}`;
        const defaultHeaders = {
            Authorization: `Snowflake Token="${this._pat}"`,
            ...options.headers,
        };

        const mergedOptions: RequestInit = {
            ...options,
            headers: {
                ...defaultHeaders,
                ...options.headers,
            },
            signal: AbortSignal.timeout(this._timeout),
        };

        return fetch(url, mergedOptions);
    }

    async get(path: string, options: RequestInit = {}): Promise<Response> {
        return this.fetch(path, { ...options, method: 'GET' });
    }

    async post(path: string, options: RequestInit = {}): Promise<Response> {
        return this.fetch(path, { ...options, method: 'POST' });
    }

    async delete(path: string, options: RequestInit = {}): Promise<Response> {
        return this.fetch(path, { ...options, method: 'DELETE' });
    }

    async health(): Promise<HealthResponse> {
        const response = await this.get('/api/health');

        if (!response.ok) {
            const error = (await response.json()) as ErrorResponse;
            throw new Error(error.message || error.error);
        }

        return (await response.json()) as HealthResponse;
    }

    async createWorkflow(
        file: File | Blob,
        filename?: string,
        overwriteWorkflowId?: string,
    ): Promise<WorkflowCreateResponse> {
        const formData = new FormData();

        if (overwriteWorkflowId) {
            formData.append('overwriteWorkflowId', overwriteWorkflowId);
        }

        if (file instanceof File) {
            formData.append('file', file);
        } else {
            formData.append('file', file, filename || 'workflow.zip');
        }

        const response = await this.post('api/workflow/create', {
            body: formData,
        });

        if (!response.ok) {
            const error = (await response.json()) as ErrorResponse;
            throw new Error(error.message || error.error);
        }

        return (await response.json()) as WorkflowCreateResponse;
    }

    async listWorkflows(): Promise<WorkflowListResponse> {
        const response = await this.get('/api/workflow/list');

        if (!response.ok) {
            const error = (await response.json()) as ErrorResponse;
            throw new Error(error.message || error.error);
        }

        return (await response.json()) as WorkflowListResponse;
    }

    async runWorkflow(
        workflowId: string,
        params: Record<string, string>,
    ): Promise<WorkflowRunResponse> {
        const response = await this.post(`/api/workflow/${workflowId}/run`, {
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ params }),
        });

        if (!response.ok) {
            const error = (await response.json()) as ErrorResponse;
            throw new Error(error.message || error.error);
        }

        return (await response.json()) as WorkflowRunResponse;
    }

    async getWorkflowManifest(
        workflowId: string,
    ): Promise<WorkflowManifestResponse> {
        const response = await this.get(`/api/workflow/${workflowId}/manifest`);

        if (!response.ok) {
            const error = (await response.json()) as ErrorResponse;
            throw new Error(error.message || error.error);
        }

        return (await response.json()) as WorkflowManifestResponse;
    }

    async runWorkflowByName(
        name: string,
        params: Record<string, string>,
    ): Promise<WorkflowRunResponse> {
        const response = await this.post(
            `/api/workflow/name/${encodeURIComponent(name)}/run`,
            {
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(params),
            },
        );

        if (!response.ok) {
            const error = (await response.json()) as ErrorResponse;
            throw new Error(error.message || error.error);
        }

        return (await response.json()) as WorkflowRunResponse;
    }

    async getWorkflowVersions(name: string): Promise<WorkflowListResponse> {
        const response = await this.get(
            `/api/workflow/name/${encodeURIComponent(name)}/versions`,
        );

        if (!response.ok) {
            const error = (await response.json()) as ErrorResponse;
            throw new Error(error.message || error.error);
        }

        return (await response.json()) as WorkflowListResponse;
    }

    // Secret methods

    async saveSecret(
        name: string,
        secret: string,
        type: SecretType = 'Secret',
    ): Promise<SecretSaveResponse> {
        const response = await this.post('/api/secret/save', {
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name, secret, type }),
        });

        if (!response.ok) {
            const error = (await response.json()) as ErrorResponse;
            throw new Error(error.message || error.error);
        }

        return (await response.json()) as SecretSaveResponse;
    }

    async listSecrets(type?: SecretType): Promise<SecretListResponse> {
        const params = type ? `?type=${encodeURIComponent(type)}` : '';
        const response = await this.get(`/api/secret/list${params}`);

        if (!response.ok) {
            const error = (await response.json()) as ErrorResponse;
            throw new Error(error.message || error.error);
        }

        return (await response.json()) as SecretListResponse;
    }

    async deleteSecret(name: string): Promise<SecretDeleteResponse> {
        const response = await this.delete(
            `/api/secret/${encodeURIComponent(name)}`,
        );

        if (!response.ok) {
            const error = (await response.json()) as ErrorResponse;
            throw new Error(error.message || error.error);
        }

        return (await response.json()) as SecretDeleteResponse;
    }

    async getSecret(name: string): Promise<SecretGetResponse> {
        const response = await this.get(
            `/api/secret/${encodeURIComponent(name)}`,
        );

        if (!response.ok) {
            const error = (await response.json()) as ErrorResponse;
            throw new Error(error.message || error.error);
        }

        return (await response.json()) as SecretGetResponse;
    }

    async refreshOAuthToken(
        name: string,
        clientId: string,
        clientSecret: string,
    ): Promise<OAuthRefreshResponse> {
        const response = await this.post('/api/secret/oauth/refresh', {
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name, clientId, clientSecret }),
        });

        if (!response.ok) {
            const error = (await response.json()) as ErrorResponse;
            throw new Error(error.message || error.error);
        }

        return (await response.json()) as OAuthRefreshResponse;
    }

    // Log methods

    async listLogs(options: LogListOptions = {}): Promise<LogListResponse> {
        const params = new URLSearchParams();
        if (options.workflowId) params.set('workflowId', options.workflowId);
        if (options.runId) params.set('runId', options.runId);
        if (options.source) params.set('source', options.source);
        if (options.limit !== undefined)
            params.set('limit', String(options.limit));
        if (options.offset !== undefined)
            params.set('offset', String(options.offset));

        const queryString = params.toString();
        const path = queryString
            ? `/api/log/list?${queryString}`
            : '/api/log/list';

        const response = await this.get(path);

        if (!response.ok) {
            const error = (await response.json()) as ErrorResponse;
            throw new Error(error.message || error.error);
        }

        return (await response.json()) as LogListResponse;
    }

    async listRuns(
        workflowId: string,
        options?: { limit?: number; offset?: number },
    ): Promise<RunListResponse> {
        const params = new URLSearchParams({ workflowId });
        if (options?.limit !== undefined)
            params.set('limit', String(options.limit));
        if (options?.offset !== undefined)
            params.set('offset', String(options.offset));

        const response = await this.get(`/api/log/runs?${params.toString()}`);

        if (!response.ok) {
            const error = (await response.json()) as ErrorResponse;
            throw new Error(error.message || error.error);
        }

        return (await response.json()) as RunListResponse;
    }
}
