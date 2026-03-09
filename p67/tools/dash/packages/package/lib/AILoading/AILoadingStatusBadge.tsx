import { Slottable } from '@radix-ui/react-slot';
import { InfoCircleSmallIcon } from '@snowflake/stellar-icons/InfoCircleSmallIcon';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef, useContext } from 'react';

import { useBaltoContext, useMergedStyles } from '../hooks';
import { useTypeRamp } from '../internal/hooks/useTypeRamp';
import { PopoverTriggerContext } from '../Popover/PopoverContext';
import type { StatusContainerProps } from '../Status/internal/StatusContainer';
import { StatusContainer } from '../Status/internal/StatusContainer';
import { TooltipContext } from '../Tooltip/TooltipContext';

interface AILoadingStatusBadgeProps<T extends keyof ReactHTML = 'span'>
    extends Omit<StatusContainerProps<T>, 'tag' | 'variant'> {
    /**
     * The label of the status badge.
     */
    label?: string | undefined;
}

const shimmer = stylex.keyframes({
    from: {
        transform: 'translateX(-100%)',
    },
    to: {
        transform: 'translateX(100%)',
    },
});

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
    aiLoadingShimmer: {
        overflow: 'hidden',
        position: 'relative',

        '::after': {
            animationDuration: '3s',
            animationIterationCount: 'infinite',
            animationName: shimmer,
            content: "''",
            inset: 0,
            pointerEvents: 'none',
            position: 'absolute',
        },
    },
    // TODO(APPS-54934): Need Figma token for these.
    aiLoadingShimmerDark: {
        '::after': {
            backgroundImage:
                'linear-gradient(90deg, rgba(255, 255, 255, 0) 0%, rgba(255, 255, 255, 0.06) 50%, rgba(255, 255, 255, 0) 100%)',
        },
    },
    aiLoadingShimmerLight: {
        '::after': {
            backgroundImage:
                'linear-gradient(90deg, rgba(0, 44, 110, 0) 0%, rgba(0, 44, 110, 0.10) 50%, rgba(0, 44, 110, 0) 100%)',
        },
    },
});

const AILoadingStatusBadge = forwardRef<
    HTMLDivElement,
    AILoadingStatusBadgeProps
>((props, forwardedRef) => {
    const { label, children, className, style, ...otherProps } = props;
    const { colorScheme } = useBaltoContext();
    const isTooltipTrigger = useContext(TooltipContext);
    const isPopoverTrigger = useContext(PopoverTriggerContext);
    const isTrigger = isTooltipTrigger || isPopoverTrigger;

    const textStyles = useTypeRamp('smallParagraphBold');
    const styleProps = useMergedStyles(
        className,
        style,
        stylex.props(
            textStyles,
            styles.base,
            styles.aiLoadingShimmer,
            colorScheme === 'light' && styles.aiLoadingShimmerLight,
            colorScheme === 'dark' && styles.aiLoadingShimmerDark,
        ),
    );

    return (
        <StatusContainer
            variant="info"
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
});

AILoadingStatusBadge.displayName = 'AILoadingStatusBadge';
export type { AILoadingStatusBadgeProps };
export { AILoadingStatusBadge };
