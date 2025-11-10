'use client'

import { useRouter } from 'next/navigation'
import { useEffect } from 'react'

export default function Home() {
  const router = useRouter()

  useEffect(() => {
    // Redirect to dashboard on load
    router.push('/dashboard')
  }, [router])

  return (
    <div className="flex h-screen items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-primary mb-2">
          Support Intelligence
        </h1>
        <p className="text-muted">Redirecting to dashboard...</p>
      </div>
    </div>
  )
}
