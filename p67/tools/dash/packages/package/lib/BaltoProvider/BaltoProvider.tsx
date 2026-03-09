import { Slot, Slottable } from '@radix-ui/react-slot';
import { UNSAFE_PortalProvider } from '@react-aria/overlays';
import { useLayoutEffect } from '@react-aria/utils';
import {
    baseColorStyles,
    baseDimensionNumberStyles,
    themeDarkStyles,
    themeLightStyles,
} from '@snowflake/balto-tokens';
import { baseTheme } from '@snowflake/stellar-tokens/themes/base.stylex';
import { compactTheme } from '@snowflake/stellar-tokens/themes/compact.stylex';
import * as stylex from '@stylexjs/stylex';
import { clsx } from 'clsx';
import type {
    ComponentPropsWithoutRef,
    CSSProperties,
    ForwardedRef,
    RefObject,
} from 'react';
import React, {
    forwardRef,
    useContext,
    useEffect,
    useMemo,
    useRef,
    useState,
} from 'react';

import type { BaltoColorScheme, BaltoContextValue, ThemeProp } from '../hooks';
import {
    BaltoContext,
    BaltoThemeProviderContext,
    defaultContextValue,
    useBaltoThemeProvider,
    useMergedStyles,
} from '../hooks';
import { Toaster } from '../Toast/Toast';
import type { Locale, TimeZone } from '../types';
import { devWarning } from '../util/dev-warning';
import { getThemesForColorScheme } from './getThemesForColorScheme';

const providerStyles = stylex.create({
    baltoProviderIsolate: {
        isolation: 'isolate',
    },
    portalContainer: {
        left: 0,
        position: 'fixed',
        top: 0,
        zIndex: 100000,
    },
});

interface ThemeProviderProps {
    /**
     * The class name of the theme provider.
     */
    className?: string | undefined;
    /**
     * The style of the theme provider.
     */
    style?: CSSProperties | undefined;
    /**
     * Whether to add base colors to the theme provider.
     */
    addBaseColors?: boolean | undefined;
    /**
     * The color scheme of the theme provider.
     */
    colorScheme?: BaltoColorScheme | undefined;
    /**
     * Whether to use the asChild prop.
     */
    asChild?: boolean | undefined;
    /**
     * The children of the theme provider.
     */
    children: React.ReactNode;
    /**
     * The themes to apply. This also inherits the parent themes.
     * If no prop is provided the parent themes are just applied
     */
    theme?: ThemeProp | undefined;
}

/**
 * The base theme of the theme provider.
 */
function useBaseTheme({
    colorScheme,
    includeBaseThemes = false,
    density = 'regular',
}: {
    /**
     * The color scheme of the theme provider.
     */
    colorScheme?: BaltoColorScheme | undefined;
    /**
     * Whether to include the base themes.
     */
    includeBaseThemes?: boolean | undefined;
    /**
     * The density of the theme provider.
     */
    density?: 'compact' | 'regular' | undefined;
}) {
    return useMemo(
        () => [
            ...getThemesForColorScheme(colorScheme ?? 'light', {
                includeBaseThemes,
            }),
            density === 'compact'
                ? compactTheme
                : density === 'regular'
                  ? baseTheme
                  : undefined,
        ],
        [colorScheme, includeBaseThemes, density],
    );
}

/** This is a hook that returns the system color scheme. */
function useSystemColorScheme() {
    const [colorScheme, setColorScheme] = useState<BaltoColorScheme>('light');

    useLayoutEffect(() => {
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

        // Set the initial color scheme based on the system preference
        if (typeof React.startTransition === 'function') {
            React.startTransition(() => {
                setColorScheme(mediaQuery.matches ? 'dark' : 'light');
            });
        } else {
            setColorScheme(mediaQuery.matches ? 'dark' : 'light');
        }

        /** Handle the change event from the media query. */
        function handleChange(event: MediaQueryListEvent) {
            setColorScheme(event.matches ? 'dark' : 'light');
        }

        mediaQuery.addEventListener('change', handleChange);

        return () => {
            mediaQuery.removeEventListener('change', handleChange);
        };
    }, []);

    return colorScheme;
}

interface BaltoProviderProps
    extends Omit<ComponentPropsWithoutRef<'div'>, 'children'>,
        ThemeProviderProps {
    /**
     * The locale of the theme provider.
     */
    locale?: Locale | undefined;
    /**
     * The time zone of the theme provider.
     */
    timeZone?: TimeZone | undefined;
    /**
     * Whether to disable isolation of the theme provider.
     */
    disableIsolation?: boolean | undefined;
    /**
     * Whether this is the root BaltoProvider.
     * If you are in an MFE you are not the root BaltoProvider, the host application is.
     *
     * @default true
     */
    isRoot?: boolean | undefined;
    /**
     * The default density.
     */
    density?: 'compact' | 'regular' | undefined;
}

