import { UNSTABLE_useLoadMoreSentinel } from '@react-aria/utils';
import type { Collection } from '@react-types/shared';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import { type ForwardedRef, forwardRef, useMemo, useRef } from 'react';
import { VisuallyHidden } from 'react-aria';

import { Spinner } from '../../Spinner';
import { SharedItem } from '../SharedItem/SharedItem';

const styles = stylex.create({
    loaderIndicator: {
        alignItems: 'center',
        display: 'flex',
        height: tokens['size-md'],
        justifyContent: 'center',
        paddingLeft: tokens['space-horizontal-md'],
        paddingRight: tokens['space-horizontal-md'],
        position: 'relative',
    },
    loadingIndicatorSentinel: {
        height: 0,
        position: 'absolute',
        width: 0,
    },
});

export interface LoaderIndicatorProps {
    /**
     * The label of the loading indicator.
     */
    label?: string | undefined;
    /**
     * An accessible label for the loading indicator.
     * When used without a label this is used to label the spinner.
     */
    'aria-label'?: string | undefined;
}

/**
 * An indicator that can be used to show that more items are loading.
 */
export const LoaderIndicator = forwardRef(function LoaderIndicator(
    props: LoaderIndicatorProps & {
        /**
         * An accessible label for the loading indicator.
         */
        'aria-label'?: string | undefined;
    },
    ref: ForwardedRef<HTMLDivElement>,
) {
    const { label, 'aria-label': ariaLabel = 'Loading more options' } = props;

    return label ? (
        <SharedItem.Wrapper asChild>
            <div ref={ref}>
                <SharedItem.Label
                    label={label}
                    prefixIcon={<Spinner size="small" />}
                />
            </div>
        </SharedItem.Wrapper>
    ) : (
        <SharedItem.Wrapper asChild>
            <div ref={ref} {...stylex.props(styles.loaderIndicator)}>
                <Spinner size="small" />
                <VisuallyHidden>{ariaLabel}</VisuallyHidden>
            </div>
        </SharedItem.Wrapper>
    );
});

export interface LoadingSentinelProps {
    /**
     * Called when the loading indicator is shown and wants to load more items.
     */
    onLoadMore: () => void;
    /**
     * The collection of the loading sentinel.
     */
    collection: Collection<unknown>;
}

/**
 * A component that can be used to asynchronously load more menu items when it is displayed to the user.
 */
export function LoadingSentinel({
    onLoadMore,
    collection,
}: LoadingSentinelProps) {
    const sentinelRef = useRef<HTMLDivElement>(null);
    const memoedLoadMoreProps = useMemo(
        () => ({
            onLoadMore,
            collection,
            sentinelRef,
        }),
        [onLoadMore, collection],
    );
    UNSTABLE_useLoadMoreSentinel(memoedLoadMoreProps, sentinelRef);

    return (
        <div
            data-testid="loadMoreSentinel"
            ref={sentinelRef}
            {...stylex.props(styles.loadingIndicatorSentinel)}
        />
    );
}
