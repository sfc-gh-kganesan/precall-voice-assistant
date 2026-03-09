import { useCallback } from 'react';
import { useId } from 'react-aria';

/**
 * react-aria defaults to the label when `id=""` is passed.
 * In snapps the user provided code uses `""` as a value a lot and we need to preserve that in the selection.
 * This constant is used to represent that value and is converted back to `""` in the selection.
 */
export const NONE_ID = '__NONE__';

export function normalizeListboxId<V>(id: V) {
    return typeof id === 'string' ? id || NONE_ID : id;
}

export function normalizeListboxIds<V>(ids: V[] | undefined) {
    return ids
        ? ids
              .map(normalizeListboxId)
              .filter((id): id is NonNullable<typeof id> => Boolean(id))
        : undefined;
}

export function useListboxOptionId<V>(id: V, label: string | undefined) {
    const genId = useId();
    return typeof id === 'string' ? normalizeListboxId(id) : (label ?? genId);
}

export function useListboxSelection<V>({
    onSelectedIdChange,
}: {
    onSelectedIdChange: ((id: V) => void) | undefined;
}) {
    const fn = useCallback(
        (id: V) => {
            if (id === NONE_ID) {
                onSelectedIdChange?.('' as V);
            } else {
                onSelectedIdChange?.(id as V);
            }
        },
        [onSelectedIdChange],
    );

    if (!onSelectedIdChange) {
        return undefined;
    }

    return fn;
}

export function useListboxSelectionMultiple<V>({
    onSelectedIdChange,
}: {
    onSelectedIdChange: ((id: V[]) => void) | undefined;
}) {
    const fn = useCallback(
        (ids: V[]) => {
            onSelectedIdChange?.(
                ids.map((id) => (id === NONE_ID ? '' : id) as V),
            );
        },
        [onSelectedIdChange],
    );

    if (!onSelectedIdChange) {
        return undefined;
    }

    return fn;
}
