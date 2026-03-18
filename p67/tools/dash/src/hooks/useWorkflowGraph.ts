import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';

export function useWorkflowGraph(workflowId: string) {
    return useQuery({
        queryKey: ['workflow-graph', workflowId],
        queryFn: () => api.workflows.getGraph(workflowId),
        enabled: !!workflowId,
    });
}
