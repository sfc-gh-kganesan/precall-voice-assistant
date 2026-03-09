import { useControlledState } from '@react-stately/utils';
import { SearchIcon } from '@snowflake/stellar-icons';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { HTMLAttributes } from 'react';
import { forwardRef, useState } from 'react';
import { mergeProps, useFocusWithin, useHover } from 'react-aria';

import type { ComboBoxProps } from '../ComboBox';
import { ComboBox } from '../ComboBox';
import { Divider as DividerPrimitive } from '../Divider';
import { useMergedStyles } from '../hooks';
import { Flex } from '../Layout';
import type { ListboxOptionProps } from '../Listbox/ListboxOption';
import type {
    ControlledValueComponent,
    LabelProps,
    SlottedDivContainerProps,
} from '../main';
import type { SearchInputProps } from '../SearchInput/SearchInput';
import { SearchInput } from '../SearchInput/SearchInput';
import { Label as LabelComponent } from '../Text';
import { ControlBarContext, useControlBarContext } from './ControlBarContext';

const styles = stylex.create({
    left: { flexShrink: 1 },
    right: { flexShrink: 0 },
    divider: {
        alignSelf: 'stretch',
        padding: tokens['space-vertical-sm'],
    },
    clearSearch: {
        alignItems: 'center',
        backgroundColor: 'transparent',
        borderWidth: 0,
        display: 'flex',
        justifyContent: 'center',
        padding: 0,
    },
    search: (activeSearchWidth: number) => ({
        flexShrink: 0,
        minWidth: 'fit-content',
        transition: 'width 150ms ease-in-out',
        width: {
            default: 140,
            ':focus-within': activeSearchWidth,
            ':hover': activeSearchWidth,
        },
    }),
    searchWrapper: (activeSearchWidth: number) => ({
        display: 'flex',
        minWidth: 'fit-content',
        width: activeSearchWidth,
    }),
    searchWrapperLeft: {
        justifyContent: 'flex-start',
    },
    searchWrapperRight: {
        justifyContent: 'flex-end',
    },
});

interface ControlBarProps extends HTMLAttributes<HTMLDivElement> {
    /**
     * Associates the control bar with the element it controls.
     * The value should be an ID of an element that the control bar controls.
     */
    'aria-controls': string;
}

const Root = forwardRef<HTMLDivElement, ControlBarProps>(
    function ControlBar(props, ref) {
        return <Flex ref={ref} justify="between" {...props} />;
    },
);

Root.displayName = 'ControlBar.Root';

const Left = forwardRef(function ControlBarLeft(
    { className, style, ...props }: SlottedDivContainerProps,
    ref?: React.Ref<HTMLDivElement>,
) {
    const mergedStyles = useMergedStyles(
        className,
        style,
        stylex.props(styles.left),
    );

    return (
        <ControlBarContext side="left">
            <Flex
                ref={ref}
                align="center"
                wrap="wrap"
                {...props}
                {...mergedStyles}
            />
        </ControlBarContext>
    );
});

Left.displayName = 'ControlBar.Left';

const Right = forwardRef(function ControlBarRight(
    { className, style, ...props }: SlottedDivContainerProps,
    ref?: React.Ref<HTMLDivElement>,
) {
    const mergedStyles = useMergedStyles(
        className,
        style,
        stylex.props(styles.right),
    );

    return (
        <ControlBarContext side="right">
            <Flex
                ref={ref}
                align="start"
                justify="end"
                {...props}
                {...mergedStyles}
            />
        </ControlBarContext>
    );
});

Right.displayName = 'ControlBar.Right';

const Divider = forwardRef(function ControlBarDivider(
    props: SlottedDivContainerProps,
    ref?: React.Ref<HTMLHRElement>,
) {
    return (
        <Flex {...props} {...stylex.props(styles.divider)}>
            <DividerPrimitive ref={ref} direction="vertical" />
        </Flex>
    );
});

Divider.displayName = 'ControlBar.Divider';

