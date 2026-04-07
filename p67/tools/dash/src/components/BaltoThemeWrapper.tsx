import { BaltoProvider } from '@snowflake/stellar-components';
import {
    createContext,
    type ReactNode,
    useContext,
    useEffect,
    useState,
} from 'react';

type ThemeMode = 'light' | 'dark' | 'auto';

interface ThemeContextValue {
    mode: ThemeMode;
    setMode: (mode: ThemeMode) => void;
}

const ThemeContext = createContext<ThemeContextValue>({
    mode: 'auto',
    setMode: () => {},
});

export function useTheme(): ThemeContextValue {
    return useContext(ThemeContext);
}

function getSystemColorScheme(): 'light' | 'dark' {
    if (typeof window === 'undefined') return 'light';
    return window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light';
}

function readStoredMode(): ThemeMode {
    try {
        const stored = localStorage.getItem('p67-theme-mode');
        if (stored === 'light' || stored === 'dark' || stored === 'auto')
            return stored;
    } catch {
        // ignore
    }
    return 'auto';
}

interface BaltoThemeWrapperProps {
    children: ReactNode;
}

export function BaltoThemeWrapper({ children }: BaltoThemeWrapperProps) {
    const [mounted, setMounted] = useState(false);
    const [mode, setModeState] = useState<ThemeMode>('auto');
    const [systemScheme, setSystemScheme] = useState<'light' | 'dark'>(
        getSystemColorScheme,
    );

    useEffect(() => {
        setMounted(true);
        setModeState(readStoredMode());
        const mql = window.matchMedia('(prefers-color-scheme: dark)');
        const handler = (e: MediaQueryListEvent) =>
            setSystemScheme(e.matches ? 'dark' : 'light');
        mql.addEventListener('change', handler);
        return () => mql.removeEventListener('change', handler);
    }, []);

    const setMode = (newMode: ThemeMode) => {
        setModeState(newMode);
        try {
            localStorage.setItem('p67-theme-mode', newMode);
        } catch {
            // ignore
        }
    };

    const colorScheme: 'light' | 'dark' = mode === 'auto' ? systemScheme : mode;

    // Sync the data-theme attribute on <html> so CSS custom properties
    // in index.css switch between light and dark palettes.
    useEffect(() => {
        document.documentElement.dataset.theme = colorScheme;
    }, [colorScheme]);

    if (!mounted) {
        return null;
    }

    return (
        <ThemeContext.Provider value={{ mode, setMode }}>
            <BaltoProvider colorScheme={colorScheme}>{children}</BaltoProvider>
        </ThemeContext.Provider>
    );
}
