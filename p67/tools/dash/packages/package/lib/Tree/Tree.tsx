import { useId } from '@react-aria/utils';
import { useControlledState } from '@react-stately/utils';
import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import {
    ChevronRightSmallIcon,
    IconContextProvider,
    type IconType,
    SearchIcon,
    XSmallIcon,
} from '@snowflake/stellar-icons';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { HTMLAttributes } from 'react';
import React, { useEffect, useState } from 'react';
import { useFocusRing, useFocusWithin } from 'react-aria';
import type { DragAndDropHooks } from 'react-aria-components';
import {
    Button,
    Collection,
    DropIndicator,
    ListLayout,
    Provider,
    Tree as ReactAriaTree,
    TreeItem as ReactAriaTreeItem,
    TreeItemContent as ReactAriaTreeItemContent,
    useDragAndDrop,
    Virtualizer,
} from 'react-aria-components';
import type { TreeData } from 'react-stately';
import { useTreeData } from 'react-stately';

import { IconButton } from '../Button';
import { Checkbox, TextInput } from '../Form';
import { CheckboxContext } from '../Form/CheckboxContext';
import { HighlightedText, HighlightedTextProvider } from '../HighlightedText';
import { useMergedStyles } from '../hooks';
import { useMergedRef } from '../internal/hooks/useMergedRef';
import { useTypeRamp } from '../internal/hooks/useTypeRamp';
import { forwardedRefGeneric } from '../internal/utils/forwardRefGeneric';
import { Flex } from '../Layout';
import { OverflowTooltip } from '../OverflowTooltip';
import { SingleLine } from '../Text';
import type { ControlledComponent } from '../util/Controlled';

const styles = stylex.create({
    disabledWrapper: {
        color: baltoTheme.reusableDisabledText,
        cursor: 'not-allowed',
    },
    tree: {
        flexGrow: 1,
        minHeight: 0,
        overflow: 'auto',
    },
    itemWrapper: {
        // TOOD(APPS-55669)

        '--content-outline': {
            default: 'none',
            ':is([data-focus-visible])': `inset 0 0 0 2px ${baltoTheme.reusableBorderFocusedActiveItem}`,
        },

        '--content-bg': {
            ':is([data-selected]):hover':
                baltoTheme.reusableSelectedHoveredBackground,
            ':is([data-selected])': baltoTheme.reusableSelectedBackground,
            ':hover:not([data-disabled])':
                baltoTheme.reusableBackgroundRowHover,
        },

        backgroundColor: {
            '::highlight(tree-highlight)':
                baltoTheme.reusableSelectedBackground,
        },
        borderRadius: tokens['radius-sm'],
        color: {
            '::highlight(tree-highlight)': baltoTheme.reusableSelectedText,
        },
    },
    item: {
        display: 'flex',
        height: tokens['size-md'],
        outline: {
            ':focus-visible': 'none',
        },
        position: 'relative',
    },
    empty: {
        alignItems: 'center',
        display: 'flex',
        height: '100%',
        justifyContent: 'center',
        paddingLeft: tokens['space-horizontal-md'],
        width: '100%',
    },
    itemContent: {
        backgroundColor: 'var(--content-bg)',
        borderRadius: tokens['radius-sm'],
        boxShadow: 'var(--content-outline)',
        flexGrow: 1,
        margin: '1px 0',
        minWidth: 0,
        paddingLeft: tokens['space-horizontal-2xs'],
        paddingRight: tokens['space-horizontal-md'],
        userSelect: 'none',
    },
    stretch: {
        flexGrow: 1,
        minWidth: 0,
    },
    subItem: {
        paddingLeft: tokens['space-horizontal-md'],
    },
    groupCollapse: {
        backgroundColor: 'transparent',
        borderWidth: 0,
        outline: {
            ':focus': 'none',
        },
        padding: 0,

        height: tokens['size-2xs'],
        width: tokens['size-2xs'],

        transform: {
            default: 'rotate(90deg)',
            ':is([aria-label="Expand"])': 'rotate(0deg)',
        },
        transition: 'transform 200ms',
    },
    spacer: {
        height: tokens['size-2xs'],
        width: tokens['size-2xs'],
    },
    lines: {
        display: 'flex',
        gap: 19,
        justifyContent: 'space-between',
    },
    line: {
        backgroundColor: baltoTheme.reusableBorderDefault,
        height: '100%',
        width: 1,

        opacity: {
            ':is([data-selected] *)': 0,
        },
    },
    footer: {
        padding: `0 ${tokens['space-horizontal-sm']}`,
    },
    footerInner: {
        borderTopColor: baltoTheme.reusableBorderDefault,
        borderTopStyle: 'solid',
        borderTopWidth: 1,
        padding: `${tokens['space-vertical-sm']} 0`,
    },
    searchButton: {
        alignItems: 'center',
        backgroundColor: 'transparent',
        borderRadius: tokens['radius-sm'],
        borderWidth: 0,
        display: 'flex',
        flexGrow: 1,
        gap: tokens['space-gap-2xs'],
        height: tokens['size-md'],
        outline: 'none',

        boxShadow: {
            ":is([data-focus-visible='true'])": `0 0 0 2px ${baltoTheme.reusableBorderFocusedActiveItem}`,
        },
    },
    searchInputWrapper: {
        position: 'relative',
    },
    searchInput: {
        flexGrow: 1,
        '::-webkit-search-cancel-button': {
            display: 'none',
        },
    },
    searchInputClear: {
        position: 'absolute',
        right: tokens['space-horizontal-sm'],
        top: '50%',
        transform: 'translateY(-50%)',
    },
    dropIndicatorLine: {
        backgroundColor: baltoTheme.reusableBorderFocusedActiveItem,
        height: 10,
        width: '100%',
    },
    dropTargetOutline: {
        boxShadow: `inset 0 0 0 2px ${baltoTheme.reusableBorderFocusedActiveItem}`,
    },
    dragButton: {
        height: 0,
        left: 0,
        opacity: 0,
        position: 'absolute',
        top: 0,
        width: 0,
    },
});

