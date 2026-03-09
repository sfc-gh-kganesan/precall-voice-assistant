import {
    useToast as useReactAriaToast,
    useToastRegion,
} from '@react-aria/toast';
import { filterDOMProps } from '@react-aria/utils';
import type { QueuedToast, ToastState } from '@react-stately/toast';
import { useToastQueue } from '@react-stately/toast';
import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { ClearIcon } from '@snowflake/stellar-icons';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import React, { createContext, useEffect, useRef } from 'react';
import { FocusScope, mergeProps, useFocusRing, useHover } from 'react-aria';
import { useSize } from 'use-shared-resize-observer/use-size';
import { useSyncExternalStore } from 'use-sync-external-store/shim';

import { IconButton } from '../Button';
import { BadgeIllustration } from '../internal';
import { Flex } from '../Layout';
import { SizeContext } from '../main';
import { Portal } from '../Portal';
import type { AriaLabelingProps } from '../types';
import type { ToastValue } from './useToast';
import { toastQueue } from './useToast';

interface AriaToastRegionProps extends AriaLabelingProps {
    /**
     * An accessibility label for the toast region.
     * @default "Notifications"
     */
    'aria-label'?: string | undefined;
}

const HoverContext = createContext(false);

const timer = stylex.keyframes({
    '0%': { transform: 'translateX(-100%)' },
    '100%': { transform: 'translateX(0)' },
});

const fadeOut = stylex.keyframes({
    '0%': { opacity: 1, transform: 'translateY(0)' },
    '100%': { opacity: 0, transform: 'translateY(-100%)' },
});

const slideUp = stylex.keyframes({
    '0%': { height: 'var(--toast-height)' },
    '100%': { height: 0 },
});

const styles = stylex.create({
    portal: {
        alignItems: 'center',
        display: 'flex',
        flexDirection: 'column',
        inset: 0,
        paddingTop: tokens['space-vertical-4xl'],
        pointerEvents: 'none',
        position: 'fixed',
        zIndex: 100000 + 1,
    },
    toaster: {},
    list: {
        alignItems: 'center',
        display: 'flex',
        flexDirection: 'column-reverse',
        margin: 0,
        padding: 0,
        pointerEvents: 'auto',
    },
    item: {
        listStyle: 'none',

        animationDuration: '300ms',
        animationName: {
            ':is([data-animation=exiting])': slideUp,
        },
        animationTimingFunction: 'ease-out',
    },
    toast: {
        backgroundColor: baltoTheme.surfaceLevel_3Background,
        borderRadius: tokens['radius-md'],
        boxShadow: baltoTheme.elevation_3BoxShadow,
        color: baltoTheme.reusableTextPrimary,
        marginTop: tokens['space-vertical-lg'],
        maxWidth: 560,
        overflow: 'hidden',
        padding: `0 ${tokens['space-horizontal-md']}`,
        position: 'relative',

        animationDuration: '300ms',
        animationName: {
            ':is([data-animation=exiting])': fadeOut,
        },
        animationTimingFunction: 'ease-out',
    },
    toastIcon: {
        flexShrink: 0,
    },
    toastMessage: {
        padding: `${tokens['space-vertical-md']} 0`,
        wordBreak: 'break-word',
    },
    timer: {
        bottom: 0,
        left: 0,
        position: 'absolute',
        right: 0,

        backgroundColor: baltoTheme.surfaceLevel_3Border,
        height: tokens['size-6xs'],

        animationIterationCount: 1,
        animationName: timer,
        animationTimingFunction: 'linear',
    },
});

const toastProviders = new Set();
const subscriptions = new Set<() => void>();

/**
 * Subscribe to the toast queue.
 */
function subscribe(fn: () => void) {
    subscriptions.add(fn);
    return () => subscriptions.delete(fn);
}

/**
 * Trigger the subscriptions.
 */
function triggerSubscriptions() {
    for (const fn of subscriptions) {
        fn();
    }
}

/**
 * Get the active toast container.
 */
function getActiveToastContainer() {
    return toastProviders.values().next().value;
}

/**
 * Use the active toast container.
 */
function useActiveToastContainer() {
    return useSyncExternalStore(
        subscribe,
        getActiveToastContainer,
        getActiveToastContainer,
    );
}

interface ToastProps {
    /**
     * The toast.
     */
    toast: QueuedToast<ToastValue>;
    /**
     * The toast state.
     */
    state: ToastState<ToastValue>;
}

