# CSS Design System Guide

## Overview

The Support Intelligence Platform now uses a **centralized CSS design system** that allows you to style the entire application by editing a single CSS file. This makes it easy to maintain visual consistency and quickly customize the look and feel of the application.

## Quick Start

### To Change the Styling

Edit **one file**: `frontend/app/design-system.css`

This file contains:
- Color palettes
- Spacing scales
- Typography settings
- Component styles
- Logo colors
- Brand text

## File Structure

```
frontend/app/
  design-system.css     <- Edit this file to change styling
  globals.css           <- Imports design-system.css
```

## Common Customizations

### 1. Change Colors

Edit the color variables in `design-system.css`:

```css
:root {
  /* Primary brand color (buttons, links, etc.) */
  --color-primary: hsl(193, 82%, 53%);  /* Snowflake blue */

  /* Background colors */
  --color-bg-primary: hsl(222, 47%, 11%);     /* Main background */
  --color-bg-secondary: hsl(217, 33%, 17%);   /* Card background */

  /* Text colors */
  --color-text-primary: hsl(210, 20%, 98%);   /* Main text */
  --color-text-secondary: hsl(217, 10%, 65%); /* Secondary text */
}
```

### 2. Change Logo Color

Edit the logo color variable:

```css
:root {
  --logo-primary-color: var(--color-primary); /* Change to any color */
}
```

Example: Make the logo red:
```css
--logo-primary-color: #FF0000;
```

### 3. Change Brand Text

The brand name and tagline can be customized by editing the component props or the CSS variables:

**Option 1: Edit the AppHeader component usage**
```tsx
<AppHeader
  title="Your Company Name"
  subtitle="Your Tagline"
/>
```

**Option 2: Use CSS variables** (future enhancement)
```css
:root {
  --brand-name: 'Your Company Name';
  --brand-tagline: 'Your Tagline';
}
```

### 4. Change Spacing

Edit the spacing scale:

```css
:root {
  --spacing-xs: 0.25rem;   /* 4px */
  --spacing-sm: 0.5rem;    /* 8px */
  --spacing-md: 1rem;      /* 16px */
  --spacing-lg: 1.5rem;    /* 24px */
  --spacing-xl: 2rem;      /* 32px */
}
```

### 5. Change Typography

Edit font sizes and families:

```css
:root {
  /* Font families */
  --font-sans: 'Inter', sans-serif;
  --font-mono: 'SF Mono', monospace;

  /* Font sizes */
  --font-size-xs: 0.75rem;   /* 12px */
  --font-size-sm: 0.875rem;  /* 14px */
  --font-size-base: 1rem;    /* 16px */
  --font-size-xl: 1.25rem;   /* 20px */
}
```

### 6. Change Border Radius

Edit corner rounding:

```css
:root {
  --border-radius-sm: 0.25rem;  /* 4px - subtle corners */
  --border-radius-md: 0.5rem;   /* 8px - medium corners */
  --border-radius-lg: 0.75rem;  /* 12px - rounded corners */
}
```

### 7. Change Shadows

Edit shadow depths:

```css
:root {
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);
}
```

## Using Design System Classes

### Buttons

```tsx
<button className="btn-primary btn-md">Primary Button</button>
<button className="btn-secondary btn-lg">Secondary Button</button>
<button className="btn-ghost btn-sm">Ghost Button</button>
```

Available button classes:
- Variants: `btn-primary`, `btn-secondary`, `btn-ghost`
- Sizes: `btn-sm`, `btn-md`, `btn-lg`

### Cards

```tsx
<div className="card">
  <div className="card-header">
    <h3 className="card-title">Card Title</h3>
    <p className="card-description">Description text</p>
  </div>
  <p>Card content</p>
</div>
```

Available card classes:
- `card` - Base card style
- `card-elevated` - Card with shadow
- `card-interactive` - Hoverable card
- `card-header`, `card-title`, `card-description`

### Inputs

```tsx
<input type="text" className="input" placeholder="Enter text..." />
<input type="email" className="input input-error" />
<input type="text" className="input input-success" />
```

Available input classes:
- `input` - Base input style
- `input-error` - Error state
- `input-success` - Success state

### Badges

```tsx
<span className="badge badge-primary">Primary</span>
<span className="badge badge-success">Success</span>
<span className="badge badge-warning">Warning</span>
<span className="badge badge-error">Error</span>
```

### Typography

```tsx
<h1 className="text-h1">Heading 1</h1>
<h2 className="text-h2">Heading 2</h2>
<p className="text-body">Body text</p>
<p className="text-small">Small text</p>
<p className="text-muted">Muted text</p>
```

### Layout

```tsx
<div className="container">
  <div className="grid-3col">
    <div className="card">Item 1</div>
    <div className="card">Item 2</div>
    <div className="card">Item 3</div>
  </div>
</div>
```

Available layout classes:
- `container` - Centered container with max-width
- `grid-2col`, `grid-3col`, `grid-4col` - Responsive grids
- `flex-center`, `flex-between`, `flex-start` - Flexbox utilities
- `space-y-xs`, `space-y-sm`, `space-y-md`, `space-y-lg` - Vertical spacing

## Component Library

### AppHeader Component

The `AppHeader` component provides consistent branding and navigation across all pages.

**Basic Usage:**
```tsx
import { AppHeader } from '@/components/common/AppHeader'

export default function MyPage() {
  return (
    <div>
      <AppHeader />
      {/* Page content */}
    </div>
  )
}
```

**Custom Title:**
```tsx
<AppHeader title="Product Analytics" subtitle="Powered by Snowflake" />
```

**Custom Navigation:**
```tsx
<AppHeader
  navLinks={[
    { href: '/dashboard', label: 'Dashboard' },
    { href: '/analytics', label: 'Analytics' },
  ]}
/>
```

