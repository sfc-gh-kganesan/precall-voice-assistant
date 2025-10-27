/**
 * API Error Handler Utilities
 * Provides generic functions for making API requests with error handling
 * and building query parameters from objects.
 */

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public statusText?: string
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

/**
 * Generic API request function with error handling
 * @param url - The URL to fetch
 * @param options - Optional fetch options
 * @returns Promise with typed response data
 */
export async function apiRequest<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    })

    if (!response.ok) {
      throw new ApiError(
        `API error: ${response.statusText}`,
        response.status,
        response.statusText
      )
    }

    return await response.json()
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    throw new ApiError(
      error instanceof Error ? error.message : 'Unknown API error occurred'
    )
  }
}

/**
 * Build query parameters string from an object
 * Handles arrays, undefined values, and proper encoding
 * @param params - Object with query parameters
 * @returns Query string (without leading ?)
 */
export function buildQueryParams(
  params: Record<string, string | number | boolean | string[] | Date | undefined>
): string {
  const searchParams = new URLSearchParams()

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null) {
      return
    }

    if (Array.isArray(value)) {
      value.forEach((item) => {
        searchParams.append(key, String(item))
      })
    } else if (value instanceof Date) {
      searchParams.append(key, value.toISOString())
    } else {
      searchParams.append(key, String(value))
    }
  })

  return searchParams.toString()
}
