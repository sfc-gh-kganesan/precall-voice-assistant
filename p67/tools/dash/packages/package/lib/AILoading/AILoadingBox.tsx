import { aiLoadingTheme } from '@snowflake/balto-themes/aiLoadingTheme.stylex.js';
import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { HTMLAttributes } from 'react';
import { forwardRef, useEffect, useRef, useState } from 'react';
import { useSharedResizeObserver } from 'use-shared-resize-observer';

import { useBaltoContext, useMergedStyles } from '../hooks';
import { Flex } from '../Layout';

interface AILoadingBoxProps extends HTMLAttributes<HTMLDivElement> {
    /**
     * Whether the loading box is loading.
     */
    isLoading?: boolean | undefined;
    /**
     * Whether the loading box should take the full width of its container.
     */
    fullBleed?: boolean | undefined;
}

// Animation durations in milliseconds.
const fadeInDuration = 300;
const fadeOutDuration = 2000;
const traceDuration = 3000;

const fadeIn = stylex.keyframes({
    from: {
        opacity: 0,
    },
    to: {
        opacity: 1,
    },
});
const fadeOut = stylex.keyframes({
    from: {
        opacity: 1,
    },
    to: {
        opacity: 0,
    },
});
const backgroundPulse1 = stylex.keyframes({
    '0%': {
        transform: 'rotate(0deg) translate3d(0, 0, 0) scale(1)',
    },
    '25%': {
        transform: 'rotate(90deg) translate3d(5%, -5%, 0) scale(1.02)',
    },
    '50%': {
        transform: 'rotate(180deg) translate3d(0, -10%, 0) scale(1.05)',
    },
    '75%': {
        transform: 'rotate(270deg) translate3d(-5%, -5%, 0) scale(1.02)',
    },
    '100%': {
        transform: 'rotate(360deg) translate3d(0, 0, 0) scale(1)',
    },
});
const backgroundPulse2 = stylex.keyframes({
    '0%': {
        transform: 'rotate(0deg) translate3d(0, 0, 0) scale(1)',
    },
    '25%': {
        transform: 'rotate(-90deg) translate3d(-5%, 5%, 0) scale(1.02)',
    },
    '50%': {
        transform: 'rotate(-180deg) translate3d(0, 10%, 0) scale(1.05)',
    },
    '75%': {
        transform: 'rotate(-270deg) translate3d(5%, 5%, 0) scale(1.02)',
    },
    '100%': {
        transform: 'rotate(-360deg) translate3d(0, 0, 0) scale(1)',
    },
});

