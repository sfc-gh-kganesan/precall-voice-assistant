import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import * as stylex from '@stylexjs/stylex';
import type { HTMLAttributes } from 'react';
import { forwardRef, useEffect, useState } from 'react';

import { useMergedStyles } from '../hooks';
import { useTypeRamp } from '../internal/hooks/useTypeRamp';
import { Flex } from '../Layout';
import type { Size } from '../types';
import endSprites from './sprites/end.svg';
import loopSprites from './sprites/loop.svg';
import startSprites from './sprites/start.svg';

interface AILoadingAvatarProps extends HTMLAttributes<HTMLDivElement> {
    /**
     * Whether the loading avatar is loading.
     * @default false
     */
    isLoading?: boolean | undefined;
    /**
     * The size of the loading avatar.
     * @default "small"
     */
    size?: Extract<Size, 'small' | 'regular'> | undefined;
    /**
     * The label of the loading avatar.
     */
    label?: string | undefined;
}

const SPRITE_SIZE = 160; // The native size (height) of the avatar sprites.
const START_SPRITES_WIDTH = 19200;
const LOOP_SPRITES_WIDTH = 15360;
const END_SPRITES_WIDTH = 17280;
const START_SPRITES_FPS = START_SPRITES_WIDTH / SPRITE_SIZE;
const LOOP_SPRITES_FPS = LOOP_SPRITES_WIDTH / SPRITE_SIZE;
const END_SPRITES_FPS = END_SPRITES_WIDTH / SPRITE_SIZE;

const avatarSize = {
    // The desired sizes of the avatar (used for positioning and scaling).
    small: 20,
    regular: 100,
};

// Loading animationdurations in milliseconds.
const loadingStartDuration = 2500;
const loadingLoopDuration = 1000;
const loadingStopDuration = 2500;

// Animation that moves the background sprites from left to right.
const leftToRight = stylex.keyframes({
    from: {
        transform: 'translateX(0)',
    },
    to: {
        transform: 'translateX(calc(-100% + 160px))',
    },
});

// Animation that for the successive "..." after the label.
const dot1 = stylex.keyframes({
    '0%, 25%': { opacity: 0 },
    '25%, 100%': { opacity: 1 },
});
const dot2 = stylex.keyframes({
    '0%, 50%': { opacity: 0 },
    '50%, 100%': { opacity: 1 },
});
const dot3 = stylex.keyframes({
    '0%, 75%': { opacity: 0 },
    '75%, 100%': { opacity: 1 },
});

const styles = stylex.create({
    avatarViewport: {
        overflow: 'hidden',
    },
    avatarViewportRegular: {
        height: avatarSize.regular,
        width: avatarSize.regular,
    },
    avatarViewportSmall: {
        height: avatarSize.small,
        width: avatarSize.small,
    },
    spritesContainer: {
        display: 'inline-block',
        height: SPRITE_SIZE,
        overflow: 'hidden',
        position: 'relative',
        width: SPRITE_SIZE,
    },
    spritesContainerRegular: {
        transform: `translate(calc(-50% + ${avatarSize.regular}px / 2), calc(-50% + ${avatarSize.regular}px / 2)) scale(${avatarSize.regular / SPRITE_SIZE})`,
    },
    spritesContainerSmall: {
        transform: `translate(calc(-50% + ${avatarSize.small}px / 2), calc(-50% + ${avatarSize.small}px / 2)) scale(${avatarSize.small / SPRITE_SIZE})`,
    },
    backgroundSprites: (spritesUrl: string, width: number, height: number) => ({
        backgroundImage: `url("${spritesUrl}")`,
        backgroundSize: `${width}px ${height}px`,
        display: 'inline-block',
        height,
        inset: 0,
        opacity: 0,
        position: 'absolute',
        width,
    }),
    avatarInitial: {
        opacity: 1,
    },
    avatarStarting: {
        animationDuration: `${loadingStartDuration}ms`,
        animationFillMode: 'forwards',
        animationName: leftToRight,
        animationTimingFunction: `steps(${START_SPRITES_FPS - 1})`,
        opacity: 1,
    },
    avatarLooping: {
        animationDuration: `${loadingLoopDuration}ms`,
        animationIterationCount: 'infinite',
        animationName: leftToRight,
        animationTimingFunction: `steps(${LOOP_SPRITES_FPS - 1})`,
        opacity: 1,
    },
    avatarStopping: {
        animationDuration: `${loadingStopDuration}ms`,
        animationFillMode: 'forwards',
        animationName: leftToRight,
        animationTimingFunction: `steps(${END_SPRITES_FPS - 1})`,
        opacity: 1,
    },
    label: {
        color: baltoTheme.reusableTextSecondary,
        display: 'inline-flex',
        flexWrap: 'wrap',
        textTransform: 'uppercase',
    },
    dot1: {
        animationDuration: '1.5s',
        animationIterationCount: 'infinite',
        animationName: dot1,
        animationTimingFunction: 'steps(1)',
    },
    dot2: {
        animationDuration: '1.5s',
        animationIterationCount: 'infinite',
        animationName: dot2,
        animationTimingFunction: 'steps(1)',
    },
    dot3: {
        animationDuration: '1.5s',
        animationIterationCount: 'infinite',
        animationName: dot3,
        animationTimingFunction: 'steps(1)',
    },
});

