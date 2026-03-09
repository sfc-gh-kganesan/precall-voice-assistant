import { Slottable } from '@radix-ui/react-slot';
import type { BaseCollection } from '@react-aria/collections';
import type { Node } from '@react-types/shared';
import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { ChevronRightSmallIcon } from '@snowflake/stellar-icons';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { HTMLAttributes } from 'react';
import {
    Children,
    createContext,
    forwardRef,
    isValidElement,
    useContext,
    useRef,
} from 'react';
import { usePress } from 'react-aria';
import {
    Breadcrumb as BreadcrumbItem,
    Breadcrumbs as BreadcrumbRoot,
    Collection,
    CollectionBuilder,
    Dialog,
    DialogTrigger,
    ListBoxItem,
    Popover,
} from 'react-aria-components';

import translations from '../../translations/base.json';
import { useMergedStyles } from '../hooks';
import { useTypeRamp } from '../internal/hooks/useTypeRamp';
import { ScreenReaderOnly } from '../internal/ScreenReaderOnly/ScreenReaderOnly';
import { SharedItem } from '../internal/SharedItem/SharedItem';
import { levelStyles } from '../internal/utils/levelStyles';
import { Listbox } from '../Listbox';
import type {
    SlottedButtonContainerProps,
    SlottedLiContainerProps,
} from '../main';
import { BaltoThemeProvider, SlottedContainer } from '../main';

const ShowChevronContext = createContext(true);

const styles = stylex.create({
    root: {
        display: 'flex',
        flexDirection: 'row',
        gap: tokens['space-gap-2xs'],
        padding: 0,
    },
    list: {
        minWidth: 200,
    },
    itemWrapper: {
        flexShrink: 0,
        listStyle: 'none',

        // TOOD(APPS-55669)

        '--breadcrumb-text-color': {
            default: baltoTheme.reusableTextSecondary,
            ":is([data-current='true'])": baltoTheme.reusableTextPrimary,
            ':hover:not(:disabled)': baltoTheme.reusableTextPrimary,
            ':active:not(:disabled)': baltoTheme.reusableTextSecondary,
            ':disabled': baltoTheme.reusableDisabledText,
        },
    },
    item: {
        alignItems: 'center',
        backgroundColor: 'transparent',
        borderWidth: 0,
        color: 'var(--breadcrumb-text-color)',
        cursor: {
            default: 'pointer',
            ':disabled': 'not-allowed',
        },
        display: 'flex',
        gap: tokens['space-gap-2xs'],
        padding: 0,
        textDecoration: 'none',
        userSelect: 'none',
    },
    icon: {
        alignItems: 'center',
        display: 'flex',
        height: tokens['size-2xs'],
        justifyContent: 'center',
        width: tokens['size-2xs'],
    },
    ellipsis: {
        backgroundColor: 'transparent',
        borderWidth: 0,
        color: baltoTheme.reusableTextSecondary,
        padding: 0,
    },
});

interface BreadcrumbsCollectionProps
    extends Omit<HTMLAttributes<HTMLOListElement>, 'aria-label'> {
    /**
     * The collection of breadcrumbs.
     */
    collection: BaseCollection<object>;
    /**
     * The aria-label of the breadcrumbs.
     */
    'aria-label': string;
}

const nodeToText = (node: React.ReactNode): string => {
    const text = Children.toArray(node).map((child) => {
        if (typeof child === 'string') return child;
        if (typeof child === 'number') return String(child);
        if (isValidElement(child)) {
            return child.props.children ? nodeToText(child.props.children) : '';
        }
        return '';
    });
    return text.join('');
};

const BreadcrumbsCollection = forwardRef<
    HTMLOListElement,
    BreadcrumbsCollectionProps
