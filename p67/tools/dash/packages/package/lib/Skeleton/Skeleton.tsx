import { skeletonTheme } from '@snowflake/balto-themes/skeletonTheme.stylex.js';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import { forwardRef } from 'react';

import { useBaltoContext, useMergedStyles } from '../hooks';
import type { Radius } from '../types';

const shimmerAnimation = stylex.keyframes({
    '0%': {
        transform: 'translateX(-75%)',
    },
    '100%': {
        transform: 'translateX(25%)',
    },
});

const styles = stylex.create({
    root: {
        height: tokens['size-2xs'],
        overflow: 'hidden',
        width: '100%',

        // TOOD(APPS-55669)

        '--shimmer-end-color': skeletonTheme.shimmerEndDefault,
        '--shimmer-start-color': skeletonTheme.shimmerStartDefault,

        backgroundColor: 'var(--shimmer-start-color)',
    },
    inner: {
        animationDuration: '1.5s',
        animationIterationCount: 'infinite',
        animationName: shimmerAnimation,
        backgroundImage:
            'linear-gradient(135deg, var(--shimmer-start-color) 0%, var(--shimmer-start-color) 40%, var(--shimmer-end-color) 50%, var(--shimmer-start-color) 60%, var(--shimmer-start-color) 100%)',
        backgroundRepeat: 'repeat',
        height: '100%',
        width: '200%',
    },
    innerDark: {
        opacity: 0.4, // TOOD(APPS-54934): Use Figma token once available from UX.
    },
    circle: {
        borderRadius: '100%',
    },
    circleInner: {
        width: '700%',
    },
    radiusXsmall: {
        borderRadius: tokens['radius-xs'],
    },
    radiusSmall: {
        borderRadius: tokens['radius-sm'],
    },
    radiusMedium: {
        borderRadius: tokens['radius-md'],
    },
    radiusLarge: {
        borderRadius: tokens['radius-xl'],
    },
});

interface SkeletonRectangleProps
    extends Omit<React.HTMLAttributes<HTMLDivElement>, 'children'> {
    /**
     * The height of the skeleton rectangle.
     */
    height?: React.CSSProperties['height'] | undefined;
    /**
     * The width of the skeleton rectangle.
     */
    width?: React.CSSProperties['width'] | undefined;
    /** The border radius of the skeleton rectangle */
    radius?: Radius | undefined;
}

const SkeletonRectangle = forwardRef<HTMLDivElement, SkeletonRectangleProps>(
    ({ height, width, className, style, radius = 'large', ...props }, ref) => {
        const { colorScheme } = useBaltoContext();
        const mergedStyles = useMergedStyles(
            className,
            {
                ...style,
                height,
                width,
            } as React.CSSProperties,
            stylex.props(
                styles.root,
                radius === 'xsmall' && styles.radiusXsmall,
                radius === 'small' && styles.radiusSmall,
                radius === 'medium' && styles.radiusMedium,
                radius === 'large' && styles.radiusLarge,
            ),
        );

        return (
            <div {...props} {...mergedStyles} ref={ref}>
                <div
                    {...stylex.props(
                        styles.inner,
                        colorScheme === 'dark' && styles.innerDark,
                    )}
                />
            </div>
        );
    },
);

SkeletonRectangle.displayName = 'SkeletonRectangle';

interface SkeletonCircleProps
    extends Omit<React.HTMLAttributes<HTMLDivElement>, 'children'> {
    /**
     * The size of the skeleton circle.
     */
    size?: React.CSSProperties['width'] | undefined;
}

const SkeletonCircle = forwardRef<HTMLDivElement, SkeletonCircleProps>(
    function SkeletonCircle({ size = 16, className, style, ...props }, ref) {
        const { colorScheme } = useBaltoContext();
        const mergedStyles = useMergedStyles(
            className,
            {
                ...style,
                height: size,
                width: size,
            } as React.CSSProperties,
            stylex.props(styles.root, styles.circle),
        );

        return (
            <div aria-hidden {...props} {...mergedStyles} ref={ref}>
                <div
                    {...stylex.props(
                        styles.inner,
                        colorScheme === 'dark' && styles.innerDark,
                        styles.circleInner,
                    )}
                />
            </div>
        );
    },
);

SkeletonCircle.displayName = 'SkeletonCircle';

export type { SkeletonCircleProps, SkeletonRectangleProps };
export { SkeletonCircle, SkeletonRectangle };
