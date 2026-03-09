import type { Node } from '@react-types/shared';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import { forwardRef } from 'react';
import type {
    Key,
    LayoutInfo,
    ListLayoutOptions,
    Rect,
} from 'react-aria-components';
import {
    ListBoxLoadMoreItem,
    ListLayout,
    ListBox as ReactAriaListBox,
    Virtualizer,
} from 'react-aria-components';
import { useMergedStyles } from '../hooks';
import type {
    LoaderIndicatorProps,
    LoadingSentinelProps,
} from '../internal/LoaderIndicator';
import { LoaderIndicator } from '../internal/LoaderIndicator';
import { forwardedRefGeneric } from '../internal/utils/forwardRefGeneric';
import type { AriaLabelingProps, Selection } from '../types';
import { ListboxOption } from './ListboxOption';
import { ListboxSection } from './ListboxSection';

interface ListboxLoaderIndicatorProps
    extends LoaderIndicatorProps,
        Pick<LoadingSentinelProps, 'onLoadMore'> {
    /**
     * Whether the list box is loading more items.
     */
    isLoading: boolean;
}

const ListboxLoaderIndicator = forwardRef<
    HTMLDivElement,
    ListboxLoaderIndicatorProps
>(
    (
        { label, isLoading, onLoadMore, 'aria-label': ariaLabel, ...props },
        ref,
    ) => {
        if (!isLoading) {
            return null;
        }

        return (
            <ListBoxLoadMoreItem
                ref={ref}
                {...props}
                onLoadMore={onLoadMore}
                isLoading={isLoading}
            >
                <LoaderIndicator aria-label={ariaLabel} label={label} />
            </ListBoxLoadMoreItem>
        );
    },
);

ListboxLoaderIndicator.displayName = 'Listbox.LoaderIndicator';

class StickyListboxLayout<T, O extends ListLayoutOptions> extends ListLayout<
    T,
    O
> {
    shouldInvalidate() {
        return true;
    }

    getVisibleLayoutInfos(rect: Rect): LayoutInfo[] {
        const info = super.getVisibleLayoutInfos(rect);
        const stickyItems: Node<T>[] = [];

        // Find the sticky items
        for (const item of this.collection) {
            if (this.collection.getItem(item.key)?.props['data-sticky']) {
                stickyItems.push(item);
            }
        }

        // Add the sticky items to the layout info if needed
        for (const item of stickyItems) {
            const currentLayoutInfo = info.find((i) => i.key === item.key);

            if (!currentLayoutInfo) {
                const layoutInfo = this.getLayoutInfo(item.key);

                if (layoutInfo) {
                    layoutInfo.isSticky = true;
                    layoutInfo.zIndex = 2;
                    layoutInfo.allowOverflow = true;

                    info.push(layoutInfo);
                }
            } else {
                currentLayoutInfo.isSticky = true;
                currentLayoutInfo.zIndex = 2;
                currentLayoutInfo.allowOverflow = true;
            }
        }

        return info;
    }

    // Provide a LayoutInfo for a specific item.
    getLayoutInfo(key: Key): LayoutInfo | null {
        return super.getLayoutInfo(key);
    }
}

const styles = stylex.create({
    list: {
        width: '100%',

        flexGrow: 1,
        outline: 'none',
        overflow: 'auto',
    },
    loaderIndicator: {
        alignItems: 'center',
        display: 'flex',
        height: tokens['size-md'],
        justifyContent: 'center',
        width: '100%',
    },
});

interface ListboxProps<T> extends AriaLabelingProps {
    /**
     * The render function for the empty state.
     */
    renderEmptyState?: (() => React.ReactNode) | undefined;
    /**
     * The class name of the list box.
     */
    className?: string | undefined;
    /**
     * The style of the list box.
     */
    style?: React.CSSProperties | undefined;
    /**
     * The callback function that is called when the selection changes.
     */
    onSelectionChange?: ((key: Selection) => void) | undefined;
    /**
     * The mode of the selection.
     */
    selectionMode?: 'single' | 'multiple' | undefined;
    /**
     * Whether the list box is virtualized.
     * @default true
     */
    isVirtualized?: boolean | undefined;
    /**
     * The contents of the collection.
     *
     * - JSX elements
     * - A function that returns a JSX element (used with `items`)
     */
    children?: React.ReactNode | ((item: T) => React.ReactNode) | undefined;
    /** Items in the list box. */
    items?: Array<T> | undefined;
    /**
     * The selected items of the list box.
     */
    selection?: Key[] | undefined;
    /**
     * Whether to disallow empty selection.
     * @default false
     */
    allowEmptySelection?: boolean | undefined;
}

/**
 * The component that renders a list box.
 */
const ListboxComponent = forwardedRefGeneric(
    <T extends object>(
        {
            children,
            renderEmptyState,
            className,
            style,
            items,
            onSelectionChange,
            selectionMode = 'single',
            selection: selectedKeys,
            isVirtualized = true,
            allowEmptySelection = false,
            ...props
        }: ListboxProps<T>,
        ref?: React.Ref<HTMLDivElement>,
    ) => {
        const mergedStyles = useMergedStyles(
            className,
            style,
            stylex.props(styles.list),
        );
        const listbox = (
            <ReactAriaListBox
                ref={ref}
                {...mergedStyles}
                renderEmptyState={renderEmptyState}
                disallowEmptySelection={!allowEmptySelection}
                items={items}
                onSelectionChange={onSelectionChange}
                selectionMode={selectionMode}
                selectedKeys={selectedKeys}
                {...props}
            >
                {children}
            </ReactAriaListBox>
        );

        if (!isVirtualized) {
            return listbox;
        }

        return (
            <Virtualizer
                layout={StickyListboxLayout}
                layoutOptions={{ estimatedRowHeight: 32 }}
            >
                {listbox}
            </Virtualizer>
        );
    },
);

// @ts-expect-error - Couldn't get displayName to work with forwardedRefGeneric
// We can't cast to any because it influences the generated type
ListboxComponent.displayName = 'Listbox.Root';

export type { ListboxProps, ListboxLoaderIndicatorProps };
export {
    ListboxComponent as Root,
    ListboxOption as Option,
    ListboxSection as Section,
    ListboxLoaderIndicator as LoaderIndicator,
};
