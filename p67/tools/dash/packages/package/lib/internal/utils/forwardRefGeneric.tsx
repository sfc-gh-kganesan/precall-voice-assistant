import type {
    ForwardedRef,
    ForwardRefRenderFunction,
    PropsWithoutRef,
    ReactElement,
    RefAttributes,
} from 'react';
import React from 'react';

type GenericForwardedRefFn<T, P = object> = (
    props: P & RefAttributes<T>,
) => ReactElement | null;

/**
 * The type definition for `forwardRef` is too strict and does not allow for
 * generic types to be passed to the render function. This function is a
 * workaround to allow for generic types to be passed to the render function.
 *
 * It can be removed once we move to react 19 where `forwardRef` is no longer
 * needed.
 */
export function forwardedRefGeneric<T, P = object>(
    render: (props: P, ref: ForwardedRef<T>) => ReactElement | null,
) {
    return React.forwardRef(
        render as ForwardRefRenderFunction<T, PropsWithoutRef<P>>,
    ) as unknown as GenericForwardedRefFn<T, P>;
}