const styles = stylex.create({
    // TODO(APPS-54934): Replace hard coded colors with themed tokens this once we have them.
    // TOOD(APPS-55669)

    colorsLight: {
        '--balto-glow-active': 'rgba(1, 116, 255, 0.12)',
        '--balto-glow-active-secondary': 'rgba(20, 165, 187, 0.12)',
        '--balto-glow-primary': 'rgba(16, 159, 212, 0.12)',
        '--balto-glow-secondary': 'rgba(13, 141, 150, 0.12)',
    },
    colorsDark: {
        '--balto-glow-active': 'rgba(1, 116, 255, 0.24)',
        '--balto-glow-active-secondary': 'rgba(20, 165, 187, 0.24)',
        '--balto-glow-primary': 'rgba(16, 159, 212, 0.24)',
        '--balto-glow-secondary': 'rgba(13, 141, 150, 0.24)',
    },

    container: {
        backgroundColor: baltoTheme.surfaceLevel_2Background,
        borderRadius: tokens['radius-sm'],
        boxShadow: `inset 0px 0px 0px 1px ${baltoTheme.surfaceLevel_2Border}`,
        display: 'inline-block', // Make container same size as children.
        position: 'relative', // For absolute positioning loading overlay within container.
    },
    contentContainer: {
        overflow: 'auto',
        padding: `${tokens['space-vertical-2xl']} ${tokens['space-horizontal-2xl']}`,
        zIndex: 1, // Make user content above the loading animation overlays.
    },
    fullBleed: {
        padding: 0,
    },
    overlayContainer: {
        borderRadius: tokens['radius-sm'],
        containerType: 'size',
        inset: 0,
        opacity: 0,
        overflow: 'hidden',
        pointerEvents: 'none',
        position: 'absolute',
        zIndex: 0,
    },
    overlayContainerVisible: {
        opacity: 1,
    },
    overlay: {
        inset: 0,
        position: 'absolute',
    },
    borderBase: {
        backgroundImage:
            'radial-gradient(circle at center, #2986E8 0%, #90E0FD 33%, #11C5CF 66%, #2986E8 100%)',
    },
    borderBaseLoading: {
        animationDuration: `${fadeInDuration}ms`,
        animationFillMode: 'forwards',
        animationName: fadeIn,
        animationTimingFunction: 'ease',
    },
    borderBaseFading: {
        animationDuration: `${fadeOutDuration}ms`,
        animationFillMode: 'forwards',
        animationName: fadeOut,
        animationTimingFunction: 'ease',
    },
    borderCover: {
        backgroundColor: baltoTheme.surfaceLevel_2Background,
        borderRadius: tokens['radius-xs'],
        transform: `scale(calc(1 - (2 * ${aiLoadingTheme.aiLoadingBoxBorderWidth} / var(--width))), calc(1 - (2 * ${aiLoadingTheme.aiLoadingBoxBorderWidth} / var(--height))))`,
        transformOrigin: 'center',
    },
    borderCoverFading: {
        transform:
            'scale(calc(1 - (2 * 1 / var(--width))), calc(1 - (2 * 1 / var(--height))))',
        transition: `transform ${fadeOutDuration}ms ease`,
    },
    borderTrace: {
        backgroundImage:
            'linear-gradient(to right, rgba(255, 255, 255, 0.3) 0%, rgba(255, 255, 255, 0.5) 50%, rgba(255, 255, 255, 0.3) 100%)',
        borderRadius: '50%',
        height: 60,
        opacity: 0,
        width: 60,
    },
    borderTraceLoading: {
        opacity: 1,
    },
    backgroundPulseBase: {
        borderRadius: '50%',
        filter: 'blur(40px)',
        opacity: 0,
        transformOrigin: 'center',
        transition: `opacity ${fadeInDuration}ms ease`,
    },
    backgroundPulse1: {
        backgroundImage:
            'radial-gradient(ellipse at center, var(--balto-glow-primary) 0%, var(--balto-glow-secondary) 50%, transparent 70%)',
        height: '320%',
        left: '-80%',
        position: 'absolute',
        top: '-120%',
        width: '320%',
    },
    backgroundPulse2: {
        backgroundImage:
            'radial-gradient(ellipse at center, var(--balto-glow-secondary) 0%, var(--balto-glow-primary) 50%, transparent 70%)',
        bottom: '-40%',
        height: '280%',
        position: 'absolute',
        right: '-20%',
        width: '240%',
    },
    backgroundPulse1Loading: {
        animationDuration: '16s',
        animationIterationCount: 'infinite',
        animationName: backgroundPulse1,
        animationTimingFunction: 'linear',
        opacity: 0.7,
    },
    backgroundPulse2Loading: {
        animationDuration: '24s',
        animationIterationCount: 'infinite',
        animationName: backgroundPulse2,
        animationTimingFunction: 'linear',
        opacity: 0.7,
    },
    backgroundPulseFading: {
        opacity: 0,
        transition: `opacity ${fadeOutDuration}ms ease`,
    },
});

// Internal states used to track the current state of the loading animation.
type LoadingState = 'none' | 'loading' | 'fading';

