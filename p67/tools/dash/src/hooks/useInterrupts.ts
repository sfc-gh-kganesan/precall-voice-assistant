import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';

export function useInterrupts(options?: {
    workflowId?: string;
    status?: string;
    limit?: number;
}) {
    return useQuery({
        queryKey: ['interrupts', options?.workflowId, options?.status],
        queryFn: () =>
            api.interrupts.list({
                workflowId: options?.workflowId,
                status: options?.status,
                limit: options?.limit,
            }),
        refetchInterval: 10000,
    });
}

export function useInterrupt(interruptId: string) {
    return useQuery({
        queryKey: ['interrupt', interruptId],
        queryFn: () => api.interrupts.get(interruptId),
        enabled: !!interruptId,
    });
}

export function useResumeInterrupt() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({
            interruptId,
            response,
        }: {
            interruptId: string;
            response: unknown;
        }) => api.interrupts.resume(interruptId, response),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['interrupts'] });
            queryClient.invalidateQueries({ queryKey: ['runs'] });
        },
    });
}
