import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { baseColor } from '@snowflake/balto-themes/baseColor.stylex.js';
import { buttonTheme } from '@snowflake/balto-themes/buttonTheme.stylex.js';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import { createContext, useContext } from 'react';
import { useTypeRamp } from '../internal/hooks/useTypeRamp';
import { SizeContext } from '../util/context';
import type { ButtonProps } from './types';

const styles = stylex.create({
    button: {
        alignItems: 'center',
        appearance: 'none',
        backgroundColor: baseColor.transparent,
        borderRadius: buttonTheme.borderRadiusDefault,
        cursor: 'pointer',
        display: 'inline-flex',
        gap: tokens['space-gap-sm'] /* 8 */,
        height: tokens['size-md'] /* 32 */,
        justifyContent: 'center',
        margin: 0,
        maxWidth: 'fit-content', // When placed inside a vertical flexbox, this prevents the button from expanding to full width.
        outlineColor: {
            ':is([data-focus-visible])':
                baltoTheme.reusableBorderFocusedActiveItem,
        },
        outlineStyle: { ':is([data-focus-visible])': 'solid' },
        outlineWidth: {
            default: '0px',
            ':is([data-focus-visible])': '2px',
        },
        padding: `0 ${tokens['space-horizontal-md']}` /* 8 12 */,
        position: 'relative',
        // If we asChild something like our own Link component
        // (although we still don't recommend doing that)
        textDecoration: 'none !important',
        touchAction: 'manipulation',
        userSelect: 'none',
        whiteSpace: 'nowrap',
    },
    buttonSmall: {
        gap: tokens['space-gap-2xs'] /* 4 */,
        height: tokens['size-sm'] /* 24 */,
        padding: `${tokens['space-vertical-2xs']} ${tokens['space-horizontal-md']}` /* 4 12 */,
    },
    buttonFullWidth: {
        display: 'flex',
        maxWidth: 'none',
        width: '100%',
    },
    buttonDisabled: {
        borderWidth: 0,
        cursor: 'not-allowed',
        outline: { ':is([data-focus-visible])': 'none' },
    },
    iconOnly: {
        height: tokens['size-md'] /* 32 */,
        padding: tokens['space-vertical-sm'] /* 8 8 */,
        width: tokens['size-md'] /* 32 */,
    },
    iconOnlySmall: {
        height: tokens['size-sm'] /* 24 */,
        minWidth: tokens['size-sm'] /* 24 */,
        padding: tokens['space-vertical-2xs'] /* 4 4 */,
        width: tokens['size-sm'] /* 24 */,
    },
    primary: {
        backgroundColor: {
            default: buttonTheme.primaryBackgroundDefault,
            ':is([data-state="open"],[aria-expanded="true"])':
                buttonTheme.primaryBackgroundPress,
            ':hover': buttonTheme.primaryBackgroundHover,
            ':active': buttonTheme.primaryBackgroundPress,
        },
        borderColor: {
            default: buttonTheme.primaryBorderDefault,
            ':is([data-state="open"],[aria-expanded="true"])':
                buttonTheme.primaryBorderPress,
            ':hover': buttonTheme.primaryBorderHover,
            ':active': buttonTheme.primaryBorderPress,
        },
        borderStyle: 'solid',
        borderWidth: buttonTheme.primaryBorderWidthDefault,
        boxShadow: {
            '::before': buttonTheme.primaryShadowDefault,
        },
        color: {
            default: buttonTheme.primaryTextDefault,
            ':is([data-state="open"],[aria-expanded="true"])':
                buttonTheme.primaryTextPress,
            ':hover': buttonTheme.primaryTextHover,
            ':active': buttonTheme.primaryTextPress,
        },
    },
    primaryDisabled: {
        backgroundColor: buttonTheme.primaryBackgroundDisabled,
        color: buttonTheme.primaryTextDisabled,
    },
    primarySelected: {
        backgroundColor: buttonTheme.primaryBackgroundPress,
        color: buttonTheme.primaryTextPress,
    },
    primaryCritical: {
        backgroundColor: {
            default: buttonTheme.primaryCriticalBackgroundDefault,
            ':is([data-state="open"],[aria-expanded="true"])':
                buttonTheme.primaryCriticalBackgroundPress,
            ':hover': buttonTheme.primaryCriticalBackgroundHover,
            ':active': buttonTheme.primaryCriticalBackgroundPress,
        },
        borderColor: {
            default: buttonTheme.primaryCriticalBorderDefault,
            ':is([data-state="open"],[aria-expanded="true"])':
                buttonTheme.primaryCriticalBorderPress,
            ':hover': buttonTheme.primaryCriticalBorderHover,
            ':active': buttonTheme.primaryCriticalBorderPress,
        },
        borderStyle: 'solid',
        borderWidth: buttonTheme.primaryCriticalBorderWidthDefault,
        boxShadow: {
            '::before': buttonTheme.primaryCriticalShadowDefault,
        },
        color: {
            default: buttonTheme.primaryCriticalTextDefault,
        },
    },
    primaryCriticalDisabled: {
        backgroundColor: buttonTheme.primaryCriticalBackgroundDisabled,
        color: buttonTheme.primaryCriticalTextDisabled,
    },
    primaryCriticalSelected: {
        backgroundColor: buttonTheme.primaryCriticalBackgroundPress,
        color: buttonTheme.primaryCriticalTextPress,
    },
    secondary: {
        backgroundColor: {
            default: buttonTheme.secondaryBackgroundDefault,
            ':is([data-state="open"],[aria-expanded="true"])':
                buttonTheme.secondaryBackgroundPress,
            ':hover': buttonTheme.secondaryBackgroundHover,
            ':active': buttonTheme.secondaryBackgroundPress,
        },
        borderColor: {
            default: buttonTheme.secondaryBorderDefault,
            ':is([data-state="open"],[aria-expanded="true"])':
                buttonTheme.secondaryBorderPress,
            ':hover': buttonTheme.secondaryBorderHover,
            ':active': buttonTheme.secondaryBorderPress,
        },
        borderStyle: 'solid',
        borderWidth: buttonTheme.secondaryBorderWidthDefault,
        boxShadow: {
            '::before': buttonTheme.secondaryShadowDefault,
        },
        color: {
            default: buttonTheme.secondaryTextDefault,
            ':is([data-state="open"],[aria-expanded="true"])':
                buttonTheme.secondaryTextPress,
            ':hover': buttonTheme.secondaryTextHover,
            ':active': buttonTheme.secondaryTextPress,
        },
    },
    secondaryDisabled: {
        backgroundColor: buttonTheme.secondaryBackgroundDisabled,
        borderColor: buttonTheme.secondaryBorderDisabled,
        color: buttonTheme.secondaryTextDisabled,
    },
    secondarySelected: {
        backgroundColor: buttonTheme.secondaryBackgroundPress,
        color: buttonTheme.secondaryTextPress,
    },
    tertiary: {
        backgroundColor: {
            default: buttonTheme.tertiaryBackgroundDefault,
            ':is([data-state="open"],[aria-expanded="true"])':
                buttonTheme.tertiaryBackgroundPress,
            ':hover': buttonTheme.tertiaryBackgroundHover,
            ':active': buttonTheme.tertiaryBackgroundPress,
        },
        borderColor: {
            default: buttonTheme.tertiaryBorderDefault,
            ':is([data-state="open"],[aria-expanded="true"])':
                buttonTheme.tertiaryBorderPress,
            ':hover': buttonTheme.tertiaryBorderHover,
            ':active': buttonTheme.tertiaryBorderPress,
        },
        borderStyle: 'solid',
        borderWidth: buttonTheme.tertiaryBorderWidthDefault,
        boxShadow: {
            '::before': buttonTheme.tertiaryShadowDefault,
        },
        color: {
            default: buttonTheme.tertiaryTextDefault,
            ':is([data-state="open"],[aria-expanded="true"])':
                buttonTheme.tertiaryTextPress,
            ':hover': buttonTheme.tertiaryTextHover,
            ':active': buttonTheme.tertiaryTextPress,
        },
    },
    tertiaryDisabled: {
        backgroundColor: baseColor.transparent,
        color: buttonTheme.tertiaryTextDisabled,
    },
    tertiarySelected: {
        backgroundColor: buttonTheme.tertiaryBackgroundPress,
        color: buttonTheme.tertiaryTextPress,
    },
    hoverShadow: {
        opacity: {
            ':hover:not(:active)::before': '1 !important',
            '::before': 0,
        },
        '::before': {
            borderRadius: 'inherit',
            content: "''",
            inset: 0,
            position: 'absolute',
        },
    },
});

