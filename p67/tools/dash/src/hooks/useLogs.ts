import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { LogSource } from '@/api/types';

export function useLogs(
    workflowId: string,
    runId: string,
    options?: {
        source?: LogSource;
        limit?: number;
        offset?: number;
        autoRefresh?: boolean;
    },
) {
    return useQuery({
        queryKey: [
            'logs',
            workflowId,
            runId,
            options?.source,
            options?.limit,
            options?.offset,
        ],
        queryFn: () =>
            api.logs.listLogs(workflowId, runId, {
                source: options?.source,
                limit: options?.limit,
                offset: options?.offset,
            }),
        enabled: !!workflowId && !!runId,
        refetchInterval: options?.autoRefresh ? 5000 : false,
    });
}