**With Actions:**
```tsx
<AppHeader
  actions={
    <button className="btn-primary btn-sm">Settings</button>
  }
/>
```

### SnowflakeLogo Component

The logo component automatically uses the color defined in `--logo-primary-color`.

```tsx
import { SnowflakeLogo } from '@/components/ui/SnowflakeLogo'

<SnowflakeLogo size={32} />
<SnowflakeLogo size={48} className="logo-snowflake-lg" />
```

## Design Tokens Reference

### Colors

| Variable | Default | Usage |
|----------|---------|-------|
| `--color-primary` | Snowflake blue | Primary actions, links |
| `--color-secondary` | Deep blue | Secondary actions |
| `--color-accent` | Cyan | Accent elements |
| `--color-success` | Green | Success states |
| `--color-warning` | Orange | Warning states |
| `--color-error` | Red | Error states |
| `--color-bg-primary` | Dark blue-gray | Main background |
| `--color-bg-secondary` | Darker gray | Card backgrounds |
| `--color-text-primary` | Off-white | Primary text |
| `--color-text-secondary` | Light gray | Secondary text |

### Spacing

| Variable | Size | Pixels |
|----------|------|--------|
| `--spacing-xs` | 0.25rem | 4px |
| `--spacing-sm` | 0.5rem | 8px |
| `--spacing-md` | 1rem | 16px |
| `--spacing-lg` | 1.5rem | 24px |
| `--spacing-xl` | 2rem | 32px |
| `--spacing-2xl` | 3rem | 48px |
| `--spacing-3xl` | 4rem | 64px |

### Typography

| Variable | Size | Pixels |
|----------|------|--------|
| `--font-size-xs` | 0.75rem | 12px |
| `--font-size-sm` | 0.875rem | 14px |
| `--font-size-base` | 1rem | 16px |
| `--font-size-lg` | 1.125rem | 18px |
| `--font-size-xl` | 1.25rem | 20px |
| `--font-size-2xl` | 1.5rem | 24px |
| `--font-size-3xl` | 1.875rem | 30px |
| `--font-size-4xl` | 2.25rem | 36px |

## Examples

### Example 1: Change to Light Theme

Edit `design-system.css`:

```css
:root {
  --color-bg-primary: hsl(0, 0%, 100%);      /* White */
  --color-bg-secondary: hsl(0, 0%, 98%);     /* Light gray */
  --color-text-primary: hsl(0, 0%, 10%);     /* Dark gray */
  --color-text-secondary: hsl(0, 0%, 40%);   /* Medium gray */
  --color-border-default: hsl(0, 0%, 85%);   /* Light border */
}
```

### Example 2: Change to Purple Accent

```css
:root {
  --color-primary: hsl(270, 70%, 60%);       /* Purple */
  --logo-primary-color: hsl(270, 70%, 60%);  /* Purple logo */
}
```

### Example 3: Increase All Spacing

```css
:root {
  --spacing-xs: 0.5rem;    /* 8px (was 4px) */
  --spacing-sm: 0.75rem;   /* 12px (was 8px) */
  --spacing-md: 1.5rem;    /* 24px (was 16px) */
  --spacing-lg: 2rem;      /* 32px (was 24px) */
  --spacing-xl: 3rem;      /* 48px (was 32px) */
}
```

### Example 4: Larger, Bolder Typography

```css
:root {
  --font-size-base: 1.125rem;  /* 18px (was 16px) */
  --font-size-lg: 1.25rem;     /* 20px (was 18px) */
  --font-weight-normal: 500;   /* Medium (was 400) */
  --font-weight-semibold: 700; /* Bold (was 600) */
}
```

## Best Practices

1. **Always use design tokens** - Use CSS custom properties (variables) instead of hardcoded values
2. **Use semantic color names** - Use `--color-primary` instead of specific color values
3. **Maintain consistency** - Stick to the spacing scale instead of arbitrary values
4. **Test changes** - After editing `design-system.css`, check multiple pages to ensure consistency
5. **Use the AppHeader component** - Don't duplicate header code across pages
6. **Document custom changes** - Add comments to explain why you changed defaults

## Migration from Old System

If you have existing components using inline Tailwind classes, you can gradually migrate them:

**Before:**
```tsx
<button className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90">
  Click me
</button>
```

**After:**
```tsx
<button className="btn-primary btn-md">
  Click me
</button>
```

## Troubleshooting

### Changes not appearing?

1. Clear your browser cache
2. Hard refresh (Cmd/Ctrl + Shift + R)
3. Restart the development server:
   ```bash
   npm run dev
   ```

### Colors look wrong?

Make sure you're using HSL format for colors that need Tailwind compatibility, or use hex/rgb for CSS-only colors:

```css
/* For Tailwind compatibility */
--color-primary: hsl(193, 82%, 53%);

/* For CSS-only use */
--color-snowflake-blue: #29B5E8;
```

### Logo not changing color?

The logo uses `currentColor` and inherits from the `.logo-snowflake` class. Make sure to edit:

```css
:root {
  --logo-primary-color: #YOUR_COLOR;
}
```

## Support

For questions or issues:
1. Check the `design-system.css` file comments
2. Review the `DESIGN_SYSTEM.md` documentation for the TypeScript design system
3. Look at existing component implementations in `/components`

## Resources

- **Design System CSS**: `frontend/app/design-system.css`
- **Global Styles**: `frontend/app/globals.css`
- **App Header**: `frontend/components/common/AppHeader.tsx`
- **Logo Component**: `frontend/components/ui/SnowflakeLogo.tsx`
- **Design Tokens (TS)**: `frontend/lib/design-tokens.ts`
- **Component Styles (TS)**: `frontend/lib/component-styles.ts`
