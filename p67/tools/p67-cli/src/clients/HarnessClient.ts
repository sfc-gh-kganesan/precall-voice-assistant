export interface HealthResponse {
  status: string;
  timestamp: string;
  localStoragePath: string;
}

export interface WorkflowCreateResponse {
  workflowId: string;
}

export interface WorkflowListResponse {
  workflows: string[];
}

export interface WorkflowRunResponse {
  exitCode: number;
  stdout: string;
  stderr: string;
  success: boolean;
}

export interface ErrorResponse {
  error: string;
  message?: string;
}

export interface HarnessClientConfig {
  baseUrl: string;
  timeout?: number;
}

export class HarnessClient {
  private _baseUrl: string;
  private _timeout: number;

  constructor(config: HarnessClientConfig) {
    this._baseUrl = config.baseUrl.replace(/\/$/, '');
    this._timeout = config.timeout || 30000;
  }

  public get baseUrl(): string {
    return this._baseUrl;
  }

  public get timeout(): number {
    return this._timeout;
  }

  async health(): Promise<HealthResponse> {
    const response = await fetch(`${this._baseUrl}/api/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: AbortSignal.timeout(this._timeout),
    });

    if (!response.ok) {
      const error = (await response.json()) as ErrorResponse;
      throw new Error(error.message || error.error);
    }

    return (await response.json()) as HealthResponse;
  }

  async createWorkflow(file: File | Blob, filename?: string): Promise<WorkflowCreateResponse> {
    const formData = new FormData();

    if (file instanceof File) {
      formData.append('file', file);
    } else {
      formData.append('file', file, filename || 'workflow.zip');
    }

    const response = await fetch(`${this._baseUrl}/api/workflow/create`, {
      method: 'POST',
      body: formData,
      signal: AbortSignal.timeout(this._timeout),
    });

    if (!response.ok) {
      const error = (await response.json()) as ErrorResponse;
      throw new Error(error.message || error.error);
    }

    return (await response.json()) as WorkflowCreateResponse;
  }

  async listWorkflows(): Promise<WorkflowListResponse> {
    const response = await fetch(`${this._baseUrl}/api/workflow/list`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: AbortSignal.timeout(this._timeout),
    });

    if (!response.ok) {
      const error = (await response.json()) as ErrorResponse;
      throw new Error(error.message || error.error);
    }

    return (await response.json()) as WorkflowListResponse;
  }

  async runWorkflow(workflowId: string): Promise<WorkflowRunResponse> {
    const response = await fetch(`${this._baseUrl}/api/workflow/${workflowId}/run`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: AbortSignal.timeout(this._timeout),
    });

    if (!response.ok) {
      const error = (await response.json()) as ErrorResponse;
      throw new Error(error.message || error.error);
    }

    return (await response.json()) as WorkflowRunResponse;
  }
}
