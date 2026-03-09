import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef } from 'react';

import { useTypeRamp } from '../internal/hooks/useTypeRamp';
import type { SlottedContainerProps } from '../util/SlottedContainer';
import { SlottedContainer } from '../util/SlottedContainer';

interface CountBadgeProps<T extends keyof ReactHTML = 'div'>
    extends SlottedContainerProps<T> {
    /**
     * The number to display in the badge.
     */
    count?: number | undefined;
    /**
     * The max value to display in the badge before it is truncated.
     * @default 99
     */
    maxValue?: number | undefined;
}

const styles = stylex.create({
    count: {
        alignItems: 'center',
        backgroundColor: baltoTheme.statusInfoBackground,
        borderRadius: tokens['radius-xl'] /* 16 */,
        color: baltoTheme.statusInfoText,
        display: 'inline-flex',
        maxWidth: 'fit-content', // When placed inside a vertical flexbox, this prevents the countbadge from expanding to full width.
        padding: `0 ${tokens['space-horizontal-sm']}` /* 0 8 */,
    },
});

const CountBadge = forwardRef<HTMLDivElement, CountBadgeProps>(
    (props, forwardedRef) => {
        const { count = 0, children, maxValue = 99, ...otherProps } = props;
        const textStyles = useTypeRamp('smallParagraphBold');
        return (
            <SlottedContainer
                {...otherProps}
                tag="span"
                ref={forwardedRef}
                stylexProps={stylex.props(textStyles, styles.count)}
            >
                {otherProps.asChild
                    ? children
                    : count > maxValue
                      ? `${maxValue}+`
                      : count}
            </SlottedContainer>
        );
    },
);

CountBadge.displayName = 'CountBadge';
export type { CountBadgeProps };
export { CountBadge };