interface TreeItem {
    /**
     * A unique identifier for the tree item.
     */
    id: string;
    /**
     * The label of the tree item.
     */
    label: string;
    /**
     * The children of the tree item.
     */
    children?: Array<TreeItem> | undefined;
}

type DnDTreeProps<T extends TreeItem> = {
    /**
     * Called when the tree items are moved.
     */
    onMoveItem: (data: Array<T>) => void;
    /**
     * The items of the tree.
     */
    items: Array<T>;
};

type TreeProps<T extends TreeItem> = {
    /**
     * The children of the tree.
     */
    children: React.ReactNode | ((props: T) => React.ReactNode);
    /**
     * The items of the tree.
     */
    items?: Array<T> | undefined;
    /**
     * The disabled items of the tree.
     */
    disabled?: string[] | undefined;
    /**
     * The selected items of the tree.
     */
    selection?: string[] | undefined;
    /**
     * The default selected items of the tree.
     */
    defaultSelection?: string[] | undefined;
    /**
     * The function to call when the selection changes.
     */
    onSelectionChange?: ((keys: Array<string> | 'all') => void) | undefined;
    /**
     * The mode of the tree.
     */
    selectionMode?: 'none' | 'single' | 'multiple' | undefined;
    /**
     * The class name of the tree.
     */
    className?: string | undefined;
    /**
     * The style of the tree.
     */
    style?: React.CSSProperties | undefined;
    /**
     * The expanded keys of the tree.
     */
    expandedKeys?: string[] | undefined;
    /**
     * The function to call when the expanded keys change.
     */
    onExpandedChange?: ((keys: string[]) => void) | undefined;
    /**
     * An accessible label for the tree.
     */
    'aria-label'?: string | undefined;
    /**
     * An id of an element that labels the tree.
     */
    'aria-labelledby'?: string | undefined;
} & (
    | {
          /**
           * onMoveItem
           */
          onMoveItem?: never | undefined;
      }
    | DnDTreeProps<T>
);

/**
 * A tree component that can be used to display a tree of items.
 */
const Root = forwardedRefGeneric(
    <T extends TreeItem>(
        props: TreeProps<T>,
        ref?: React.Ref<HTMLDivElement>,
    ) => {
        if (props.onMoveItem) {
            return <DragAndDropTree {...props} />;
        }

        return <TreeImpl {...props} ref={ref} />;
    },
);

// @ts-expect-error - Couldn't get displayName to work with forwardedRefGeneric
// We can't cast to any because it influences the generated type
Root.displayName = 'Tree.Root';

