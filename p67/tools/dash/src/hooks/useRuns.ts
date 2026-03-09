import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';

export function useRuns(workflowId: string, limit = 20, offset = 0) {
    return useQuery({
        queryKey: ['runs', workflowId, limit, offset],
        queryFn: () => api.logs.listRuns(workflowId, limit, offset),
        enabled: !!workflowId,
        refetchInterval: 10000,
    });
}
