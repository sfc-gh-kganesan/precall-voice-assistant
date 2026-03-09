import { createContext as createStrictContext } from '@radix-ui/react-context';
import {
    type BaseColorTypes,
    type BaseDimensionToken,
    baseColorStyles,
    baseDimensionNumberStyles,
    type ThemeDarkTypes,
    type ThemeLightTypes,
    themeLightStyles,
} from '@snowflake/balto-tokens';
import type {
    CompiledStyles,
    InlineStyles,
    StyleXArray,
} from '@stylexjs/stylex';
import { createContext, useContext } from 'react';

import type { Locale, TimeZone } from '../types';

type BaltoColorScheme = 'light' | 'dark';

type ThemeProp = ReadonlyArray<
    StyleXArray<
        | (null | undefined | CompiledStyles)
        | boolean
        | Readonly<[CompiledStyles, InlineStyles]>
    >
>;

interface BaltoThemeProviderContextValue {
    colorScheme?: BaltoColorScheme;
    theme?: ThemeProp;
}

const [BaltoThemeProviderContext, useBaltoThemeProvider] =
    createStrictContext<BaltoThemeProviderContextValue | null>(
        'BaltoThemeProvider',
        null,
    );

interface BaltoContextValue {
    colorScheme: BaltoColorScheme;
    locale: Locale;
    timeZone: TimeZone;
    styleValues: Readonly<ThemeLightTypes | ThemeDarkTypes>;
    colorValues: Readonly<BaseColorTypes>;
    dimensionValues: Readonly<Record<BaseDimensionToken, number>>;
    portalContainer: HTMLElement | null;
}

const defaultContextValue: BaltoContextValue = {
    colorScheme: 'light',
    locale: 'en-US',
    timeZone: 'America/Los_Angeles',
    styleValues: themeLightStyles,
    colorValues: baseColorStyles,
    dimensionValues: baseDimensionNumberStyles,
    portalContainer: null,
};

const BaltoContext = createContext<BaltoContextValue>(defaultContextValue);
BaltoContext.displayName = 'BaltoContext';

function useBaltoContext() {
    const value = useContext(BaltoContext);
    const { colorScheme = 'light' } =
        useBaltoThemeProvider('useBaltoContext') || {};

    if (!value) {
        console.error(
            'No value found for Balto context, Please make sure Context is initialized correctly.',
        );
        return defaultContextValue;
    }
    return {
        ...value,
        colorScheme,
    };
}

export {
    defaultContextValue,
    useBaltoContext,
    BaltoContext,
    BaltoThemeProviderContext,
    useBaltoThemeProvider,
};

export type {
    BaltoColorScheme as BaltoTheme,
    BaltoContextValue,
    BaltoColorScheme,
    ThemeProp,
};