declare global {
    interface Window {
        /**
         * Manages portals for Balto components inside of nested MFE.
         * This is not intended to be used by end users.
         */
        __internalBaltoPortalContainer?:
            | {
                  /**
                   * Create a portal element in the root portal.
                   */
                  createPortalElement: (id: string) => HTMLDivElement;
                  /**
                   * Destroy a portal element in the root portal.
                   */
                  destroyPortalElement: (id: string) => void;
              }
            | undefined;
    }
}

const NO_STYLES = {};
let portalId = 0;

/**
 * This enables balto providers in nested MFE to use the root portal.
 * This fixes many issues with z-index and portal positioning.
 */
function useSetUpPortalContainerManager(
    rootPortalRef: RefObject<HTMLDivElement>,
    isRoot: boolean,
) {
    const [portalRef, setPortalRef] = useState<HTMLDivElement | null>(null);

    useLayoutEffect(() => {
        if (!isRoot) return;

        const portals: Record<string, HTMLDivElement> = {};

        window.__internalBaltoPortalContainer = {
            createPortalElement: (id: string) => {
                const el = document.createElement('div');
                el.id = id;
                portals[id] = el;
                rootPortalRef.current?.appendChild(el);
                return el;
            },
            destroyPortalElement: (id: string) => {
                delete portals[id];
                const el = portals[id];

                if (el) {
                    rootPortalRef.current?.removeChild(el);
                }
            },
        };
    }, [rootPortalRef, isRoot]);

    useLayoutEffect(() => {
        const id = `stellar-portal-${portalId++}`;
        const el =
            window.__internalBaltoPortalContainer?.createPortalElement(id) ??
            null;
        setPortalRef(el);

        return () => {
            if (el) {
                window.__internalBaltoPortalContainer?.destroyPortalElement(id);
            }
        };
    }, [isRoot]);

    return portalRef;
}

const AppWrapper = forwardRef(function AppWrapper(
    props: BaltoProviderProps,
    ref: ForwardedRef<HTMLDivElement>,
) {
    const {
        colorScheme: colorSchemeProp,
        theme,
        addBaseColors = false,
        disableIsolation = false,
        asChild = false,
        className,
        style,
        children,
        locale,
        timeZone,
        isRoot = true,
        density = 'regular',
        ...rest
    } = props;
    const Component = asChild ? Slot : 'div';

    const systemColorScheme = useSystemColorScheme();
    const colorScheme = colorSchemeProp ?? systemColorScheme;

    const mergedStyles = useMergedStyles(
        getBaltoClassNames(className, addBaseColors, colorScheme),
        style,
        stylex.props(
            useBaseTheme({ colorScheme, includeBaseThemes: true, density }),
            theme,
            // additional styles for isolation only at root level BaltoProvider.AppWrapper
            !disableIsolation && providerStyles.baltoProviderIsolate,
        ),
    );
    const portalStyles = useMergedStyles(
        getBaltoClassNames('', addBaseColors, colorScheme),
        NO_STYLES,
        stylex.props(
            useBaseTheme({ colorScheme, includeBaseThemes: true, density }),
            theme,
            // additional styles for isolation only at root level BaltoProvider.AppWrapper
            !disableIsolation && providerStyles.baltoProviderIsolate,
        ),
    );

    // If a locale is not provided, use the browser's locale, removing suffix like in "en-US@posix".
    const [browserLocale, setBrowserLocale] = useState(locale ?? 'en-US');
    useLayoutEffect(() => {
        setBrowserLocale(
            locale ?? (navigator.language.split('@')[0] as Locale),
        );
    }, [locale]);

    // If a timeZone is not provided, use the browser's timeZone
    const [browserTimeZone, setBrowserTimeZone] = useState<TimeZone>(
        timeZone ?? 'America/Los_Angeles',
    );
    useLayoutEffect(() => {
        setBrowserTimeZone(
            timeZone ??
                (Intl.DateTimeFormat().resolvedOptions().timeZone as TimeZone),
        );
    }, [timeZone]);

    const rootPortalRef = useRef<HTMLDivElement | null>(null);
    const portalRef = useSetUpPortalContainerManager(rootPortalRef, isRoot);
    const contextValue = useMemo<BaltoContextValue>(
        () => ({
            colorScheme: colorScheme ?? 'light',
            locale: browserLocale,
            timeZone: browserTimeZone,
            styleValues:
                colorScheme === 'dark' ? themeDarkStyles : themeLightStyles,
            portalContainer: portalRef,
            dimensionValues: baseDimensionNumberStyles,
            colorValues: baseColorStyles,
        }),
        [colorScheme, browserLocale, browserTimeZone, portalRef],
    );

    useEffect(() => {
        if (!portalRef) return;

        if (portalStyles.className) {
            portalRef.className = portalStyles.className;
        }

        if (portalStyles.style) {
            for (const [key, value] of Object.entries(portalStyles.style)) {
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                portalRef.style[key as any] = value;
            }
        }
    }, [portalStyles, portalRef]);

    return (
        <UNSAFE_PortalProvider getContainer={() => portalRef}>
            <BaltoContext.Provider value={contextValue}>
                <BaltoThemeProviderContext
                    theme={theme}
                    colorScheme={colorScheme}
                >
                    <Component ref={ref} {...mergedStyles} {...rest}>
                        <Slottable>{children}</Slottable>
                        <Toaster />
                        <div
                            {...stylex.props(providerStyles.portalContainer)}
                            ref={rootPortalRef}
                        />
                    </Component>
                </BaltoThemeProviderContext>
            </BaltoContext.Provider>
        </UNSAFE_PortalProvider>
    );
});

