import { Button } from '@snowflake/stellar-components';
import type { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';

interface AppShellProps {
    children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
    const location = useLocation();

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
                    padding: '12px 24px',
                    borderBottom: '1px solid var(--color-border)',
                    backgroundColor: 'var(--color-surface)',
                }}
            >
                <div
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '24px',
                    }}
                >
                    <Link to="/" style={{ textDecoration: 'none' }}>
                        <h1
                            style={{
                                fontSize: '20px',
                                fontWeight: 600,
                                color: 'var(--color-text)',
                            }}
                        >
                            p67 Dashboard
                        </h1>
                    </Link>
                    <nav style={{ display: 'flex', gap: '8px' }}>
                        <Link to="/">
                            <Button
                                variant={
                                    location.pathname === '/'
                                        ? 'primary'
                                        : 'secondary'
                                }
                                size="small"
                            >
                                Workflows
                            </Button>
                        </Link>
                        <Link to="/interrupts">
                            <Button
                                variant={
                                    location.pathname === '/interrupts'
                                        ? 'primary'
                                        : 'secondary'
                                }
                                size="small"
                            >
                                Interrupts
                            </Button>
                        </Link>
                    </nav>
                </div>
            </header>
            <main style={{ flex: 1, padding: '24px' }}>{children}</main>
        </div>
    );
}