const AILoadingBox = forwardRef<HTMLDivElement, AILoadingBoxProps>(
    (props, forwardedRef) => {
        const { colorScheme } = useBaltoContext();

        const {
            className,
            style,
            isLoading,
            fullBleed,
            children,
            ...otherProps
        } = props;
        const overlayRef = useRef<HTMLDivElement>(null);
        const borderTraceRef = useRef<HTMLDivElement>(null);
        const borderCoverRef = useRef<HTMLDivElement>(null);

        const [loadingState, setLoadingState] = useState<LoadingState>('none');
        const [borderTraceAnimation, setBorderTraceAnimation] =
            useState<Animation | null>(null);

        // Updates the internal loading state based on the `isLoading` prop changes.
        useEffect(() => {
            let fadingTimeoutId: ReturnType<typeof setTimeout> | undefined;
            if (isLoading === true) {
                setLoadingState('loading');
                borderTraceAnimation?.play();
            } else {
                if (loadingState === 'loading') {
                    setTimeout(() => setLoadingState('fading'), 50); // Wait for resize observer to update the container size in case it changes when isLoading becomes false.
                    clearTimeout(fadingTimeoutId);
                    fadingTimeoutId = setTimeout(() => {
                        setLoadingState('none');
                        borderTraceAnimation?.pause();
                    }, fadeOutDuration);
                } else {
                    setLoadingState('none');
                }
                return () => clearTimeout(fadingTimeoutId);
            }
            // eslint-disable-next-line react-hooks/exhaustive-deps
        }, [isLoading]);

        // Keeps track of the size of the container used for animation calculations.
        useSharedResizeObserver({
            ref: overlayRef,
            onUpdate: (entry) => {
                const rect = entry.contentRect;

                // Set the size of the ai loading box on the border cover element for calculating its scale animation.
                if (borderCoverRef.current) {
                    borderCoverRef.current.style.setProperty(
                        '--width',
                        `${rect.width}`,
                    );
                    borderCoverRef.current.style.setProperty(
                        '--height',
                        `${rect.height}`,
                    );
                }

                // Initialize the border trace animation using https://developer.mozilla.org/en-US/docs/Web/API/Web_Animations_API.
                // This cannot be done in pure CSS due to lack of chaining + looping capability.
                if (borderTraceRef.current) {
                    // Calculate the offsets for each border to ensure constant trace speed.
                    const widthOffset =
                        rect.width / (rect.width + rect.height) / 2;
                    const heightOffset =
                        rect.height / (rect.width + rect.height) / 2;
                    const topOffset = widthOffset;
                    const rightOffset = topOffset + heightOffset;
                    const bottomOffset = rightOffset + widthOffset;
                    const leftOffset = 1;
                    const trace = borderTraceRef.current;
                    const animation = trace.animate(
                        [
                            { transform: 'translate(-50%, -50%)', offset: 0 },
                            {
                                transform:
                                    'translate(calc(100cqw - 50%), -50%)',
                                offset: topOffset,
                            },
                            {
                                transform:
                                    'translate(calc(100cqw - 50%), calc(100cqh - 50%))',
                                offset: rightOffset,
                            },
                            {
                                transform:
                                    'translate(-50%, calc(100cqh - 50%))',
                                offset: bottomOffset,
                            },
                            {
                                transform: 'translate(-50%, -50%)',
                                offset: leftOffset,
                            },
                        ],
                        { duration: traceDuration, iterations: Infinity },
                    );
                    // Read the `isLoading` prop to decide initial animation state.
                    if (isLoading === false) {
                        animation.pause();
                    }
                    setBorderTraceAnimation(animation);
                }
            },
        });

        return (
            <Flex
                inline={true}
                direction="column"
                gap="1_5x"
                {...useMergedStyles(
                    className,
                    style,
                    stylex.props(
                        styles.container,
                        colorScheme === 'light'
                            ? styles.colorsLight
                            : styles.colorsDark,
                    ),
                )}
                {...otherProps}
                ref={forwardedRef}
            >
                {/* Overlay container for all the layers of the loading animation. */}
                <div
                    ref={overlayRef}
                    {...stylex.props(
                        styles.overlayContainer,
                        loadingState !== 'none' &&
                            styles.overlayContainerVisible,
                    )}
                >
                    <div
                        {...stylex.props(
                            styles.overlay,
                            styles.borderBase,
                            loadingState === 'loading' &&
                                styles.borderBaseLoading,
                            loadingState === 'fading' &&
                                styles.borderBaseFading,
                        )}
                    />
                    <div
                        ref={borderTraceRef}
                        {...stylex.props(
                            styles.overlay,
                            styles.borderTrace,
                            loadingState === 'loading' &&
                                styles.borderTraceLoading,
                        )}
                    />
                    <div
                        ref={borderCoverRef}
                        {...stylex.props(
                            styles.overlay,
                            styles.borderCover,
                            loadingState === 'fading' &&
                                styles.borderCoverFading,
                        )}
                    />
                    <div
                        {...stylex.props(
                            styles.backgroundPulseBase,
                            styles.backgroundPulse1,
                            (loadingState === 'loading' ||
                                loadingState === 'fading') &&
                                styles.backgroundPulse1Loading,
                            loadingState === 'fading' &&
                                styles.backgroundPulseFading,
                        )}
                    />
                    <div
                        {...stylex.props(
                            styles.backgroundPulseBase,
                            styles.backgroundPulse2,
                            (loadingState === 'loading' ||
                                loadingState === 'fading') &&
                                styles.backgroundPulse2Loading,
                            loadingState === 'fading' &&
                                styles.backgroundPulseFading,
                        )}
                    />
                </div>
                {/* User defined content shows on top of the loading animation overlays. */}
                <Flex
                    direction="column"
                    gap="1_5x"
                    {...stylex.props(
                        styles.contentContainer,
                        fullBleed && styles.fullBleed,
                    )}
                >
                    {children}
                </Flex>
            </Flex>
        );
    },
);
AILoadingBox.displayName = 'AILoadingBox';
export type { AILoadingBoxProps };
export { AILoadingBox };
