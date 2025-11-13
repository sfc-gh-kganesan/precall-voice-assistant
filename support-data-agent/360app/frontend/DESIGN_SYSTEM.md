# Design System Documentation

## Overview

This design system provides a comprehensive set of reusable styles, components, and design tokens for the Support Intelligence Platform. It ensures visual consistency, accessibility, and maintainability across the application.

## Architecture

The design system is built on three main pillars:

1. **Design Tokens** (`lib/design-tokens.ts`) - Fundamental design values
2. **Component Styles** (`lib/component-styles.ts`) - Reusable component styling utilities
3. **Global Styles** (`app/globals.css`) - Base styles and CSS custom properties

## Design Tokens

Design tokens are the atomic values of our design system. They define spacing, typography, colors, and other fundamental design decisions.

### Location
`lib/design-tokens.ts`

### Available Tokens

#### Spacing Scale
```typescript
import { spacing } from '@/lib/design-tokens'

// Usage examples:
// spacing[2]  -> '0.5rem' (8px)
// spacing[4]  -> '1rem' (16px)
// spacing[8]  -> '2rem' (32px)
```

#### Typography
```typescript
import { fontSize, fontWeight } from '@/lib/design-tokens'

// Font sizes with line heights
// fontSize.sm -> ['0.875rem', { lineHeight: '1.25rem' }]
// fontSize.lg -> ['1.125rem', { lineHeight: '1.75rem' }]

// Font weights
// fontWeight.normal -> '400'
// fontWeight.semibold -> '600'
```

#### Border Radius
```typescript
import { borderRadius } from '@/lib/design-tokens'

// borderRadius.sm -> '0.125rem'
// borderRadius.lg -> '0.5rem'
// borderRadius.full -> '9999px'
```

#### Shadows
```typescript
import { boxShadow } from '@/lib/design-tokens'

// boxShadow.sm -> '0 1px 2px 0 rgb(0 0 0 / 0.05)'
// boxShadow.md -> '0 4px 6px -1px rgb(0 0 0 / 0.1)...'
```

#### Animation
```typescript
import { duration, easing } from '@/lib/design-tokens'

// duration.fast -> '150ms'
// duration.normal -> '200ms'
// easing.inOut -> 'cubic-bezier(0.4, 0, 0.2, 1)'
```

## Component Styles

Component styles provide consistent, reusable styling patterns using Tailwind utility classes.

### Location
`lib/component-styles.ts`

### Button Styles

```typescript
import { getButtonStyles } from '@/lib/component-styles'

// Basic usage
<button className={getButtonStyles('primary', 'md')}>
  Click me
</button>

// With custom classes
<button className={getButtonStyles('secondary', 'lg', 'w-full')}>
  Full width button
</button>
```

**Variants:**
- `primary` - Primary action button (Snowflake blue background)
- `secondary` - Secondary action button
- `destructive` - Destructive actions (red)
- `outline` - Outlined button
- `ghost` - Minimal button with hover effect
- `link` - Text link style

**Sizes:**
- `sm` - Small (h-9, px-3)
- `md` - Medium (h-10, px-4) - Default
- `lg` - Large (h-11, px-8)
- `icon` - Icon button (h-10, w-10)

### Card Styles

```typescript
import { getCardStyles } from '@/lib/component-styles'

// Basic card
<div className={getCardStyles('default', 'md')}>
  Card content
</div>

// Elevated card with large padding
<div className={getCardStyles('elevated', 'lg')}>
  Card content
</div>
```

**Variants:**
- `default` - Standard card
- `elevated` - Card with shadow
- `interactive` - Hoverable card with pointer
- `success` - Success state (green tint)
- `warning` - Warning state (orange tint)
- `error` - Error state (red tint)

**Padding:**
- `none` - No padding
- `sm` - Small (p-3)
- `md` - Medium (p-4) - Default
- `lg` - Large (p-6)
- `xl` - Extra large (p-8)

### Input Styles

```typescript
import { getInputStyles } from '@/lib/component-styles'

// Text input
<input
  type="text"
  className={getInputStyles('default', 'md')}
  placeholder="Enter text..."
/>

// Error state
<input
  type="email"
  className={getInputStyles('error', 'md')}
/>
```

