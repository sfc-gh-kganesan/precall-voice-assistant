// React Query client configuration
import { QueryClient } from "react-query";

export const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            refetchOnWindowFocus: false,
            retry: 1,
            staleTime: 5000, // 5 seconds
            cacheTime: 300000, // 5 minutes
        },
        mutations: {
            retry: false,
        },
    },
});
