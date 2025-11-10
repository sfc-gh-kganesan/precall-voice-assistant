import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Format number with commas
export function formatNumber(num: number): string {
  return new Intl.NumberFormat('en-US').format(num)
}

// Format percentage
export function formatPercentage(num: number, decimals: number = 1): string {
  return `${num.toFixed(decimals)}%`
}

// Format duration in hours
export function formatDuration(hours: number): string {
  if (hours < 1) {
    return `${Math.round(hours * 60)}m`
  }
  if (hours < 24) {
    return `${hours.toFixed(1)}h`
  }
  return `${(hours / 24).toFixed(1)}d`
}

// Get trend arrow and color
export function getTrendInfo(changeType: 'increase' | 'decrease' | 'neutral') {
  switch (changeType) {
    case 'increase':
      return { arrow: '↑', className: 'text-success' }
    case 'decrease':
      return { arrow: '↓', className: 'text-error' }
    default:
      return { arrow: '→', className: 'text-muted' }
  }
}