**Variants:**
- `default` - Standard input
- `error` - Error state (red border and ring)
- `success` - Success state (green border and ring)

**Sizes:**
- `sm` - Small (h-8, text-xs)
- `md` - Medium (h-10, text-sm) - Default
- `lg` - Large (h-12, text-base)

### Badge Styles

```typescript
import { getBadgeStyles } from '@/lib/component-styles'

// Status badge
<span className={getBadgeStyles('success', 'sm')}>
  Active
</span>

// Outlined badge
<span className={getBadgeStyles('outline', 'md')}>
  Beta
</span>
```

**Variants:**
- `default` - Primary color
- `secondary` - Secondary color
- `success` - Green
- `warning` - Orange
- `error` - Red
- `muted` - Gray
- `outline` - Transparent with border

**Sizes:**
- `sm` - Small (text-xs) - Default
- `md` - Medium (text-sm)
- `lg` - Large (text-base)

### Typography Styles

```typescript
import { getTypographyStyles } from '@/lib/component-styles'

// Headings
<h1 className={getTypographyStyles('h1')}>Page Title</h1>
<h2 className={getTypographyStyles('h2')}>Section Title</h2>

// Text
<p className={getTypographyStyles('p')}>Body text</p>
<p className={getTypographyStyles('muted')}>Muted text</p>
```

**Variants:**
- `h1`, `h2`, `h3`, `h4` - Heading levels
- `p` - Paragraph
- `lead` - Lead paragraph (larger, muted)
- `large` - Large text
- `small` - Small text
- `muted` - Muted text
- `code` - Inline code

### Table Styles

```typescript
import { tableStyles } from '@/lib/component-styles'

<div className={tableStyles.wrapper}>
  <table className={tableStyles.table}>
    <thead className={tableStyles.header}>
      <tr className={tableStyles.headerRow}>
        <th className={tableStyles.headerCell}>Header</th>
      </tr>
    </thead>
    <tbody className={tableStyles.body}>
      <tr className={tableStyles.row}>
        <td className={tableStyles.cell}>Data</td>
      </tr>
    </tbody>
  </table>
</div>
```

### Layout Utilities

```typescript
import { layoutStyles } from '@/lib/component-styles'

// Container
<div className={layoutStyles.container}>
  Centered container with responsive padding
</div>

// Spacing stacks
<div className={layoutStyles.stack.md}>
  <div>Item 1</div>
  <div>Item 2</div>
</div>

// Grid layouts
<div className={layoutStyles.grid['3col']}>
  <div>Column 1</div>
  <div>Column 2</div>
  <div>Column 3</div>
</div>
```

**Stack sizes:** `xs`, `sm`, `md`, `lg`, `xl`

**Grid layouts:** `2col`, `3col`, `4col` (responsive)

## Color System

Colors are defined using CSS custom properties in `app/globals.css` and follow the Snowflake brand guidelines.

### Semantic Colors

```css
/* In your components */
className="bg-primary text-primary-foreground"
className="bg-secondary text-secondary-foreground"
className="bg-accent text-accent-foreground"
className="bg-destructive text-destructive-foreground"
```

### State Colors

```css
className="text-success"  /* Green - positive states */
className="text-warning"  /* Orange - warning states */
className="text-error"    /* Red - error states */
```

### Neutral Colors

```css
className="bg-background"        /* App background */
className="bg-card"              /* Card background */
className="text-foreground"      /* Primary text */
className="text-muted-foreground" /* Secondary text */
className="border-border"        /* Border color */
```

## Global CSS Classes

In addition to the component utilities, several global CSS classes are available:

### Utility Classes

```css
.hover-opacity      /* Smooth opacity transition on hover */
.disabled-state     /* Disabled appearance */
.focus-ring         /* Focus ring for accessibility */
```

### Component Base Classes

```css
.btn                /* Base button styles */
.card               /* Base card styles */
.input              /* Base input styles */
.badge              /* Base badge styles */
.link               /* Link styles */
```

