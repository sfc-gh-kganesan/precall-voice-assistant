'use client'

import { useRouter } from 'next/navigation'
import { SnowflakeLogo } from '@/components/ui/SnowflakeLogo'

interface ConfigurationHeaderProps {
  configName: string
}

export function ConfigurationHeader({ configName }: ConfigurationHeaderProps) {
  const router = useRouter()

  return (
    <header className="border-b border-border bg-card shadow-sm">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          {/* Left: Logo and Title */}
          <div className="flex items-center gap-3">
            <SnowflakeLogo size={36} />
            <div>
              <h1 className="text-xl font-bold text-foreground">
                Support Intelligence
              </h1>
              <p className="text-xs text-muted-foreground">
                Configuration: {configName}
              </p>
            </div>
          </div>

          {/* Right: Navigation Actions */}
          <div className="flex gap-3">
            <button
              onClick={() => router.push('/dashboard')}
              className="px-4 py-2 text-sm font-medium border border-border rounded-md hover:bg-muted transition-colors"
            >
              View Dashboard
            </button>
            <button
              onClick={() => router.push('/admin')}
              className="px-4 py-2 text-sm font-medium border border-border rounded-md hover:bg-muted transition-colors"
            >
              Back to Admin
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}
