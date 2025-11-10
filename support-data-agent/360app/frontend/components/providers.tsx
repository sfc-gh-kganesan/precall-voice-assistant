'use client'

import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from '@/lib/queryClient'
import { useConfigInitialization } from '@/hooks/useConfigInitialization'

function ConfigInitializer({ children }: { children: React.ReactNode }) {
  useConfigInitialization()
  return <>{children}</>
}

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <ConfigInitializer>
        {children}
      </ConfigInitializer>
    </QueryClientProvider>
  )
}