### Layout Classes

```css
.container-custom   /* Container with responsive padding */
.section            /* Section spacing */
```

## Best Practices

### 1. Use Design Tokens for Direct Styling

When you need specific values in JavaScript:

```typescript
import { spacing, duration } from '@/lib/design-tokens'

const styles = {
  padding: spacing[4],
  transitionDuration: duration.normal
}
```

### 2. Use Component Styles for Components

For React components, use the style utility functions:

```typescript
import { getButtonStyles, getCardStyles } from '@/lib/component-styles'

function MyComponent() {
  return (
    <div className={getCardStyles('default', 'md')}>
      <button className={getButtonStyles('primary', 'md')}>
        Action
      </button>
    </div>
  )
}
```

### 3. Combine with Custom Classes

All style functions accept an optional className parameter:

```typescript
<button className={getButtonStyles('primary', 'md', 'w-full mt-4')}>
  Full width with margin
</button>
```

### 4. Use Semantic Colors

Always use semantic color names rather than specific colors:

```typescript
// Good
className="text-foreground bg-card border-border"

// Avoid
className="text-white bg-gray-800 border-gray-700"
```

### 5. Maintain Consistency

- Use the design system utilities instead of inline Tailwind classes for common patterns
- Refer to this documentation when styling new components
- Update the design system if you find yourself repeating patterns

## Accessibility

The design system includes accessibility features by default:

- **Focus indicators:** All interactive elements have visible focus rings
- **Color contrast:** All color combinations meet WCAG AA standards
- **Semantic HTML:** Component styles work with proper semantic HTML
- **Keyboard navigation:** All interactive elements are keyboard accessible

## Dark Mode

The application uses dark mode by default. All colors are defined using CSS custom properties that can be themed:

```css
:root {
  --background: 222 47% 11%;
  --foreground: 210 20% 98%;
  /* ... other colors */
}
```

## Migration Guide

To migrate existing components to use the design system:

### Before
```typescript
<div className="bg-card border border-border rounded-lg p-6">
  <button className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90">
    Click me
  </button>
</div>
```

### After
```typescript
import { getCardStyles, getButtonStyles } from '@/lib/component-styles'

<div className={getCardStyles('default', 'lg')}>
  <button className={getButtonStyles('primary', 'md')}>
    Click me
  </button>
</div>
```

## Contributing

When adding new patterns to the design system:

1. Add design tokens if introducing new fundamental values
2. Create style utilities in `component-styles.ts` for reusable patterns
3. Document the new patterns in this file
4. Use the `cn()` utility from `lib/utils.ts` to merge classes safely

## Examples

### Complete Component Example

```typescript
'use client'

import {
  getCardStyles,
  getButtonStyles,
  getTypographyStyles,
  getBadgeStyles
} from '@/lib/component-styles'

export function FeatureCard({ title, description, status }) {
  return (
    <div className={getCardStyles('elevated', 'lg')}>
      <div className="flex items-start justify-between mb-4">
        <h3 className={getTypographyStyles('h3')}>{title}</h3>
        <span className={getBadgeStyles('success', 'sm')}>{status}</span>
      </div>

      <p className={getTypographyStyles('muted', 'mb-6')}>
        {description}
      </p>

      <button className={getButtonStyles('primary', 'md', 'w-full')}>
        Learn More
      </button>
    </div>
  )
}
```

### Form Example

```typescript
import { getInputStyles, getButtonStyles } from '@/lib/component-styles'

export function LoginForm() {
  return (
    <form className="space-y-4">
      <div>
        <label className="block text-sm font-medium mb-2">Email</label>
        <input
          type="email"
          className={getInputStyles('default', 'md')}
          placeholder="your@email.com"
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Password</label>
        <input
          type="password"
          className={getInputStyles('default', 'md')}
          placeholder="••••••••"
        />
      </div>

      <button
        type="submit"
        className={getButtonStyles('primary', 'md', 'w-full')}
      >
        Sign In
      </button>
    </form>
  )
}
```

## Support

For questions or suggestions about the design system, please reach out to the frontend team or create an issue in the repository.
