import { useEffect, useRef, useState } from 'react';
import { api } from '@/api/client';
import { useTheme } from '@/components/BaltoThemeWrapper';

interface UserMenuProps {
    user: string;
}

export function UserMenu({ user }: UserMenuProps) {
    const [open, setOpen] = useState(false);
    const [copied, setCopied] = useState(false);
    const [endpoint, setEndpoint] = useState<string | null | undefined>(
        undefined,
    );
    const { mode, setMode } = useTheme();
    const menuRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!open) return;
        const handler = (e: MouseEvent) => {
            if (
                menuRef.current &&
                !menuRef.current.contains(e.target as Node)
            ) {
                setOpen(false);
            }
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, [open]);

    // Fetch endpoint on mount so it's ready when the menu opens
    useEffect(() => {
        api.getConfig()
            .then((config) => {
                const url = config.controldEndpoint
                    ? config.controldEndpoint.startsWith('https://')
                        ? config.controldEndpoint
                        : `https://${config.controldEndpoint}`
                    : null;
                setEndpoint(url);
            })
            .catch(() => setEndpoint(null));
    }, []);

    const handleCopyEndpoint = async () => {
        if (!endpoint) return;
        try {
            await navigator.clipboard.writeText(endpoint);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch {
            // ignore clipboard errors
        }
    };

    const themeModes: Array<{
        label: string;
        value: 'light' | 'dark' | 'auto';
    }> = [
        { label: 'Light', value: 'light' },
        { label: 'Dark', value: 'dark' },
        { label: 'Auto', value: 'auto' },
    ];

    return (
        <div ref={menuRef} style={{ position: 'relative' }}>
            <button
                type="button"
                onClick={() => setOpen((o) => !o)}
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    padding: '2px',
                    borderRadius: '4px',
                    color: 'var(--sf-gray-500)',
                    fontSize: '13px',
                    fontWeight: 500,
                    fontFamily: 'inherit',
                }}
                aria-label="User menu"
                aria-expanded={open}
            >
                <div
                    style={{
                        width: '26px',
                        height: '26px',
                        borderRadius: '50%',
                        background: 'var(--sf-blue-600)',
                        color: '#fff',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '12px',
                        fontWeight: 700,
                        flexShrink: 0,
                    }}
                >
                    {user.charAt(0).toUpperCase()}
                </div>
                {user}
            </button>

            {open && (
                <div
                    style={{
                        position: 'absolute',
                        top: 'calc(100% + 8px)',
                        right: 0,
                        background: 'var(--sf-surface)',
                        border: '1px solid var(--sf-gray-200)',
                        borderRadius: '8px',
                        boxShadow:
                            'var(--sf-shadow-md, 0 4px 16px rgba(0,0,0,0.12))',
                        minWidth: '220px',
                        zIndex: 100,
                        overflow: 'hidden',
                    }}
                >
                    <div
                        style={{
                            padding: '12px 16px',
                            fontSize: '13px',
                            fontWeight: 700,
                            color: 'var(--sf-gray-900)',
                            borderBottom: '1px solid var(--sf-gray-200)',
                        }}
                    >
                        {user}
                    </div>

                    <div
                        style={{
                            padding: '8px 16px',
                            borderBottom: '1px solid var(--sf-gray-200)',
                        }}
                    >
                        <div
                            style={{
                                fontSize: '11px',
                                fontWeight: 600,
                                color: 'var(--sf-gray-500)',
                                textTransform: 'uppercase',
                                letterSpacing: '0.06em',
                                marginBottom: '6px',
                            }}
                        >
                            API Endpoint
                        </div>
                        {endpoint === undefined ? (
                            <div
                                style={{
                                    fontSize: '12px',
                                    color: 'var(--sf-gray-400)',
                                }}
                            >
                                Loading...
                            </div>
                        ) : endpoint === null ? (
                            <div
                                style={{
                                    fontSize: '12px',
                                    color: 'var(--sf-gray-400)',
                                    fontStyle: 'italic',
                                }}
                            >
                                Not available
                            </div>
                        ) : (
                            <button
                                type="button"
                                onClick={handleCopyEndpoint}
                                title={endpoint}
                                style={{
                                    display: 'block',
                                    width: '100%',
                                    padding: '4px 8px',
                                    textAlign: 'left',
                                    background: copied
                                        ? 'var(--sf-green-50)'
                                        : 'var(--sf-gray-50)',
                                    border: '1px solid var(--sf-gray-200)',
                                    borderRadius: '4px',
                                    cursor: 'pointer',
                                    fontSize: '11px',
                                    fontFamily: 'monospace',
                                    color: copied
                                        ? 'var(--sf-green-600)'
                                        : 'var(--sf-gray-700)',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    whiteSpace: 'nowrap',
                                }}
                            >
                                {copied ? 'Copied!' : endpoint}
                            </button>
                        )}
                    </div>

                    <div
                        style={{
                            borderTop: '1px solid var(--sf-gray-200)',
                            padding: '8px 16px 12px',
                        }}
                    >
                        <div
                            style={{
                                fontSize: '11px',
                                fontWeight: 600,
                                color: 'var(--sf-gray-500)',
                                textTransform: 'uppercase',
                                letterSpacing: '0.06em',
                                marginBottom: '8px',
                            }}
                        >
                            Theme
                        </div>
                        <div style={{ display: 'flex', gap: '4px' }}>
                            {themeModes.map(({ label, value }) => (
                                <button
                                    key={value}
                                    type="button"
                                    onClick={() => setMode(value)}
                                    style={{
                                        flex: 1,
                                        padding: '5px 0',
                                        fontSize: '12px',
                                        fontWeight: mode === value ? 700 : 500,
                                        color:
                                            mode === value
                                                ? 'var(--sf-blue-600)'
                                                : 'var(--sf-gray-600)',
                                        background:
                                            mode === value
                                                ? 'var(--sf-blue-50, rgba(37,99,235,0.08))'
                                                : 'none',
                                        border:
                                            mode === value
                                                ? '1px solid var(--sf-blue-200, rgba(37,99,235,0.3))'
                                                : '1px solid var(--sf-gray-200)',
                                        borderRadius: '4px',
                                        cursor: 'pointer',
                                        fontFamily: 'inherit',
                                    }}
                                >
                                    {label}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
