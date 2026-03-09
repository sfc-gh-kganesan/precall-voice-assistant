import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import type {
    WorkflowRunAccepted,
    WorkflowRunStatusResponse,
} from '@/api/types';

export function useWorkflows() {
    return useQuery({
        queryKey: ['workflows'],
        queryFn: () => api.workflows.list(),
        refetchInterval: 10000,
    });
}

export function useWorkflowManifest(workflowId: string) {
    return useQuery({
        queryKey: ['workflow-manifest', workflowId],
        queryFn: () => api.workflows.getManifest(workflowId),
        enabled: !!workflowId,
    });
}

export function useWorkflowVersions(name: string | null) {
    return useQuery({
        queryKey: ['workflow-versions', name],
        queryFn: () => api.workflows.getVersions(name ?? ''),
        enabled: !!name,
    });
}

export function useRunWorkflow() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async ({
            workflowId,
            params,
        }: {
            workflowId: string;
            params?: Record<string, string>;
        }) => {
            const response = await api.workflows.run(workflowId, params);
            if ('exitCode' in response) {
                return response;
            }
            const accepted = response as WorkflowRunAccepted;
            const result = await pollForCompletion(accepted.runId);
            return result;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['workflows'] });
            queryClient.invalidateQueries({ queryKey: ['runs'] });
        },
    });
}

async function pollForCompletion(
    runId: string,
    maxAttempts = 120,
    interval = 1000,
): Promise<WorkflowRunStatusResponse> {
    for (let i = 0; i < maxAttempts; i++) {
        const status = await api.workflows.getRunStatus(runId);
        if (status.status !== 'running') {
            return status;
        }
        await new Promise((resolve) => setTimeout(resolve, interval));
    }
    throw new Error('Workflow execution timed out');
}

export function useRunStatus(runId: string | null) {
    return useQuery({
        queryKey: ['run-status', runId],
        queryFn: () => api.workflows.getRunStatus(runId ?? ''),
        enabled: !!runId,
        refetchInterval: (query) => {
            const data = query.state.data;
            if (data && data.status !== 'running') {
                return false;
            }
            return 1000;
        },
    });
}

export function useDeleteWorkflow() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (workflowId: string) => api.workflows.delete(workflowId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['workflows'] });
        },
    });
}

export function useSetVisibility() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({
            workflowId,
            visibility,
        }: {
            workflowId: string;
            visibility: 'Private' | 'Public';
        }) => api.workflows.setVisibility(workflowId, visibility),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['workflows'] });
        },
    });
}