/**
 * A tree component that supports drag and drop.
 */
function DragAndDropTree<T extends TreeItem>({
    onMoveItem,
    ...props
}: TreeProps<T> & DnDTreeProps<T>) {
    const internalTreeData = useTreeData({
        initialItems: props.items,
    });

    // Notify the parent when the items update
    useEffect(() => {
        /**
         * Convert the tree data to the tree item type.
         */
        function getNodeValue(item: TreeData<T>['items'][number]): T {
            return {
                ...item.value,
                children: item.children?.map(getNodeValue),
            };
        }

        const newTreeData = internalTreeData.items.map((i) => getNodeValue(i));
        onMoveItem(newTreeData);
    }, [internalTreeData.items, onMoveItem]);

    const { dragAndDropHooks } = useDragAndDrop({
        getItems: (keys) => {
            return [...keys]
                .map((key) => internalTreeData.getItem(key))
                .filter(
                    (item): item is NonNullable<typeof item> =>
                        item !== undefined,
                )
                .map((item) => ({
                    'text/plain': item.value.label,
                }));
        },
        onMove(e) {
            const targetNode = internalTreeData.getItem(e.target.key);

            if (e.target.dropPosition === 'before') {
                internalTreeData.moveBefore(e.target.key, e.keys);
            } else if (e.target.dropPosition === 'after') {
                internalTreeData.moveAfter(e.target.key, e.keys);
            } else if (e.target.dropPosition === 'on' && targetNode) {
                const targetIndex = targetNode.children
                    ? targetNode.children.length
                    : 0;
                const keyArray = Array.from(e.keys);

                for (let i = 0; i < keyArray.length; i++) {
                    const value = keyArray[i];

                    if (value) {
                        internalTreeData.move(
                            value,
                            e.target.key,
                            targetIndex + i,
                        );
                    }
                }
            }
        },
        shouldAcceptItemDrop(target) {
            const targetItem = internalTreeData.getItem(target.key);
            return Boolean(targetItem?.value.children);
        },
        renderDropIndicator(target) {
            return (
                <DropIndicator
                    target={target}
                    {...stylex.props(styles.dropIndicatorLine)}
                />
            );
        },
    });

    return <TreeImpl {...props} dragAndDropHooks={dragAndDropHooks} />;
}

/**
 * The default tree implementation.
 */
const TreeImpl = forwardedRefGeneric(function TreeImpl<T extends TreeItem>(
    {
        onSelectionChange,
        disabled,
        selectionMode = 'single',
        className,
        style,
        expandedKeys,
        onExpandedChange,
        selection,
        defaultSelection,
        dragAndDropHooks,
        ...props
    }: TreeProps<T> & {
        /**
         * The setup for the drag and drop.
         */
        dragAndDropHooks?: DragAndDropHooks | undefined;
    },
    ref?: React.Ref<HTMLDivElement>,
) {
    const { value } = React.useContext(SearchContext);
    const mergedStyles = useMergedStyles(
        className,
        style,
        stylex.props(styles.tree),
    );

    return (
        <Virtualizer
            layout={ListLayout}
            layoutOptions={{ estimatedRowHeight: 32 }}
        >
            <ReactAriaTree
                ref={ref}
                {...props}
                {...mergedStyles}
                selectedKeys={selection}
                defaultSelectedKeys={defaultSelection}
                disabledBehavior="all"
                disabledKeys={disabled}
                selectionMode={selectionMode}
                expandedKeys={expandedKeys}
                dragAndDropHooks={dragAndDropHooks}
                onExpandedChange={(keys) =>
                    onExpandedChange?.(Array.from(keys) as string[])
                }
                onSelectionChange={
                    onSelectionChange
                        ? (keys) =>
                              onSelectionChange(
                                  typeof keys === 'string'
                                      ? keys
                                      : (Array.from(keys) as string[]),
                              )
                        : undefined
                }
                renderEmptyState={() => {
                    if (value !== '') {
                        return (
                            <div {...stylex.props(styles.empty)}>
                                <SingleLine variant="secondary">
                                    No results found
                                </SingleLine>
                            </div>
                        );
                    }

                    return null;
                }}
            />
        </Virtualizer>
    );
});

