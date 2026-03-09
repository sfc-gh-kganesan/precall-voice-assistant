import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { IconContextProvider } from '@snowflake/stellar-icons';
import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef, useContext } from 'react';
import { useTypeRamp } from '../internal/hooks/useTypeRamp';
import type { Size } from '../types';
import { SizeContext } from '../util/context';
import type { SlottedContainerProps } from '../util/SlottedContainer';
import { SlottedContainer } from '../util/SlottedContainer';
import type { TextVariant } from './types';

interface PreProps<T extends keyof ReactHTML = 'pre'>
    extends SlottedContainerProps<T> {
    /**
     * The variant of the pre.
     */
    variant?: TextVariant | undefined;
    /**
     * Whether the pre is bold.
     * @default false
     */
    bold?: boolean | undefined;
    /**
     * The size of the pre.
     * @default "regular"
     */
    size?: Extract<Size, 'small' | 'regular'> | undefined;
    /**
     * Whether the pre is in all caps.
     * @default false
     */
    caps?: boolean | undefined;
}

const styles = stylex.create({
    primary: {
        color: baltoTheme.reusableTextPrimary,
    },
    secondary: {
        color: baltoTheme.reusableTextSecondary,
    },
    pre: {
        fontFamily: baltoTheme.fontFamilyMono,
        margin: 0,
        padding: 0,
        whiteSpace: 'pre',
    },
    error: {
        color: baltoTheme.statusCriticalMessageText,
    },
});

const Pre = forwardRef<HTMLPreElement, PreProps>((props, forwardedRef) => {
    const contextSize = useContext(SizeContext);
    const {
        bold,
        size = contextSize ?? 'regular',
        variant,
        caps,
        ...otherProps
    } = props;
    const textStyles = useTypeRamp(
        size === 'small'
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
    return (
        <IconContextProvider>
            <SlottedContainer
                {...otherProps}
                tag={'pre'}
                stylexProps={stylex.props(
                    textStyles,
                    styles.pre,
                    variant === 'primary' && styles.primary,
                    variant === 'secondary' && styles.secondary,
                    variant === 'critical' && styles.error,
                )}
                ref={forwardedRef}
            />
        </IconContextProvider>
    );
});

Pre.displayName = 'Pre';
export type { PreProps };
export { Pre };