>(function Button(
    {
        className,
        style,
        collection,
        children,
        'aria-label': ariaLabel,
        ...props
    },
    ref?,
) {
    const styleProps = useMergedStyles(
        className,
        style,
        stylex.props(styles.root),
    );

    // If the collection is small render all the children
    if (collection.size <= 4) {
        return (
            <BreadcrumbRoot ref={ref} {...styleProps} {...props}>
                {children}
            </BreadcrumbRoot>
        );
    }

    const items = Array.from(collection.getKeys())
        .map((k) => collection.getItem(k))
        .filter((i): i is Node<object> => Boolean(i));
    const firstItem = items[0];
    const last3Items = items.slice(-3);
    const middleItems = items.slice(1, -3);

    return (
        <DialogTrigger>
            <BreadcrumbRoot ref={ref} {...styleProps} {...props}>
                <BreadcrumbItem {...firstItem?.props} />
                <OverflowItem />
                {last3Items?.map((item) => (
                    <BreadcrumbItem key={item?.key} {...item?.props} />
                ))}
            </BreadcrumbRoot>

            <ShowChevronContext.Provider value={false}>
                <Popover>
                    <BaltoThemeProvider>
                        <Dialog {...stylex.props(levelStyles.level3Surface)}>
                            <Listbox.Root
                                items={middleItems}
                                aria-label={ariaLabel}
                                {...stylex.props(styles.list)}
                            >
                                {(item) => {
                                    const textValue = nodeToText(
                                        item.props.children({
                                            isCurrent: false,
                                        }),
                                    );

                                    return (
                                        <SharedItem.Wrapper
                                            asChild
                                            {...(props as SlottedLiContainerProps)}
                                        >
                                            <ListBoxItem textValue={textValue}>
                                                <SharedItem.Label
                                                    label={textValue}
                                                />
                                            </ListBoxItem>
                                        </SharedItem.Wrapper>
                                    );
                                }}
                            </Listbox.Root>
                        </Dialog>
                    </BaltoThemeProvider>
                </Popover>
            </ShowChevronContext.Provider>
        </DialogTrigger>
    );
});

/**
 * An item that is used to represent the overflow of the breadcrumbs.
 */
function OverflowItem() {
    const ref = useRef<HTMLButtonElement>(null);
    const { pressProps } = usePress({ ref });
    const itemTextStyle = useTypeRamp('paragraph');

    return (
        <Item
            {...stylex.props(styles.ellipsis, itemTextStyle)}
            ref={ref}
            {...pressProps}
        >
            <ScreenReaderOnly>
                {translations.en['ellipsis']['aria-label']}
            </ScreenReaderOnly>
            <span aria-hidden="true">...</span>
        </Item>
    );
}

interface BreadcrumbsRootProps
    extends Omit<HTMLAttributes<HTMLOListElement>, 'aria-label'> {
    /** An aria-label for the ellipses overflow menu. */
    'aria-label': string;
}

const Root = forwardRef<HTMLOListElement, BreadcrumbsRootProps>(
    function Breadcrumbs(props, ref?) {
        // Use the colleciton builder to get the full collection so we can render "..."
        // when there are more than 4 items.
        return (
            <CollectionBuilder
                content={<Collection>{props.children}</Collection>}
            >
                {(collection) => (
                    <BreadcrumbsCollection
                        ref={ref}
                        collection={collection}
                        {...props}
                    />
                )}
            </CollectionBuilder>
        );
    },
);

Root.displayName = 'Breadcrumbs.Root';

/**
 * A component that renders a chevron icon.
 */
function Chevron() {
    const showChevron = useContext(ShowChevronContext);
    if (!showChevron) return null;
    return <ChevronRightSmallIcon />;
}

const Item = forwardRef<HTMLButtonElement, SlottedButtonContainerProps>(
    function Item({ className, style, children, ...props }, ref?) {
        const itemTextStyle = useTypeRamp('paragraph');

        return (
            <BreadcrumbItem {...stylex.props(styles.itemWrapper)}>
                {({ isCurrent }) => {
                    return (
                        <SlottedContainer
                            className={className}
                            style={style}
                            stylexProps={stylex.props(
                                styles.item,
                                itemTextStyle,
                            )}
                            tag="button"
                            ref={ref}
                            {...props}
                        >
                            <Slottable>{children}</Slottable>
                            {!isCurrent && <Chevron />}
                        </SlottedContainer>
                    );
                }}
            </BreadcrumbItem>
        );
    },
);

Item.displayName = 'Breadcrumbs.Item';

export { Root, Item };
