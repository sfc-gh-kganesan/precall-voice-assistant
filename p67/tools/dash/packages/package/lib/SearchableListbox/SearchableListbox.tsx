import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type React from 'react';
import type { HTMLAttributes } from 'react';
import { forwardRef, useMemo, useRef } from 'react';
import type { ListBoxProps, Selection } from 'react-aria-components';
import { Autocomplete, useFilter } from 'react-aria-components';

import type { FieldSize } from '../internal/FieldWrapper/FieldWrapper';
import { useMergedRef } from '../internal/hooks/useMergedRef';
import { Flex } from '../Layout';
import type {
    ListboxLoaderIndicatorProps,
    ListboxSectionProps,
} from '../Listbox';
import { Listbox } from '../Listbox';
import type { ListboxOptionProps } from '../Listbox/ListboxOption';
import { ListboxOption } from '../Listbox/ListboxOption';
import { ListboxSection } from '../Listbox/ListboxSection';
import { NONE_ID } from '../Listbox/useListboxSelection';
import {
    type ControlledComponent,
    HighlightedTextProvider,
    useMergedStyles,
} from '../main';
import { SearchInput } from '../SearchInput/SearchInput';
import { SingleLine } from '../Text';
import type { Key } from '../types';
import { devError } from '../util/dev-warning';

const styles = stylex.create({
    wrapper: {
        position: 'relative',
    },
    list: {
        padding: `${tokens['space-vertical-sm']} 0`,
        zIndex: 0,
    },
    noResults: {
        height: tokens['size-md'],
        margin: tokens['space-horizontal-sm'],
        padding: `0 ${tokens['space-horizontal-md']}`,
    },
    searchInput: {
        flexShrink: 0,
        padding: `0 ${tokens['space-horizontal-md']}`,
        zIndex: 1,
    },
});

interface SearchableListboxBaseProps
    extends ControlledComponent<'searchValue', string>,
        Omit<
            HTMLAttributes<HTMLDivElement>,
            'value' | 'defaultValue' | 'spellCheck' | 'onChange' | 'onSubmit'
        > {
    /**
     * Whether the listbox is disabled.
     * @default false
     */
    disabled?: boolean | undefined;
    /**
     * The children of the listbox.
     */
    children: React.ReactNode;
    /**
     * The size of the listbox.
     * @default "regular"
     */
    size?: FieldSize | undefined;
    /**
     * The placeholder of the listbox.
     */
    placeholder?: string | undefined;
    /**
     * The variant of the listbox.
     * @default "regular"
     */
    variant?: 'regular' | 'secondary' | undefined;
    /**
     * The function to render the empty state.
     */
    renderEmptyState?: (() => React.ReactNode) | undefined;
    /**
     * How to filter the options.
     * @default "contains"
     */
    filter?: 'contains' | 'controlled' | undefined;
    /**
     * Whether the listbox should be auto focused.
     * @default true
     */
    autoFocus?: boolean | undefined;
    /**
     * Whether to show the search icon.
     * @default true
     */
    showSearchIcon?: boolean | undefined;
}

interface SearchableListboxSingleSelectionProps
    extends SearchableListboxBaseProps,
        ControlledComponent<'selectedValue', string | number> {
    /**
     * The selection mode of the single select.
     */
    selectionMode?: 'single' | undefined;
    /**
     *
     */
    selectedValues?: never | undefined;
    /**
     * The default selected values of the single select.
     */
    defaultSelectedValues?: never | undefined;
    /**
     * The function to call when the selection changes.
     */
    onSelectedValuesChange?: never | undefined;
}

interface SearchableListboxMultiSelectionProps
    extends SearchableListboxBaseProps {
    /**
     * The selection mode of the multi select.
     */
    selectionMode: 'multiple';
    /**
     * The selected keys of the multi-select.
     */
    selectedValues?: Array<Key> | undefined;
    /**
     * The default selected keys of the multi-select.
     */
    defaultSelectedValues?: Array<Key> | undefined;
    /**
     * The function to call when the selection changes.
     */
    onSelectedValuesChange?: ((key: Array<Key>) => void) | undefined;
    /**
     * The value of the listbox.
     */
    selectedValue?: Key | undefined;
    /**
     * The default value of the listbox.
     */
    defaultSelectedValue?: Key | undefined;
    /**
     * The function to call when the value changes.
     */
    onSelectedValueChange?: ((key: Key) => void) | undefined;
}

type SearchableListboxProps =
    | SearchableListboxSingleSelectionProps
    | SearchableListboxMultiSelectionProps;

/**
 * An list that is filtered by a search input.
 */