interface TreeItemBaseProps {
    /**
     * The label of the tree item.
     */
    label: string;
    /**
     * The children of the tree item.
     */
    children?: React.ReactNode | undefined;
    /**
     * The icon of the tree item.
     */
    icon?: IconType | undefined;
    /**
     * The actions of the tree item.
     */
    actions?: React.ReactNode | undefined;
    /**
     * The id of the tree item.
     */
    id?: string | undefined;
    /**
     * The variant of the tree item.
     */
    variant?: 'regular' | 'checkbox' | undefined;
    /**
     * The disabled state of the tree item.
     */
    disabled?: boolean | undefined;
}

type TreeItemProps = TreeItemBaseProps &
    (
        | {
              /**
               * The variant of the tree item.
               */
              variant?: 'regular' | undefined;
              /**
               * Whether the checkbox is in an indeterminate state.
               * This overrides the appearance of the `Checkbox`, whether selection is controlled or uncontrolled.
               * It is up to you to manage the state updates via the `onCheckedChange` prop.
               */
              isIndeterminate?: never | undefined;
          }
        | {
              /**
               * The variant of the tree item.
               */
              variant?: 'checkbox' | undefined;
              /**
               * Whether the checkbox is in an indeterminate state.
               * This overrides the appearance of the `Checkbox`, whether selection is controlled or uncontrolled.
               * It is up to you to manage the state updates via the `onCheckedChange` prop.
               */
              isIndeterminate?: boolean | undefined;
          }
    );

/**
 *
 */
function TreeItemLabel({
    children,
}: {
    /**
     * The label of the tree item.
     */
    children: string;
}) {
    const id = useId();
    const paragraphStyles = useTypeRamp('labelSmall');

    return (
        <OverflowTooltip.Text {...stylex.props(paragraphStyles)}>
            <HighlightedText data-highlight-id={id}>{children}</HighlightedText>
        </OverflowTooltip.Text>
    );
}

const TreeSubItemContext = React.createContext(0);

const TreeItem = ({
    label,
    children,
    actions,
    icon: IconComponent,
    id,
    variant = 'regular',
    isIndeterminate,
    disabled,
}: TreeItemProps) => {
    const level = React.useContext(TreeSubItemContext) || 0;

    return (
        <ReactAriaTreeItem
            textValue={label}
            id={id || label}
            key={id || label}
            isDisabled={disabled}
            value={{ id: id || label }}
            {...stylex.props(styles.itemWrapper)}
        >
            <ReactAriaTreeItemContent>
                {({ isDropTarget, allowsDragging, isDisabled }) => {
                    return (
                        <div
                            {...stylex.props(
                                styles.item,
                                level !== 0 && styles.subItem,
                                isDropTarget && styles.dropTargetOutline,
                                isDisabled && styles.disabledWrapper,
                            )}
                        >
                            {allowsDragging && (
                                <Button
                                    slot="drag"
                                    {...stylex.props(styles.dragButton)}
                                />
                            )}

                            {level !== 0 && (
                                <div {...stylex.props(styles.lines)}>
                                    {Array.from({ length: level }).map(
                                        (_, i) => (
                                            <div
                                                key={`line-${i}`}
                                                {...stylex.props(styles.line)}
                                            />
                                        ),
                                    )}
                                </div>
                            )}
                            <OverflowTooltip.Wrapper position="right">
                                <Flex
                                    gap="0x"
                                    align="center"
                                    {...stylex.props(styles.itemContent)}
                                >
                                    {React.Children.count(children) > 0 ? (
                                        <Button
                                            slot="chevron"
                                            {...stylex.props(
                                                styles.groupCollapse,
                                            )}
                                            excludeFromTabOrder
                                        >
                                            <IconContextProvider>
                                                <ChevronRightSmallIcon />
                                            </IconContextProvider>
                                        </Button>
                                    ) : (
                                        <div {...stylex.props(styles.spacer)} />
                                    )}
                                    <Flex
                                        inline
                                        gap="1x"
                                        align="center"
                                        {...stylex.props(styles.stretch)}
                                    >
                                        {variant === 'checkbox' && (
                                            <CheckboxContext slot="selection">
                                                <Checkbox
                                                    aria-label={label}
                                                    isIndeterminate={
                                                        isIndeterminate
                                                    }
                                                />
                                            </CheckboxContext>
                                        )}

                                        {IconComponent && (
                                            <IconContextProvider>
                                                <IconComponent />
                                            </IconContextProvider>
                                        )}
                                        <TreeItemLabel>{label}</TreeItemLabel>
                                    </Flex>
                                    {actions && (
                                        <Flex align="center" gap="0x">
                                            {actions}
                                        </Flex>
                                    )}
                                </Flex>
                            </OverflowTooltip.Wrapper>
                        </div>
                    );
                }}
            </ReactAriaTreeItemContent>
            <TreeSubItemContext.Provider value={level + 1}>
                <Collection>{children}</Collection>
            </TreeSubItemContext.Provider>
        </ReactAriaTreeItem>
    );
};

