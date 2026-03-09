import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef } from 'react';

import { useTypeRamp } from '../internal/hooks/useTypeRamp';
import type { Size } from '../types';
import type { SlottedContainerProps } from '../util/SlottedContainer';
import { SlottedContainer } from '../util/SlottedContainer';

interface SpanProps<T extends keyof ReactHTML = 'span'>
    extends SlottedContainerProps<T> {
    /**
     * Whether the label is bold.
     * @default false
     */
    bold?: boolean | undefined;
    /**
     * The size of the label.
     * @default "regular"
     */
    size?: Extract<Size, 'small' | 'regular'> | undefined;
    /**
     * Whether the label should be truncated.
     * @default false
     */
    truncate?: boolean | undefined;
    /**
     * The variant of the label.
     * @default "primary"
     */
    variant?: 'primary' | 'secondary' | undefined;
}

const styles = stylex.create({
    primary: {
        color: baltoTheme.reusableTextPrimary,
    },
    secondary: {
        color: baltoTheme.reusableTextSecondary,
    },
    truncate: {
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
    },
});

const FilterLabel = forwardRef<HTMLSpanElement, SpanProps>(
    (props, forwardedRef) => {
        const { children, truncate, variant, size, bold, ...otherProps } =
            props;
        const labelTextStyles = useTypeRamp(
            size === 'regular'
                ? bold
                    ? 'boldSingleLine'
                    : 'regularSingleLine'
                : bold
                  ? 'smallSingleLineBold'
                  : 'smallSingleLine',
        );

        return (
            <SlottedContainer
                {...otherProps}
                tag={'span'}
                stylexProps={stylex.props(
                    labelTextStyles,
                    variant === 'primary' && styles.primary,
                    variant === 'secondary' && styles.secondary,
                    truncate && styles.truncate,
                )}
                ref={forwardedRef}
            >
                {children}
            </SlottedContainer>
        );
    },
);

FilterLabel.displayName = 'FilterLabel';
export type { SpanProps };
export { FilterLabel };