const SearchableListbox = forwardRef<HTMLDivElement, SearchableListboxProps>(
    function SearchableListbox(
        {
            disabled,
            children,
            defaultSearchValue,
            onSearchValueChange,
            searchValue,
            placeholder,
            variant = 'regular',
            showSearchIcon = true,
            className,
            style,
            renderEmptyState,
            filter = 'contains',
            autoFocus = true,
            selectionMode = 'single',
            selectedValues,
            defaultSelectedValues,
            onSelectedValuesChange,
            selectedValue,
            defaultSelectedValue,
            onSelectedValueChange,
            ...props
        }: SearchableListboxProps,
        ref,
    ) {
        const { contains } = useFilter({ sensitivity: 'base' });

        const wrapperRef = useRef<HTMLDivElement>(null);
        const combinedRef = useMergedRef(wrapperRef, ref);
        const mergedStyles = useMergedStyles(
            className,
            style,
            stylex.props(styles.wrapper),
        );

        const listBoxProps = useMemo((): Pick<
            ListBoxProps<object>,
            'selectedKeys' | 'defaultSelectedKeys' | 'onSelectionChange'
        > => {
            if (selectionMode === 'multiple') {
                return {
                    selectedKeys: selectedValues,
                    defaultSelectedKeys: defaultSelectedValues,
                    onSelectionChange: (selection: Selection) => {
                        if (selection === 'all') {
                            // onSelectedValuesChange?.(selection);
                        } else {
                            onSelectedValuesChange?.(
                                Array.from(selection).map(
                                    (id) => (id === NONE_ID ? '' : id) as Key,
                                ),
                            );
                        }
                    },
                };
            }

            return {
                selectedKeys: selectedValue ? [selectedValue] : undefined,
                defaultSelectedKeys: defaultSelectedValue
                    ? [defaultSelectedValue]
                    : undefined,
                onSelectionChange: (selection: Selection) => {
                    if (selection === 'all') {
                        devError(
                            'Selection mode single does not support selection all',
                        );
                    }

                    const first = Array.from(selection)[0];

                    if (first) {
                        onSelectedValueChange?.(first);
                    }
                },
            };
        }, [
            selectionMode,
            selectedValues,
            defaultSelectedValues,
            onSelectedValuesChange,
            selectedValue,
            defaultSelectedValue,
            onSelectedValueChange,
        ]);

        return (
            <Autocomplete
                filter={filter === 'contains' ? contains : undefined}
                inputValue={searchValue}
                defaultInputValue={defaultSearchValue}
                onInputChange={onSearchValueChange}
            >
                <HighlightedTextProvider
                    inputValue={searchValue || ''}
                    wrapperRef={wrapperRef}
                >
                    <Flex
                        direction="column"
                        gap="0x"
                        {...mergedStyles}
                        ref={combinedRef}
                    >
                        <SearchInput
                            variant={variant}
                            autoFocus={autoFocus}
                            showSearchIcon={showSearchIcon}
                            aria-label="Search options"
                            disabled={disabled}
                            placeholder={placeholder}
                            {...props}
                            {...stylex.props(styles.searchInput)}
                        />
                        <Listbox.Root
                            {...stylex.props(styles.list)}
                            {...listBoxProps}
                            selectionMode={selectionMode}
                            allowEmptySelection={true}
                            renderEmptyState={
                                renderEmptyState ||
                                (() => (
                                    <Flex
                                        align="center"
                                        justify="center"
                                        grow={1}
                                        {...stylex.props(styles.noResults)}
                                    >
                                        <SingleLine variant="secondary">
                                            No results found
                                        </SingleLine>
                                    </Flex>
                                ))
                            }
                        >
                            {children}
                        </Listbox.Root>
                    </Flex>
                </HighlightedTextProvider>
            </Autocomplete>
        );
    },
);

SearchableListbox.displayName = 'SearchableListbox.Root';

const Item = forwardRef(function SearchableListboxItem(
    props: ListboxOptionProps,
    ref: React.Ref<HTMLLIElement>,
) {
    return <ListboxOption {...props} ref={ref} />;
});

Item.displayName = 'SearchableListbox.Item';

const SearchableListboxLoaderIndicator = forwardRef<
    HTMLDivElement,
    ListboxLoaderIndicatorProps
>(function ComboBoxLoaderIndicator(props, ref) {
    return <Listbox.LoaderIndicator {...props} ref={ref} />;
});

SearchableListboxLoaderIndicator.displayName =
    'SearchableListbox.LoadingIndicator';

const SearchableListboxSection = forwardRef(function SearchableListboxSection(
    props: ListboxSectionProps,
    ref: React.Ref<HTMLAreaElement>,
) {
    return <ListboxSection {...props} ref={ref} />;
});

SearchableListboxSection.displayName = 'SearchableListbox.Section';

export type { SearchableListboxProps };
export {
    SearchableListbox as Root,
    Item,
    SearchableListboxSection as Section,
    SearchableListboxLoaderIndicator as LoadingIndicator,
};
