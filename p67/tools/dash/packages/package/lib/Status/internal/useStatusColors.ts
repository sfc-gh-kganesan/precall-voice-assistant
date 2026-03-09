import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import type {
    CompiledStyles,
    InlineStyles,
    StyleXArray,
} from '@stylexjs/stylex';
import * as stylex from '@stylexjs/stylex';

import type { StatusVariant } from '../types';

const styles = stylex.create({
    statusNeutral: {
        color: baltoTheme.statusNeutralText,
    },
    statusNeutralBackground: {
        backgroundColor: baltoTheme.statusNeutralBackground,
    },
    statusNeutralLink: {
        color: {
            default: baltoTheme.reusableLinkNeutralDefault,
            ':hover': baltoTheme.reusableLinkNeutralHover,
            ':active': baltoTheme.reusableLinkNeutralPress,
        },
    },
    statusNeutralLinkDisabled: {
        color: { default: baltoTheme.reusableLinkNeutralDisabled },
    },
    statusActive: {
        color: baltoTheme.componentStatusPillActiveText,
    },
    statusActiveBackground: {
        backgroundColor: baltoTheme.componentStatusPillActiveBackground,
    },
    statusSuccess: {
        color: baltoTheme.statusSuccessText,
    },
    statusSuccessBackground: {
        backgroundColor: baltoTheme.statusSuccessBackground,
    },
    statusSuccessLink: {
        color: {
            default: baltoTheme.reusableLinkSuccessDefault,
            ':hover': baltoTheme.reusableLinkSuccessHover,
            ':active': baltoTheme.reusableLinkSuccessPress,
        },
    },
    statusSuccessLinkDisabled: {
        color: {
            default: baltoTheme.reusableLinkSuccessDisabled,
        },
    },
    statusInfo: {
        color: baltoTheme.statusInfoText,
    },
    statusInfoBackground: {
        backgroundColor: baltoTheme.statusInfoBackground,
    },
    statusInfoLink: {
        color: {
            default: baltoTheme.reusableLinkInfoDefault,
            ':hover': baltoTheme.reusableLinkInfoHover,
            ':active': baltoTheme.reusableLinkInfoPress,
        },
    },
    statusInfoLinkDisabled: {
        color: {
            default: baltoTheme.reusableLinkInfoDisabled,
        },
    },
    statusCaution: {
        color: baltoTheme.statusCautionText,
    },
    statusCautionBackground: {
        backgroundColor: baltoTheme.statusCautionBackground,
    },
    statusCautionLink: {
        color: {
            default: baltoTheme.reusableLinkCautionDefault,
            ':hover': baltoTheme.reusableLinkCautionHover,
            ':active': baltoTheme.reusableLinkCautionPress,
        },
    },
    statusCautionLinkDisabled: {
        color: {
            default: baltoTheme.reusableLinkCautionDisabled,
        },
    },
    statusCritical: {
        color: baltoTheme.statusCriticalText,
    },
    statusCriticalBackground: {
        backgroundColor: baltoTheme.statusCriticalBackground,
    },
    statusCriticalLink: {
        color: {
            default: baltoTheme.reusableLinkCriticalDefault,
            ':hover': baltoTheme.reusableLinkCriticalHover,
            ':active': baltoTheme.reusableLinkCriticalPress,
        },
    },
    statusCriticalLinkDisabled: {
        color: {
            default: baltoTheme.reusableLinkCriticalDisabled,
        },
    },
});

const useStatusTextColors = (
    variant: StatusVariant,
    addBackground: boolean = false,
): StyleXArray<
    | (null | undefined | CompiledStyles)
    | boolean
    | Readonly<[CompiledStyles, InlineStyles]>
> => [
    variant === 'neutral' && styles.statusNeutral,
    variant === 'neutral' && addBackground && styles.statusNeutralBackground,
    variant === 'active' && styles.statusActive,
    variant === 'active' && addBackground && styles.statusActiveBackground,
    variant === 'success' && styles.statusSuccess,
    variant === 'success' && addBackground && styles.statusSuccessBackground,
    variant === 'info' && styles.statusInfo,
    variant === 'info' && addBackground && styles.statusInfoBackground,
    variant === 'caution' && styles.statusCaution,
    variant === 'caution' && addBackground && styles.statusCautionBackground,
    variant === 'critical' && styles.statusCritical,
    variant === 'critical' && addBackground && styles.statusCriticalBackground,
];

const useStatusLinkColors = (
    variant?: StatusVariant,
    disabled?: boolean,
): StyleXArray<
    | (null | undefined | CompiledStyles)
    | boolean
    | Readonly<[CompiledStyles, InlineStyles]>
> => [
    variant === 'neutral' && styles.statusNeutralLink,
    variant === 'neutral' && disabled && styles.statusNeutralLinkDisabled,

    variant === 'success' && styles.statusSuccessLink,
    variant === 'success' && disabled && styles.statusSuccessLinkDisabled,

    variant === 'info' && styles.statusInfoLink,
    variant === 'info' && disabled && styles.statusInfoLinkDisabled,

    variant === 'caution' && styles.statusCautionLink,
    variant === 'caution' && disabled && styles.statusCautionLinkDisabled,

    variant === 'critical' && styles.statusCriticalLink,
    variant === 'critical' && disabled && styles.statusCriticalLinkDisabled,
];

export { useStatusTextColors, useStatusLinkColors };
