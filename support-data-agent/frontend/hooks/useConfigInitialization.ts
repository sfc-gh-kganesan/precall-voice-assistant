'use client'

import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAppStore } from '@/stores/appStore'
import { adminApi } from '@/services/api'

/**
 * Hook to initialize the active configuration on app startup.
 *
 * Fetches all configurations from the backend (which queries the CONFIGURATIONS
 * table in Snowflake) and automatically sets the newest one as the active config.
 *
 * This ensures that dashboard, topics, and products pages have an active config
 * to query data against.
 */
export function useConfigInitialization() {
  const { activeConfigId, setActiveConfigId, setIsInitializing } = useAppStore()
  const hasInitialized = useRef(false)

  // Fetch all configurations from backend
  const { data: configurations, isLoading } = useQuery({
    queryKey: ['configurations'],
    queryFn: () => adminApi.getAllConfigurations(),
    staleTime: 1000 * 60 * 5, // Cache for 5 minutes
  })

  useEffect(() => {
    // Update the initializing state
    setIsInitializing(isLoading)

    // Only run initialization once
    if (hasInitialized.current || isLoading) {
      return
    }

    // If we have configs and no active config is set, set the newest one
    if (configurations && configurations.length > 0) {
      // Backend already sorts by createdAt DESC (newest first)
      const newestConfig = configurations[0]

      // If there's no active config or the active config doesn't exist anymore
      const activeConfigExists = configurations.some(
        (c) => c.configId === activeConfigId
      )

      if (!activeConfigId || !activeConfigExists) {
        setActiveConfigId(newestConfig.configId)
      }

      hasInitialized.current = true
    } else if (configurations && configurations.length === 0) {
      // No configs exist, ensure activeConfigId is null
      if (activeConfigId) {
        setActiveConfigId(null)
      }
      hasInitialized.current = true
    }
  }, [configurations, isLoading, activeConfigId, setActiveConfigId, setIsInitializing])

  return { isInitializing: isLoading }
}
