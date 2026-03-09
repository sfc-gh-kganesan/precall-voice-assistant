import { BaltoProvider } from '@snowflake/stellar-components';
import { type ReactNode, useEffect, useState } from 'react';

interface BaltoThemeWrapperProps {
    children: ReactNode;
}

function getSystemColorScheme(): 'light' | 'dark' {
    if (typeof window === 'undefined') return 'light';
    return window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light';
}

export function BaltoThemeWrapper({ children }: BaltoThemeWrapperProps) {
    const [mounted, setMounted] = useState(false);
    const [colorScheme, setColorScheme] = useState<'light' | 'dark'>(
        getSystemColorScheme,
    );

    useEffect(() => {
        setMounted(true);
        const mql = window.matchMedia('(prefers-color-scheme: dark)');
        const handler = (e: MediaQueryListEvent) =>
            setColorScheme(e.matches ? 'dark' : 'light');
        mql.addEventListener('change', handler);
        return () => mql.removeEventListener('change', handler);
    }, []);

    if (!mounted) {
        return null;
    }

    return <BaltoProvider colorScheme={colorScheme}>{children}</BaltoProvider>;
}
