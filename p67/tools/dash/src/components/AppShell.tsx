import { type ReactNode, useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { api } from '@/api/client';
import { UserMenu } from '@/components/UserMenu';

interface AppShellProps {
    children: ReactNode;
}

const NAV_ITEMS = [
    {
        path: '/',
        label: 'Workflows',
        match: (p: string) => p === '/' || p.startsWith('/workflow'),
    },
    {
        path: '/interrupts',
        label: 'Interrupts',
        match: (p: string) => p === '/interrupts',
    },
];

export function AppShell({ children }: AppShellProps) {
    const location = useLocation();
    const [user, setUser] = useState<string | null>(null);

    useEffect(() => {
        api.whoami()
            .then((res) => setUser(res.snowflakeUser))
            .catch(() => {});
    }, []);

    return (
        <div
            style={{
                display: 'flex',
                flexDirection: 'column',
                minHeight: '100vh',
            }}
        >
            <header
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0 24px',
                    height: '52px',
                    borderBottom: '1px solid var(--sf-gray-200)',
                    backgroundColor: 'var(--sf-surface)',
                    boxShadow: 'var(--sf-shadow-sm)',
                    position: 'sticky',
                    top: 0,
                    zIndex: 50,
                }}
            >
                <div
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '32px',
                    }}
                >
                    <Link
                        to="/"
                        style={{
                            textDecoration: 'none',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '10px',
                        }}
                    >
                        <svg
                            aria-hidden="true"
                            width="20"
                            height="20"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="var(--sf-blue-600)"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                        >
                            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                        </svg>
                        <span
                            style={{
                                fontSize: '15px',
                                fontWeight: 700,
                                color: 'var(--sf-gray-900)',
                                letterSpacing: '-0.02em',
                            }}
                        >
                            Workflow Studio
                        </span>
                    </Link>
                    <nav
                        style={{
                            display: 'flex',
                            gap: '2px',
                            height: '52px',
                            alignItems: 'stretch',
                        }}
                    >
                        {NAV_ITEMS.map((item) => {
                            const isActive = item.match(location.pathname);
                            return (
                                <Link
                                    key={item.path}
                                    to={item.path}
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        padding: '0 16px',
                                        fontSize: '13px',
                                        fontWeight: isActive ? 600 : 500,
                                        color: isActive
                                            ? 'var(--sf-blue-600)'
                                            : 'var(--sf-gray-500)',
                                        textDecoration: 'none',
                                        borderBottom: isActive
                                            ? '2px solid var(--sf-blue-600)'
                                            : '2px solid transparent',
                                        transition:
                                            'color 150ms ease, border-color 150ms ease',
                                    }}
                                >
                                    {item.label}
                                </Link>
                            );
                        })}
                    </nav>
                </div>
                {user && <UserMenu user={user} />}
            </header>
            <main style={{ flex: 1 }}>{children}</main>
        </div>
    );
}