const Label = forwardRef(function ControlBarLabel(
    props: Omit<LabelProps, 'variant'>,
    ref?: React.Ref<HTMLLabelElement>,
) {
    return <LabelComponent variant="secondary" ref={ref} {...props} />;
});

Label.displayName = 'ControlBar.Label';

interface SearchProps extends SearchInputProps {
    /**
     * The width of the search input when it is active.
     */
    activeSearchWidth?: number | undefined;
    /**
     * The placeholder of the search input when it is active.
     */
    activeSearchPlaceholder?: string | undefined;
}

const Search = forwardRef<HTMLDivElement, SearchProps>(function Search(
    {
        placeholder = 'Search',
        onValueChange: onValueChangeProp,
        value: valueProp,
        defaultValue: defaultValueProp,
        activeSearchWidth = 240,
        activeSearchPlaceholder = 'Search',
        ...props
    },
    ref,
) {
    const [isActive, setIsActive] = useState(false);
    const { focusWithinProps } = useFocusWithin({
        onFocusWithinChange: setIsActive,
    });
    const { isHovered, hoverProps } = useHover({});
    const [searchValue, setSearchValue] = useControlledState(
        valueProp,
        defaultValueProp || '',
        onValueChangeProp,
    );
    const { side } = useControlBarContext('search');

    return (
        <div
            {...stylex.props(
                styles.searchWrapper(activeSearchWidth),
                side === 'left'
                    ? styles.searchWrapperLeft
                    : styles.searchWrapperRight,
            )}
        >
            <SearchInput
                ref={ref}
                placeholder={
                    isActive || isHovered
                        ? activeSearchPlaceholder
                        : placeholder
                }
                value={searchValue}
                onValueChange={setSearchValue}
                {...mergeProps(props, focusWithinProps, hoverProps)}
                {...stylex.props(styles.search(activeSearchWidth))}
            />
        </div>
    );
});

Search.displayName = 'ControlBar.Search';

interface SearchListProps
    extends ComboBoxProps,
        ControlledValueComponent<string> {
    /**
     * The label of the search list.
     */
    'aria-label': string;
    /**
     * The width of the search input when it is active.
     */
    activeSearchWidth?: number | undefined;
    /**
     * The placeholder of the search input when it is active.
     */
    activeSearchPlaceholder?: string | undefined;
}

const SearchList = forwardRef<HTMLDivElement, SearchListProps>(function Search(
    {
        placeholder = 'Search',
        value: valueProp,
        defaultValue: defaultValueProp,
        onValueChange: onValueChangeProp,
        activeSearchWidth = 240,
        activeSearchPlaceholder = 'Search',
        ...props
    },
    ref,
) {
    const [isActive, setIsActive] = useState(false);
    const { focusWithinProps } = useFocusWithin({
        onFocusWithinChange: setIsActive,
    });
    const { isHovered, hoverProps } = useHover({});
    const [searchValue, setSearchValue] = useControlledState(
        valueProp,
        defaultValueProp || '',
        onValueChangeProp,
    );
    const { side } = useControlBarContext('search');

    return (
        <div
            {...stylex.props(
                styles.searchWrapper(activeSearchWidth),
                side === 'left'
                    ? styles.searchWrapperLeft
                    : styles.searchWrapperRight,
            )}
        >
            <ComboBox.Root
                ref={ref}
                icon={SearchIcon}
                placeholder={
                    isActive || isHovered
                        ? activeSearchPlaceholder
                        : placeholder
                }
                value={searchValue}
                onValueChange={setSearchValue}
                {...stylex.props(styles.search(activeSearchWidth))}
                {...mergeProps(props, focusWithinProps, hoverProps)}
            />
        </div>
    );
});

SearchList.displayName = 'ControlBar.Search';

const SearchOption = forwardRef<HTMLLIElement, ListboxOptionProps>(
    function SearchOption(props, ref) {
        return <ComboBox.Option {...props} ref={ref} />;
    },
);

SearchOption.displayName = 'ControlBar.SearchOption';

export type { ControlBarProps };
export { Root, Left, Right, Divider, Label, Search, SearchList, SearchOption };
