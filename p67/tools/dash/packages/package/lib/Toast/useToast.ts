import type React from 'react';
import { useMemo } from 'react';
import { UNSTABLE_ToastQueue as ToastQueue } from 'react-aria-components';

import type { ToastVariant } from './types';

interface ToastValue {
    /**
     * The content of the toast.
     */
    children: string;
    /**
     * The variant of the toast.
     */
    variant: ToastVariant;
    /**
     * Whether the toast should be persistent.
     */
    persistent?: boolean | undefined;
    /**
     * An action to be displayed in the toast.
     */
    ctaButton?: React.ReactNode | undefined;
    /**
     * The element's unique identifier. See [MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Global_attributes/id).
     */
    id?: string | undefined;
}

// The way react-aria wants you to animate things (view transitions) doesn't
// work with stylex or firefox yet. So we patch in the animation classes here.
const toastQueue = new ToastQueue<ToastValue>({}) as ToastQueue<ToastValue> & {
    /**
     * Remove a toast from the queue.
     */
    remove: (key: string) => void;
};

const defaultClose = toastQueue.close.bind(toastQueue);

toastQueue.close = (key: string) => {
    const els = document.querySelectorAll(`[data-toast-key="${key}"]`);

    if (!els.length) {
        defaultClose(key);
        return;
    }

    els.forEach((el) => {
        el.setAttribute('data-animation', 'exiting');
    });
};

toastQueue.remove = (key: string) => {
    defaultClose(key);
};

const DEFAULT_DURATION = 4000;

interface ToastOptions {
    /**
     * The label of the toast.
     */
    label?: string | undefined;
    /**
     * The function to call when the toast is closed.
     */
    onClose?: (() => void) | undefined;
    /**
     * An action to be displayed in the toast.
     */
    ctaButton?: React.ReactNode | undefined;
    /**
     * How long the toast should be displayed for.
     */
    timeout?: number | undefined;
    /**
     * Whether the toast should be persistent.
     */
    persistent?: boolean | undefined;
}

interface AddToastOptions extends ToastOptions {
    /**
     * The content of the toast.
     */
    children: string;
    /**
     * The variant of the toast.
     */
    variant: ToastValue['variant'];
}

/**
 * Add a toast to the queue from outside of React.
 */
function addToast({
    children,
    variant,
    persistent,
    timeout: timeoutProp,
    onClose,
    ctaButton,
}: AddToastOptions) {
    // Actionable toasts cannot be auto dismissed. That would fail WCAG SC 2.2.1.
    // It is debatable whether non-actionable toasts would also fail.
    const timeout = persistent
        ? undefined
        : timeoutProp
          ? Math.max(timeoutProp, DEFAULT_DURATION)
          : DEFAULT_DURATION;
    const key = toastQueue.add(
        {
            children,
            variant,
            persistent,
            ctaButton,
        },
        { timeout, onClose },
    );

    return () => toastQueue.close(key);
}

/**
 * Use the toast hook to add a toast to the queue. It takes similar arguments to the `addToast` function.
 */
function useToast() {
    return useMemo(
        () => ({
            neutral(children: string, options?: ToastOptions): () => void {
                return addToast({
                    children,
                    variant: 'neutral',
                    ...(options ?? {}),
                });
            },
            success(children: string, options?: ToastOptions): () => void {
                return addToast({
                    children,
                    variant: 'success',
                    ...(options ?? {}),
                });
            },
            critical(children: string, options?: ToastOptions): () => void {
                return addToast({
                    children,
                    variant: 'critical',
                    ...(options ?? {}),
                });
            },
        }),
        [],
    );
}

export type { ToastValue, ToastOptions };
export { toastQueue, useToast, addToast };
