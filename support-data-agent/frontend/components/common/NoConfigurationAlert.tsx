'use client'

import { useRouter } from 'next/navigation'

export function NoConfigurationAlert() {
  const router = useRouter()

  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="max-w-md w-full bg-card border border-border rounded-lg p-8 text-center">
        <div className="mb-4">
          <svg
            className="w-16 h-16 mx-auto text-warning"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>

        <h2 className="text-xl font-semibold mb-2">No System Configuration Found</h2>

        <p className="text-muted-foreground mb-6">
          Please configure your data source in the Admin page to start viewing analytics and insights.
        </p>

        <button
          onClick={() => router.push('/admin')}
          className="w-full bg-primary text-primary-foreground px-6 py-3 rounded-md hover:bg-primary/90 font-medium"
        >
          Go to Admin Setup
        </button>

        <p className="text-xs text-muted-foreground mt-4">
          The admin setup will guide you through connecting your data source and configuring field mappings.
        </p>
      </div>
    </div>
  )
}
