/**
 * Component Styles Library
 *
 * Centralized, reusable component styling utilities using Tailwind classes.
 * These utilities provide consistent styling patterns across the application.
 */

import { cn } from './utils'

/**
 * Button Variants
 * Consistent button styles with size and variant options
 */
export const buttonStyles = {
  base: 'inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',

  variants: {
    primary: 'bg-primary text-primary-foreground hover:bg-primary/90',
    secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/90',
    destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
    outline: 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
    ghost: 'hover:bg-accent hover:text-accent-foreground',
    link: 'text-primary underline-offset-4 hover:underline',
  },

  sizes: {
    sm: 'h-9 px-3 text-sm',
    md: 'h-10 px-4 py-2',
    lg: 'h-11 px-8',
    icon: 'h-10 w-10',
  },
}

export function getButtonStyles(
  variant: keyof typeof buttonStyles.variants = 'primary',
  size: keyof typeof buttonStyles.sizes = 'md',
  className?: string
) {
  return cn(
    buttonStyles.base,
    buttonStyles.variants[variant],
    buttonStyles.sizes[size],
    className
  )
}

/**
 * Card Variants
 * Consistent card container styles
 */
export const cardStyles = {
  base: 'rounded-lg border bg-card text-card-foreground shadow-sm',

  variants: {
    default: 'border-border',
    elevated: 'border-border shadow-md',
    interactive: 'border-border transition-all hover:border-primary/50 hover:shadow-md cursor-pointer',
    success: 'border-success/20 bg-success/5',
    warning: 'border-warning/20 bg-warning/5',
    error: 'border-error/20 bg-error/5',
  },

  padding: {
    none: '',
    sm: 'p-3',
    md: 'p-4',
    lg: 'p-6',
    xl: 'p-8',
  },
}

export function getCardStyles(
  variant: keyof typeof cardStyles.variants = 'default',
  padding: keyof typeof cardStyles.padding = 'md',
  className?: string
) {
  return cn(
    cardStyles.base,
    cardStyles.variants[variant],
    cardStyles.padding[padding],
    className
  )
}

/**
 * Input Variants
 * Consistent form input styles
 */
export const inputStyles = {
  base: 'flex w-full rounded-md border bg-input px-3 py-2 text-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',

  variants: {
    default: 'border-border',
    error: 'border-error focus-visible:ring-error',
    success: 'border-success focus-visible:ring-success',
  },

  sizes: {
    sm: 'h-8 text-xs',
    md: 'h-10 text-sm',
    lg: 'h-12 text-base',
  },
}

export function getInputStyles(
  variant: keyof typeof inputStyles.variants = 'default',
  size: keyof typeof inputStyles.sizes = 'md',
  className?: string
) {
  return cn(
    inputStyles.base,
    inputStyles.variants[variant],
    inputStyles.sizes[size],
    className
  )
}

/**
 * Badge Variants
 * Consistent badge/pill styles for status indicators
 */
export const badgeStyles = {
  base: 'inline-flex items-center rounded-full font-medium transition-colors',

  variants: {
    default: 'bg-primary/10 text-primary',
    secondary: 'bg-secondary/10 text-secondary',
    success: 'bg-success/10 text-success',
    warning: 'bg-warning/10 text-warning',
    error: 'bg-error/10 text-error',
    muted: 'bg-muted text-muted-foreground',
    outline: 'border border-border bg-transparent',
  },

  sizes: {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
    lg: 'px-3 py-1.5 text-base',
  },
}

export function getBadgeStyles(
  variant: keyof typeof badgeStyles.variants = 'default',
  size: keyof typeof badgeStyles.sizes = 'sm',
  className?: string
) {
  return cn(
    badgeStyles.base,
    badgeStyles.variants[variant],
    badgeStyles.sizes[size],
    className
  )
}

/**
 * Typography Variants
 * Consistent text styles
 */
export const typographyStyles = {
  h1: 'scroll-m-20 text-4xl font-extrabold tracking-tight lg:text-5xl',
  h2: 'scroll-m-20 text-3xl font-semibold tracking-tight',
  h3: 'scroll-m-20 text-2xl font-semibold tracking-tight',
  h4: 'scroll-m-20 text-xl font-semibold tracking-tight',
  p: 'leading-7',
  lead: 'text-xl text-muted-foreground',
  large: 'text-lg font-semibold',
  small: 'text-sm font-medium leading-none',
  muted: 'text-sm text-muted-foreground',
  code: 'relative rounded bg-muted px-[0.3rem] py-[0.2rem] font-mono text-sm font-semibold',
}

export function getTypographyStyles(
  variant: keyof typeof typographyStyles,
  className?: string
) {
  return cn(typographyStyles[variant], className)
}

/**
 * Table Styles
 * Consistent table component styles
 */
export const tableStyles = {
  wrapper: 'relative w-full overflow-auto',
  table: 'w-full caption-bottom text-sm',
  header: 'border-b border-border',
  headerRow: '[&_tr]:border-b',
  headerCell: 'h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0',
  body: '[&_tr:last-child]:border-0',
  row: 'border-b border-border transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted',
  cell: 'p-4 align-middle [&:has([role=checkbox])]:pr-0',
  footer: 'border-t border-border bg-muted/50 font-medium [&>tr]:last:border-b-0',
}

/**
 * Loading States
 * Consistent loading and skeleton styles
 */
export const loadingStyles = {
  spinner: 'animate-spin rounded-full border-2 border-current border-t-transparent',
  skeleton: 'animate-pulse rounded-md bg-muted',
  dots: 'flex items-center gap-1',
  dot: 'h-2 w-2 rounded-full bg-current',
}

/**
 * Transition/Animation Utilities
 */
export const transitionStyles = {
  fast: 'transition-all duration-150 ease-out',
  normal: 'transition-all duration-200 ease-out',
  slow: 'transition-all duration-300 ease-out',
  colors: 'transition-colors duration-200',
  transform: 'transition-transform duration-200',
  opacity: 'transition-opacity duration-200',
}

/**
 * Focus Styles
 * Consistent keyboard focus indicators
 */
export const focusStyles = {
  ring: 'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  visible: 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
  within: 'focus-within:outline-none focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2',
}

/**
 * Layout Utilities
 */
export const layoutStyles = {
  container: 'container mx-auto px-4 sm:px-6 lg:px-8',
  section: 'py-12 md:py-16 lg:py-20',
  stack: {
    xs: 'space-y-1',
    sm: 'space-y-2',
    md: 'space-y-4',
    lg: 'space-y-6',
    xl: 'space-y-8',
  },
  grid: {
    '2col': 'grid grid-cols-1 md:grid-cols-2 gap-4',
    '3col': 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4',
    '4col': 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4',
  },
}
