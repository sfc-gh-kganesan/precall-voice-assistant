import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Query client configuration with caching and retry settings
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,      // 5 minutes
      gcTime: 10 * 60 * 1000,        // 10 minutes (formerly cacheTime in v4)
      retry: 1,                      // Simple retry
      refetchOnWindowFocus: false,
    },
  },
})

// Export provider component for use in app
export { QueryClientProvider }