export const IsIconOnlyContext = createContext<boolean>(false);

export const useButtonStyles = (props: ButtonProps) => {
    const contextSize = useContext(SizeContext);
    const {
        variant = 'primary',
        size = contextSize ?? 'regular',
        fullWidth,
        children,
        isLoading,
        ...otherProps
    } = props;
    const disabled = otherProps.disabled;
    const selected = otherProps.selected;
    const isIconOnly = useContext(IsIconOnlyContext) || children === undefined;

    const textStyles = useTypeRamp(size === 'regular' ? 'label' : 'labelSmall');
    const disabledStyling = disabled || isLoading;
    const selectedStyling = selected && !disabledStyling;

    return [
        styles.button,
        textStyles, // TODO: This has to be after styles.button, otherwise textsize small CSS class gets dropped, why?
        size === 'small' && styles.buttonSmall,
        fullWidth && styles.buttonFullWidth,
        disabledStyling && styles.buttonDisabled,
        isIconOnly && size === 'regular' && styles.iconOnly,
        isIconOnly && size === 'small' && styles.iconOnlySmall,
        variant === 'primary' && styles.primary,
        variant === 'primary' && disabledStyling && styles.primaryDisabled,
        variant === 'primary' && selectedStyling && styles.primarySelected,
        variant === 'primary-critical' && styles.primaryCritical,
        variant === 'primary-critical' &&
            disabledStyling &&
            styles.primaryCriticalDisabled,
        variant === 'primary-critical' &&
            selectedStyling &&
            styles.primaryCriticalSelected,
        variant === 'secondary' && styles.secondary,
        variant === 'secondary' && disabledStyling && styles.secondaryDisabled,
        variant === 'secondary' && selectedStyling && styles.secondarySelected,
        variant === 'tertiary' && styles.tertiary,
        variant === 'tertiary' && disabledStyling && styles.tertiaryDisabled,
        variant === 'tertiary' && selectedStyling && styles.tertiarySelected,
        styles.hoverShadow,
    ];
};
