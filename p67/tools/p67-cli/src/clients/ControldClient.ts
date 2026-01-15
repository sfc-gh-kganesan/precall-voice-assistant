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

export interface ErrorResponse {
    error: string;
    message?: string;
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

    async runWorkflow(workflowId: string): Promise<WorkflowRunResponse> {
        const response = await this.post(`/api/workflow/${workflowId}/run`);

        if (!response.ok) {
            const error = (await response.json()) as ErrorResponse;
            throw new Error(error.message || error.error);
        }

        return (await response.json()) as WorkflowRunResponse;
    }
}
