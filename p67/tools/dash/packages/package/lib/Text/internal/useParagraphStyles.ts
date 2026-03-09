import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import type {
    CompiledStyles,
    InlineStyles,
    StyleXArray,
} from '@stylexjs/stylex';
import * as stylex from '@stylexjs/stylex';
import { useMemo } from 'react';
import { useTypeRamp } from '../../internal/hooks/useTypeRamp';
import type { ParagraphContextValue } from './ParagraphContext';

const styles = stylex.create({
    primary: {
        color: baltoTheme.reusableTextPrimary,
    },
    secondary: {
        color: baltoTheme.reusableTextSecondary,
    },
    error: {
        color: baltoTheme.statusCriticalMessageText,
    },
    caution: {
        color: baltoTheme.statusCautionMessageText,
    },
});
const useParagraphStyles = (
    ctx: ParagraphContextValue,
): ReadonlyArray<
    StyleXArray<
        | (null | undefined | CompiledStyles)
        | boolean
        | Readonly<[CompiledStyles, InlineStyles]>
    >
> => {
    const { bold, caps, small, variant } = ctx;

    const textStyles = useTypeRamp(
        small
            ? caps
                ? 'allCapsSmall'
                : bold
                  ? 'smallParagraphBold'
                  : 'smallParagraph'
            : caps
              ? 'allCaps'
              : bold
                ? 'boldParagraph'
                : 'paragraph',
    );
    return useMemo(() => {
        return [
            textStyles,
            variant === 'primary' && styles.primary,
            variant === 'secondary' && styles.secondary,
            variant === 'critical' && styles.error,
            variant === 'caution' && styles.caution,
        ];
    }, [textStyles, variant]);
};

export { useParagraphStyles };
