import { aiLoadingDark } from '@snowflake/balto-themes/aiLoadingDark.stylex.js';
import { aiLoadingLight } from '@snowflake/balto-themes/aiLoadingLight.stylex.js';
import { appNavigationDark } from '@snowflake/balto-themes/appNavigationDark.stylex.js';
import { appNavigationLight } from '@snowflake/balto-themes/appNavigationLight.stylex.js';
import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { buttonDark } from '@snowflake/balto-themes/buttonDark.stylex.js';
import { buttonLight } from '@snowflake/balto-themes/buttonLight.stylex.js';
import { fieldDark } from '@snowflake/balto-themes/fieldDark.stylex.js';
import { fieldLight } from '@snowflake/balto-themes/fieldLight.stylex.js';
import { progressBarDark } from '@snowflake/balto-themes/progressBarDark.stylex.js';
import { progressBarLight } from '@snowflake/balto-themes/progressBarLight.stylex.js';
import { segmentedButtonDark } from '@snowflake/balto-themes/segmentedButtonDark.stylex.js';
import { segmentedButtonLight } from '@snowflake/balto-themes/segmentedButtonLight.stylex.js';
import { skeletonDark } from '@snowflake/balto-themes/skeletonDark.stylex.js';
import { skeletonLight } from '@snowflake/balto-themes/skeletonLight.stylex.js';
import { themeDark } from '@snowflake/balto-themes/themeDark.stylex.js';
import { themeLight } from '@snowflake/balto-themes/themeLight.stylex.js';
import { toolbarDark } from '@snowflake/balto-themes/toolbarDark.stylex.js';
import { toolbarLight } from '@snowflake/balto-themes/toolbarLight.stylex.js';
import type {
    CompiledStyles,
    InlineStyles,
    StyleXArray,
} from '@stylexjs/stylex';
import * as stylex from '@stylexjs/stylex';

import type { BaltoColorScheme } from '../hooks';
import { getTypeRamp } from '../internal/hooks/useTypeRamp';

const providerStyles = stylex.create({
    base: {
        color: baltoTheme.reusableTextPrimary,

        MozOsxFontSmoothing: 'grayscale',
        WebkitFontSmoothing: 'antialiased',
        boxSizing: 'border-box',
        fontSynthesis: 'none',
        textRendering: 'optimizeLegibility',
    },
    overrideLineHeight: {
        // we never set the default line height, this is what the page was using.
        // should revisit and use a line height from the design system.
        lineHeight: 'inherit',
    },
    darkMode: {
        colorScheme: 'dark',
    },
    lightMode: {
        colorScheme: 'light',
    },
});
type StyleXInput = ReadonlyArray<
    StyleXArray<
        | (null | undefined | CompiledStyles)
        | boolean
        | Readonly<[CompiledStyles, InlineStyles]>
        | typeof themeLight
        | typeof progressBarLight
        | typeof buttonLight
        | typeof segmentedButtonLight
        | typeof skeletonLight
        | typeof appNavigationLight
        | typeof fieldLight
    >
>;
/**
 * Returns the themes for a given color scheme.
 * @param colorScheme - The color scheme to get the themes for.
 * @returns The themes for the given color scheme.
 */
export function getThemesForColorScheme(
    colorScheme: BaltoColorScheme,
    { includeBaseThemes = false }: { includeBaseThemes?: boolean } = {},
): StyleXInput {
    return [
        colorScheme === 'dark' ? aiLoadingDark : aiLoadingLight,
        colorScheme === 'dark' ? themeDark : themeLight,
        colorScheme === 'dark' ? progressBarDark : progressBarLight,
        colorScheme === 'dark' ? buttonDark : buttonLight,
        colorScheme === 'dark'
            ? providerStyles.darkMode
            : providerStyles.lightMode,
        colorScheme === 'dark' ? segmentedButtonDark : segmentedButtonLight,
        colorScheme === 'dark' ? skeletonDark : skeletonLight,
        colorScheme === 'dark' ? appNavigationDark : appNavigationLight,
        colorScheme === 'dark' ? fieldDark : fieldLight,
        colorScheme === 'dark' ? toolbarDark : toolbarLight,
        includeBaseThemes && providerStyles.base,
        includeBaseThemes && getTypeRamp('paragraph'),
        includeBaseThemes && providerStyles.overrideLineHeight,
    ];
}
