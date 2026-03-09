import type {
    Interrupt,
    InterruptListResponse,
    LogListResponse,
    RunListResponse,
    WhoamiResponse,
    WorkflowListResponse,
    WorkflowManifestResponse,
    WorkflowRunAccepted,
    WorkflowRunResponse,
    WorkflowRunStatusResponse,
} from './types';

const BASE_URL = '/api';

async function fetchApi<T>(
    endpoint: string,
    options?: RequestInit,
): Promise<T> {
    const response = await fetch(`${BASE_URL}${endpoint}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options?.headers,
        },
    });

    if (!response.ok) {
        const error = await response
            .json()
            .catch(() => ({ error: 'Unknown error' }));
        throw new Error(
            error.message || error.error || `HTTP ${response.status}`,
        );
    }

    return response.json();
}

export const api = {
    whoami: () => fetchApi<WhoamiResponse>('/whoami'),

    workflows: {
        list: () => fetchApi<WorkflowListResponse>('/workflow/list'),

        getManifest: (workflowId: string) =>
            fetchApi<WorkflowManifestResponse>(
                `/workflow/${workflowId}/manifest`,
            ),

        run: (
            workflowId: string,
            params?: Record<string, string>,
            sync = false,
        ) =>
            fetchApi<WorkflowRunResponse | WorkflowRunAccepted>(
                `/workflow/${workflowId}/run${sync ? '?sync=true' : ''}`,
                {
                    method: 'POST',
                    body: JSON.stringify({ params }),
                },
            ),

        getRunStatus: (runId: string) =>
            fetchApi<WorkflowRunStatusResponse>(`/workflow/runs/${runId}`),

        delete: (workflowId: string) =>
            fetchApi<{ deleted: boolean; workflowId: string }>(
                `/workflow/${workflowId}`,
                { method: 'DELETE' },
            ),

        setVisibility: (workflowId: string, visibility: 'Private' | 'Public') =>
            fetchApi<{ workflowId: string; visibility: string }>(
                `/workflow/${workflowId}/visibility`,
                {
                    method: 'PATCH',
                    body: JSON.stringify({ visibility }),
                },
            ),

        getVersions: (name: string) =>
            fetchApi<WorkflowListResponse>(`/workflow/name/${name}/versions`),
    },

    logs: {
        listRuns: (workflowId: string, limit = 20, offset = 0) =>
            fetchApi<RunListResponse>(
                `/log/runs?workflowId=${workflowId}&limit=${limit}&offset=${offset}`,
            ),

        listLogs: (
            workflowId: string,
            runId: string,
            options?: { source?: string; limit?: number; offset?: number },
        ) => {
            const params = new URLSearchParams({
                workflowId,
                runId,
                limit: String(options?.limit ?? 100),
                offset: String(options?.offset ?? 0),
            });
            if (options?.source) params.set('source', options.source);
            return fetchApi<LogListResponse>(`/log/list?${params}`);
        },
    },

    interrupts: {
        list: (options?: {
            workflowId?: string;
            runId?: string;
            status?: string;
            limit?: number;
            offset?: number;
        }) => {
            const params = new URLSearchParams();
            if (options?.workflowId)
                params.set('workflowId', options.workflowId);
            if (options?.runId) params.set('runId', options.runId);
            if (options?.status) params.set('status', options.status);
            if (options?.limit) params.set('limit', String(options.limit));
            if (options?.offset) params.set('offset', String(options.offset));
            return fetchApi<InterruptListResponse>(
                `/workflow/interrupts?${params}`,
            );
        },

        get: (interruptId: string) =>
            fetchApi<Interrupt>(`/workflow/interrupts/${interruptId}`),

        resume: (interruptId: string, response: unknown) =>
            fetchApi<{
                success: boolean;
                interruptId: string;
                resumedAt: string;
                nextInterrupt?: unknown;
                status?: string;
            }>(`/workflow/interrupts/${interruptId}/resume`, {
                method: 'POST',
                body: JSON.stringify({ response }),
            }),
    },
};