TreeItem.displayName = 'Tree.Item';

const Footer = ({
    children,
}: {
    /**
     * The children of the footer.
     */
    children?: React.ReactNode | undefined;
}) => {
    return (
        <div {...stylex.props(styles.footer)}>
            <Flex
                justify="between"
                align="center"
                {...stylex.props(styles.footerInner)}
            >
                {children}
            </Flex>
        </div>
    );
};

Footer.displayName = 'Tree.Footer';

interface TreeSearchProps {
    /**
     * The children of the search.
     */
    children?: React.ReactNode | undefined;
}

const SearchContext = React.createContext<{
    /**
     * The value of the search.
     */
    value: string;
    /**
     * The function to call when the value changes.
     */
    onValueChange: (value: string) => void;
}>({
    value: '',
    onValueChange: () => {},
});

const Search = ({ children }: TreeSearchProps) => {
    const { focusProps, isFocusVisible } = useFocusRing();
    const [showInput, setShowInput] = useState(false);
    const { focusWithinProps } = useFocusWithin({
        onBlurWithin: () => setShowInput(false),
    });
    const { value, onValueChange } = React.useContext(SearchContext);

    if (showInput) {
        return (
            <Flex
                {...stylex.props(styles.searchInputWrapper)}
                {...focusWithinProps}
            >
                <TextInput
                    aria-label="Search"
                    value={value}
                    onChange={(e) => onValueChange(e.target.value)}
                    autoFocus
                    {...stylex.props(styles.searchInput)}
                    fullWidth
                />
                {value && (
                    <div {...stylex.props(styles.searchInputClear)}>
                        <IconButton
                            icon={XSmallIcon}
                            aria-label="Clear search"
                            variant="tertiary"
                            size="small"
                            onClick={() => {
                                onValueChange('');
                                setShowInput(false);
                            }}
                        />
                    </div>
                )}
            </Flex>
        );
    }

    return (
        <Flex align="center" gap="1x">
            <button
                type="button"
                {...stylex.props(styles.searchButton)}
                {...focusProps}
                data-focus-visible={isFocusVisible}
                onClick={() => setShowInput(true)}
            >
                <SearchIcon />
                <SingleLine variant="secondary">{value || 'Search'}</SingleLine>
            </button>
            {children}
        </Flex>
    );
};

Search.displayName = 'Tree.Search';

const Wrapper = React.forwardRef(function Wrapper(
    {
        searchValue: valueProp,
        onSearchValueChange,
        defaultSearchValue,
        ...props
    }: {
        /**
         *
         */
        children: React.ReactNode;
    } & Omit<HTMLAttributes<HTMLDivElement>, 'defaultValue'> &
        ControlledComponent<'searchValue', string>,
    ref?: React.Ref<HTMLDivElement>,
) {
    const wrapperRef = React.useRef<HTMLDivElement>(null);
    const mergedRef = useMergedRef(ref, wrapperRef);
    const [value = '', setValue] = useControlledState(
        valueProp,
        defaultSearchValue ?? '',
        onSearchValueChange,
    );

    return (
        <Provider
            values={[[SearchContext, { value, onValueChange: setValue }]]}
        >
            <HighlightedTextProvider wrapperRef={wrapperRef} inputValue={value}>
                <Flex ref={mergedRef} {...props} direction="column" gap="0x" />
            </HighlightedTextProvider>
        </Provider>
    );
});

Wrapper.displayName = 'Tree.Wrapper';

export type { TreeProps, TreeItemProps };
export { Root, TreeItem as Item, Footer, Search, Wrapper };
