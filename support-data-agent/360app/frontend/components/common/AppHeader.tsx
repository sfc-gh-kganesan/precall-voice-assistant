'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { SnowflakeLogo } from '@/components/ui/SnowflakeLogo'
import { cn } from '@/lib/utils'

interface NavLink {
  href: string
  label: string
}

const defaultNavLinks: NavLink[] = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/products', label: 'Products' },
  { href: '/topics', label: 'Topics' },
  { href: '/tickets', label: 'Cases' },
  { href: '/admin', label: 'Admin' },
]

interface AppHeaderProps {
  title?: string
  subtitle?: string
  navLinks?: NavLink[]
  className?: string
  actions?: React.ReactNode
}

/**
 * AppHeader - Centralized header component with logo and navigation
 *
 * This component provides consistent branding and navigation across all pages.
 * Edit the Snowflake logo colors and brand text by modifying CSS variables in design-system.css:
 * - --logo-primary-color: Changes the logo color
 * - --brand-name: Changes the main title
 * - --brand-tagline: Changes the subtitle
 */
export function AppHeader({
  title = 'Support Intelligence',
  subtitle = 'Powered by Snowflake',
  navLinks = defaultNavLinks,
  className,
  actions,
}: AppHeaderProps) {
  const pathname = usePathname()

  return (
    <header className={cn('nav-header', className)}>
      <div className="nav-container">
        {/* Brand Section */}
        <div className="brand-header">
          <SnowflakeLogo size={36} className="logo-snowflake" />
          <div className="brand-header-text">
            <h1 className="brand-header-title">{title}</h1>
            <p className="brand-header-subtitle">{subtitle}</p>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="nav-links">
          {navLinks.map((link) => {
            const isActive = pathname === link.href
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn('nav-link', {
                  'nav-link-active': isActive,
                })}
              >
                {link.label}
              </Link>
            )
          })}
          {actions && <div className="flex items-center gap-3">{actions}</div>}
        </nav>
      </div>
    </header>
  )
}