const Toast = (props: ToastProps) => {
    const { toast, state } = props;
    const domRef = useRef(null);
    const { closeButtonProps, titleProps, toastProps, contentProps } =
        useReactAriaToast(props, state, domRef);
    const { isFocusVisible, focusProps } = useFocusRing();
    const isHovered = React.useContext(HoverContext);

    const wrapperRef = useRef(null);
    const size = useSize(wrapperRef);

    return (
        <li
            ref={wrapperRef}
            data-toast-key={toast.key}
            {...stylex.props(styles.item)}
            style={
                {
                    '--toast-height': size.height
                        ? `${size.height}px`
                        : undefined,
                } as React.CSSProperties
            }
            onAnimationStart={() => {}}
            onAnimationEnd={(e) => {
                if (e.target !== e.currentTarget) {
                    return;
                }

                toastQueue.remove(props.toast.key);
            }}
        >
            <Flex
                align="center"
                gap="1_5x"
                {...mergeProps(toastProps, focusProps)}
                {...filterDOMProps(toast.content)}
                ref={domRef}
                data-focus-visible={isFocusVisible}
                {...stylex.props(styles.toast)}
                data-toast-key={toast.key}
            >
                <Flex
                    align="center"
                    gap="1_5x"
                    {...contentProps}
                    {...stylex.props(styles.toastMessage)}
                >
                    {toast.content.variant === 'success' && (
                        <BadgeIllustration
                            size="xsmall"
                            variant="success"
                            {...stylex.props(styles.toastIcon)}
                        />
                    )}
                    {toast.content.variant === 'critical' && (
                        <BadgeIllustration
                            size="xsmall"
                            variant="critical"
                            {...stylex.props(styles.toastIcon)}
                        />
                    )}
                    <div role="presentation" {...titleProps}>
                        {toast.content.children}
                    </div>
                </Flex>

                <SizeContext.Provider value="small">
                    {toast.content.ctaButton}
                </SizeContext.Provider>

                <IconButton
                    variant="tertiary"
                    size="small"
                    icon={ClearIcon}
                    aria-label={closeButtonProps['aria-label'] || 'Close toast'}
                    onClick={() => {
                        state.close(toast.key);
                    }}
                />

                {toast.timeout && !toast.content.persistent && (
                    <div
                        {...stylex.props(styles.timer)}
                        style={{
                            animationDuration: `${toast.timeout}ms`,
                            animationPlayState: isHovered
                                ? 'paused'
                                : 'running',
                        }}
                    />
                )}
            </Flex>
        </li>
    );
};

interface ToastPortalProps extends AriaToastRegionProps {
    /**
     * The children of the toast portal.
     */
    children: React.ReactNode;
    /**
     * The state of the toast.
     */
    state: ToastState<ToastValue>;
}

const ToastPortal = ({
    children,
    state,
    ...props
}: ToastPortalProps): JSX.Element | null => {
    const ref = useRef(null);
    const { regionProps } = useToastRegion(props, state, ref);
    const { focusProps, isFocusVisible } = useFocusRing();
    const { hoverProps, isHovered } = useHover({});

    return (
        <HoverContext.Provider value={isHovered}>
            <FocusScope>
                <Portal {...stylex.props(styles.portal)}>
                    <div
                        {...mergeProps(regionProps, focusProps, hoverProps)}
                        ref={ref}
                        data-focus-visible={isFocusVisible}
                        {...stylex.props(styles.toaster)}
                    >
                        {children}
                    </div>
                </Portal>
            </FocusScope>
        </HoverContext.Provider>
    );
};

/**
 * This component is used to render the toast notifications.
 * It is used in conjunction with the `useToast` hook to add toasts to the queue.
 */
function Toaster(props: AriaToastRegionProps) {
    const ref = useRef(null);
    const state = useToastQueue(toastQueue);
    const activeToastContainer = useActiveToastContainer();

    useEffect(() => {
        toastProviders.add(ref);
        triggerSubscriptions();

        return () => {
            // Remove this toast provider, and call subscriptions.
            // This will cause all other instances to re-render,
            // and the first one to become the new active toast provider.
            toastProviders.delete(ref);
            triggerSubscriptions();
        };
    }, []);

    if (ref === activeToastContainer && state.visibleToasts.length > 0) {
        return (
            <ToastPortal state={state} {...props}>
                <ol {...stylex.props(styles.list)}>
                    {state.visibleToasts.map((toast) => {
                        return (
                            <Toast
                                key={toast.key}
                                toast={toast}
                                state={state}
                            />
                        );
                    })}
                </ol>
            </ToastPortal>
        );
    }

    return null;
}

export { Toaster };
