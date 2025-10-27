/**
 * Application Constants
 *
 * Centralized configuration for the Support Data Agent application.
 * Includes API config, UI limits, defaults, and error messages.
 */

// =============================================================================
// API Configuration
// =============================================================================

/**
 * API configuration including base URL and request settings
 */
export const API_CONFIG = {
  /**
   * Base URL for the backend API
   * Reads from NEXT_PUBLIC_SDA_SERVICE_URL environment variable
   * Falls back to localhost:8000 for local development
   */
  BASE_URL: typeof window !== 'undefined'
    ? (process.env.NEXT_PUBLIC_SDA_SERVICE_URL || 'http://localhost:8000')
    : (process.env.NEXT_PUBLIC_SDA_SERVICE_URL || 'http://backend:8000'),

  /**
   * Request timeout in milliseconds
   */
  TIMEOUT: 30000, // 30 seconds

  /**
   * Number of retry attempts for failed requests
   */
  RETRY_ATTEMPTS: 1,
} as const

// =============================================================================
// UI Constants
// =============================================================================

/**
 * UI-related constants for input limits, polling intervals, etc.
 */
export const UI_CONSTANTS = {
  /**
   * Maximum length for chat messages
   */
  MAX_MESSAGE_LENGTH: 500,

  /**
   * Default page size for paginated tables
   */
  DEFAULT_PAGE_SIZE: 20,

  /**
   * Polling interval for job status checks (in milliseconds)
   */
  POLLING_INTERVAL: 2000, // 2 seconds

  /**
   * Debounce delay for search inputs (in milliseconds)
   */
  DEBOUNCE_DELAY: 300,
} as const

// =============================================================================
// Default Values
// =============================================================================

/**
 * Default values used throughout the application
 */
export const DEFAULTS = {
  /**
   * Default session ID for chat interactions
   * In a real application, this would be generated per user session
   */
  SESSION_ID: 'default-session',

  /**
   * Default filter period
   */
  PERIOD: 'week' as const,

  /**
   * Default sort order
   */
  SORT_ORDER: 'desc' as const,
} as const

// =============================================================================
// React Query Configuration
// =============================================================================

/**
 * Configuration for React Query caching and refetching
 */
export const QUERY_CONFIG = {
  /**
   * Time before data is considered stale (in milliseconds)
   */
  STALE_TIME: 5 * 60 * 1000, // 5 minutes

  /**
   * Time before cached data is garbage collected (in milliseconds)
   */
  CACHE_TIME: 10 * 60 * 1000, // 10 minutes

  /**
   * Number of retry attempts for failed queries
   */
  RETRY_COUNT: 1,

  /**
   * Whether to refetch on window focus
   */
  REFETCH_ON_WINDOW_FOCUS: false,
} as const

// =============================================================================
// Error Messages
// =============================================================================

/**
 * Standardized error messages for consistent UX
 */
export const ERROR_MESSAGES = {
  /**
   * Generic errors
   */
  UNKNOWN_ERROR: 'An unknown error occurred',
  NETWORK_ERROR: 'Network error. Please check your connection',
  API_ERROR: 'API request failed',

  /**
   * Chat errors
   */
  CHAT_ERROR: 'Failed to send message',

  /**
   * Data fetching errors
   */
  FETCH_ERROR: 'Failed to load data',
  FETCH_KPI_ERROR: 'Failed to load KPI metrics',
  FETCH_PRODUCTS_ERROR: 'Failed to load product metrics',
  FETCH_TOPICS_ERROR: 'Failed to load topic metrics',
  FETCH_TICKETS_ERROR: 'Failed to load tickets',

  /**
   * Admin/Configuration errors
   */
  FETCH_CONFIG_ERROR: 'Failed to load configuration',
  SAVE_CONFIG_ERROR: 'Failed to save configuration',
  DELETE_CONFIG_ERROR: 'Failed to delete configuration',

  /**
   * Database errors
   */
  FETCH_DATABASES_ERROR: 'Failed to load databases',
  FETCH_SCHEMAS_ERROR: 'Failed to load schemas',
  FETCH_TABLES_ERROR: 'Failed to load tables',

  /**
   * Job errors
   */
  START_JOB_ERROR: 'Failed to start job',
  FETCH_JOB_STATUS_ERROR: 'Failed to fetch job status',
} as const

// =============================================================================
// Success Messages
// =============================================================================

/**
 * Standardized success messages
 */
export const SUCCESS_MESSAGES = {
  CONFIG_SAVED: 'Configuration saved successfully',
  CONFIG_DELETED: 'Configuration deleted successfully',
  JOB_STARTED: 'Job started successfully',
  ANALYTICS_STARTED: 'Analytics job started successfully',
} as const

// =============================================================================
// Route Paths
// =============================================================================

/**
 * Application route paths
 */
export const ROUTES = {
  HOME: '/',
  DASHBOARD: '/dashboard',
  PRODUCTS: '/products',
  TOPICS: '/topics',
  TICKETS: '/tickets',
  ADMIN: '/admin',
  ADMIN_CONFIG: '/admin/configuration',
} as const

// =============================================================================
// Type Exports
// =============================================================================

export type Period = typeof DEFAULTS.PERIOD
export type SortOrder = typeof DEFAULTS.SORT_ORDER
