import { Slottable } from '@radix-ui/react-slot';
import { InfoCircleSmallIcon } from '@snowflake/stellar-icons/InfoCircleSmallIcon';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef, useContext } from 'react';

import { useMergedStyles } from '../hooks';
import { useTypeRamp } from '../internal/hooks/useTypeRamp';
import { PopoverTriggerContext } from '../Popover/PopoverContext';
import { TooltipContext } from '../Tooltip/TooltipContext';
import type { StatusContainerProps } from './internal/StatusContainer';
import { StatusContainer } from './internal/StatusContainer';
import type { StatusVariant } from './types';

interface StatusBadgeProps<T extends keyof ReactHTML = 'span'>
    extends Omit<StatusContainerProps<T>, 'tag' | 'variant'> {
    /**
     * The variant of the status badge.
     * @default "neutral"
     */
    variant?: StatusVariant | undefined;
    /**
     * The label of the status badge.
     */
    label?: string | undefined;
}

const styles = stylex.create({
    base: {
        alignItems: 'center',
        borderRadius: tokens['radius-xs'] /* 4 */,
        borderWidth: 0,
        display: 'inline-flex',
        gap: tokens['space-gap-3xs'] /* 4 */,
        maxHeight: 'fit-content', // When placed inside a horizontal flexbox, this prevents the badge from expanding to full height.
        maxWidth: 'fit-content', // When placed inside a vertical flexbox, this prevents the badge from expanding to full width.
        padding: `${tokens['space-vertical-3xs']} ${tokens['space-horizontal-xs']}` /* 2 6 */,
    },
});

const StatusBadge = forwardRef<HTMLDivElement, StatusBadgeProps>(
    (props, forwardedRef) => {
        const {
            label,
            variant = 'neutral',
            children,
            className,
            style,
            ...otherProps
        } = props;
        const isTooltipTrigger = useContext(TooltipContext);
        const isPopoverTrigger = useContext(PopoverTriggerContext);
        const isTrigger = isTooltipTrigger || isPopoverTrigger;

        const textStyles = useTypeRamp('smallParagraphBold');
        const styleProps = useMergedStyles(
            className,
            style,
            stylex.props(textStyles, styles.base),
        );

        return (
            <StatusContainer
                variant={variant}
                {...otherProps}
                tag={isTrigger ? 'button' : 'span'}
                ref={forwardedRef}
                {...styleProps}
            >
                {label}
                <Slottable>{children}</Slottable>
                {isTrigger && <InfoCircleSmallIcon />}
            </StatusContainer>
        );
    },
);

StatusBadge.displayName = 'StatusBadge';
export type { StatusBadgeProps };
export { StatusBadge };
