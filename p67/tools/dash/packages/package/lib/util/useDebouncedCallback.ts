import { useCallback, useEffect, useRef } from 'react';

import { useLatest } from './useLatest';

export type TimeoutId = ReturnType<typeof setTimeout>;
export type DebounceOptions = {
    leading?: boolean | undefined;
    trailing?: boolean | undefined;
};
/**
 * Debounces a callback. A debounce is similar to a throttle, but every attempt to call the function resets the
 * block-timer until the function can be executed again. This means that if the debounced callback is consistently
 * called too frequently, it will not be called again at all - until it stops for long enough time.
 *
 * By default, `options.trailing = true`, meaning that the callback will only be invoked as soon as a certain time
 * has passed since the last call (defined by `waitMs`).
 *
 * @param callback
 * @param waitMs
 * @param options
 * @returns
 */
export function useDebouncedCallback<T extends (...args: never[]) => unknown>(
    callback: T,
    waitMs: number,
    options: DebounceOptions = {
        leading: false,
        trailing: true,
    },
): (...args: Parameters<T>) => TimeoutId {
    const leading = useLatest(options.leading);
    const trailing = useLatest(options.trailing);
    const debouncedCallback = useLatest<T>(callback);
    const timeoutId = useRef<TimeoutId | null>(null);

    useEffect(() => {
        return () => {
            if (timeoutId.current) {
                clearTimeout(timeoutId.current);
            }
        };
    }, []);

    return useCallback<(...args: Parameters<T>) => TimeoutId>(
        (...args: Parameters<T>) => {
            if (timeoutId.current) {
                clearTimeout(timeoutId.current);
            } else if (leading.current) {
                debouncedCallback.current(...args);
            }

            timeoutId.current = setTimeout(() => {
                if (trailing.current) {
                    debouncedCallback.current(...args);
                }
                timeoutId.current = null;
            }, waitMs);

            return timeoutId.current;
        },
        [debouncedCallback, leading, trailing, waitMs],
    );
}