// Internal loading states used to track the current state of the avatar.
type LoadingState = 'initial' | 'starting' | 'looping' | 'stopping';

const AILoadingAvatar = forwardRef<HTMLDivElement, AILoadingAvatarProps>(
    (props, forwardedRef) => {
        const {
            className,
            style,
            isLoading,
            size = 'small',
            label,
            children,
            ...otherProps
        } = props;
        const [loadingState, setLoadingState] =
            useState<LoadingState>('initial');
        const [loopStartTime, setLoopStartTime] = useState<number>(-1);
        const styleProps = useMergedStyles(className, style, stylex.props());

        // Updates the internal loading state based on the `isLoading` prop changes.
        useEffect(() => {
            let startingTimeoutId: ReturnType<typeof setTimeout> | undefined;
            let stoppingTimeoutId: ReturnType<typeof setTimeout> | undefined;
            let remainingLoopingTimeoutId:
                | ReturnType<typeof setTimeout>
                | undefined;

            const clearTimeouts = () => {
                clearTimeout(startingTimeoutId);
                clearTimeout(stoppingTimeoutId);
                clearTimeout(remainingLoopingTimeoutId);
            };

            if (isLoading === false) {
                // When isLoading=false and the loading state is "starting" or "looping",
                // set the loading state to "stopping" followed by "initial" after a timeout.
                if (loadingState === 'starting' || loadingState === 'looping') {
                    let stopLoopingDelay = 0;
                    if (loadingState === 'looping' && loopStartTime !== -1) {
                        // If the loading state is "looping", calculate the remaining time to finish the current loop
                        // before playing the stop animation so that they can be connected seamlessly.
                        stopLoopingDelay =
                            loadingLoopDuration -
                            ((Date.now() - loopStartTime) %
                                loadingLoopDuration);
                    }
                    clearTimeouts();
                    remainingLoopingTimeoutId = setTimeout(() => {
                        setLoadingState('stopping');
                        stoppingTimeoutId = setTimeout(() => {
                            setLoadingState('initial');
                        }, loadingStopDuration);
                    }, stopLoopingDelay);
                }
            } else {
                // When isLoading=true, always reset the loading state to "starting", followed by "looping" after a timeout.
                setLoadingState('starting');
                clearTimeouts();
                startingTimeoutId = setTimeout(() => {
                    setLoadingState('looping');
                    setLoopStartTime(Date.now());
                }, loadingStartDuration);
            }
            return () => {
                clearTimeouts();
            };
            // eslint-disable-next-line react-hooks/exhaustive-deps
        }, [isLoading]);

        const labelTextStyles = useTypeRamp('allCaps');

        return (
            <Flex
                inline={true}
                direction="row"
                align="center"
                gap="1x"
                {...otherProps}
                {...styleProps}
                ref={forwardedRef}
            >
                {children}
                <div
                    {...stylex.props(
                        styles.avatarViewport,
                        size === 'small' && styles.avatarViewportSmall,
                        size === 'regular' && styles.avatarViewportRegular,
                    )}
                >
                    <div
                        {...stylex.props(
                            styles.spritesContainer,
                            size === 'small' && styles.spritesContainerSmall,
                            size === 'regular' &&
                                styles.spritesContainerRegular,
                        )}
                    >
                        <div
                            {...stylex.props(
                                styles.backgroundSprites(
                                    startSprites,
                                    START_SPRITES_WIDTH,
                                    SPRITE_SIZE,
                                ),
                                loadingState === 'initial' &&
                                    styles.avatarInitial,
                                loadingState === 'starting' &&
                                    styles.avatarStarting,
                            )}
                        ></div>
                        <div
                            {...stylex.props(
                                styles.backgroundSprites(
                                    loopSprites,
                                    LOOP_SPRITES_WIDTH,
                                    SPRITE_SIZE,
                                ),
                                loadingState === 'looping' &&
                                    styles.avatarLooping,
                            )}
                        ></div>
                        <div
                            {...stylex.props(
                                styles.backgroundSprites(
                                    endSprites,
                                    END_SPRITES_WIDTH,
                                    SPRITE_SIZE,
                                ),
                                loadingState === 'stopping' &&
                                    styles.avatarStopping,
                            )}
                        ></div>
                    </div>
                </div>
                {label && (
                    <div {...stylex.props(styles.label, labelTextStyles)}>
                        {label}
                        {isLoading && (
                            <div>
                                <span {...stylex.props(styles.dot1)}>.</span>
                                <span {...stylex.props(styles.dot2)}>.</span>
                                <span {...stylex.props(styles.dot3)}>.</span>
                            </div>
                        )}
                    </div>
                )}
            </Flex>
        );
    },
);
AILoadingAvatar.displayName = 'AILoadingAvatar';
export type { AILoadingAvatarProps };
export { AILoadingAvatar };