const PassThrough = forwardRef(function PassThrough(
    props: BaltoProviderProps,
    ref: ForwardedRef<HTMLDivElement>,
) {
    const {
        locale: _locale,
        timeZone: _timeZone,
        disableIsolation: _disableIsolation,
        addBaseColors: _addBaseColors,
        colorScheme: _colorScheme,
        asChild,
        theme: _theme,
        ...otherProps
    } = props;
    const Component = asChild ? Slot : 'div';

    useEffect(() => {
        devWarning(
            "You nested BaltoProviders! This isn't supported and likely isn't needed.",
        );
    }, []);

    return <Component {...otherProps} ref={ref} />;
});

const BaltoProvider = forwardRef(function BaltoProvider(
    { asChild, ...props }: BaltoProviderProps,
    ref: ForwardedRef<HTMLDivElement>,
) {
    const parentContext = useContext(BaltoContext);

    if (parentContext !== defaultContextValue) {
        return <PassThrough {...props} ref={ref} />;
    }

    return (
        <BaltoContext.Provider value={defaultContextValue}>
            <AppWrapper {...props} asChild={asChild} ref={ref} />
        </BaltoContext.Provider>
    );
});

interface BaltoThemeProviderProps
    extends Omit<ThemeProviderProps, 'colorScheme'> {
    /**
     * The color scheme of the theme provider.
     */
    colorScheme?: BaltoColorScheme | undefined;
}
const getBaltoClassNames = (
    className: string | undefined,
    addBaseColors: boolean,
    colorScheme: BaltoColorScheme,
) => {
    return clsx(
        className,
        'baltoBaseDimension',
        addBaseColors && 'baltoBaseColor',
        // for compatibility with existing css
        colorScheme === 'dark' ? 'darkMode' : 'lightMode',
    );
};

interface BaltoThemeProviderProps {
    /**
     * The children of the theme provider.
     */
    children: React.ReactNode;
    /**
     * The color scheme of the theme provider.
     */
    colorScheme?: BaltoColorScheme | undefined;
    /**
     * The themes to apply. This also inherits the parent themes.
     * If no prop is provided the parent themes are just applied
     */
    theme?: ThemeProp | undefined;
}

/**
 * This component will apply a theme to it's child.
 * It only accepts one child to apply the theming classes to.
 */
const BaltoThemeProvider = forwardRef<HTMLDivElement, BaltoThemeProviderProps>(
    function BaltoThemeProvider(
        {
            theme: themeProp,
            colorScheme: colorSchemeProp,
            className,
            style,
            addBaseColors = false,
            ...props
        },
        ref,
    ) {
        const parentOverride = useBaltoThemeProvider(
            'BaltoThemeProviderComponent',
        );
        const theme = [...(parentOverride?.theme || []), ...(themeProp || [])];
        const colorScheme = colorSchemeProp ?? parentOverride?.colorScheme;
        const baseTheme = useBaseTheme({
            colorScheme,
            includeBaseThemes: false,
        });
        const mergedStyles = useMergedStyles(
            getBaltoClassNames(
                className,
                addBaseColors,
                colorScheme ?? 'light',
            ),
            style,
            stylex.props(baseTheme, theme),
        );
        return (
            <BaltoThemeProviderContext theme={theme} colorScheme={colorScheme}>
                <Slot {...mergedStyles} {...props} ref={ref} />
            </BaltoThemeProviderContext>
        );
    },
);

export type { BaltoProviderProps };
export { BaltoProvider, BaltoThemeProvider };
