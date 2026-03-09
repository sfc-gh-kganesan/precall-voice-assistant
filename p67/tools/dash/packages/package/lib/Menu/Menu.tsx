import { createLeafComponent } from '@react-aria/collections';
import { useControlledState } from '@react-stately/utils';
import * as stylex from '@stylexjs/stylex';
import type {
    DOMAttributes,
    ForwardedRef,
    ReactElement,
    ReactNode,
} from 'react';
import { forwardRef, useContext, useState } from 'react';
import {
    MenuStateContext,
    Popover,
    Menu as ReactAriaMenu,
    MenuTrigger as ReactAriaMenuTrigger,
} from 'react-aria-components';
import { BaltoThemeProvider } from '../BaltoProvider/BaltoProvider';
import type { LoadingSentinelProps } from '../internal/LoaderIndicator';
import { LoaderIndicator, LoadingSentinel } from '../internal/LoaderIndicator';
import { levelStyles } from '../internal/utils/levelStyles';
import type { ListboxLoaderIndicatorProps } from '../Listbox';
import type { Direction, PopoverAlign, PopoverPosition } from '../main';
import type { FocusableElement } from '../types';
import type { ControlledOpenComponent } from '../util/Controlled';
import { positionToPlacement } from '../util/positionToPlacement';
import { AutoFocusContext } from './AutoFocusContext';
import { menuStyles } from './internal/menuStyles';
import { MenuDivider } from './MenuDivider';
import { MenuItem } from './MenuItem';
import { MenuSection } from './MenuSection';
import { MenuSectionHeader } from './MenuSectionHeader';
import { MenuSub } from './MenuSub';
import { MenuTrigger } from './MenuTrigger';

interface MenuProps extends ControlledOpenComponent {
    /**
     * The trigger of the menu.
     *
     * > NOTE: If you are passing a component as the trigger, it must correctly
     * > spread all the props passed to it to a DOM element and forward a ref.
     */
    trigger: ReactElement<DOMAttributes<FocusableElement>, string>;
    /**
     * The children of the menu.
     */
    children: ReactNode;
    /**
     * The direction of the menu.
     */
    dir?: Direction | undefined;
    /**
     * The alignment of the menu.
     * @default "start"
     */
    align?: PopoverAlign | undefined;
    /**
     * The position of the menu.
     * @default "bottom"
     */
    position?: PopoverPosition | undefined;
    /**
     * Whether the menu should match the width of the trigger.
     * @default false
     */
    matchTriggerWidth?: boolean | undefined;
    /** Control the width of the list of options */
    maxListWidth?: string | number | undefined;
}

const MenuComponent = forwardRef<HTMLDivElement, MenuProps>(
    (props, forwardedRef) => {
        const {
            open: openProp,
            defaultOpen,
            onOpenChange,
            trigger,
            align = 'start',
            position = 'bottom',
            matchTriggerWidth,
            maxListWidth,
            ...otherProps
        } = props;
        const [shouldAutoFocusOnClose, setShouldAutoFocusOnClose] =
            useState(true);
        const [open, setOpen] = useControlledState(
            openProp,
            defaultOpen ?? false,
            onOpenChange,
        );

        return (
            <AutoFocusContext
                shouldAutoFocusOnClose={shouldAutoFocusOnClose}
                setShouldAutoFocusOnClose={setShouldAutoFocusOnClose}
            >
                <ReactAriaMenuTrigger isOpen={open} onOpenChange={setOpen}>
                    <MenuTrigger>{trigger}</MenuTrigger>

                    <Popover
                        placement={positionToPlacement(position, align)}
                        offset={8}
                        containerPadding={8}
                        {...stylex.props(
                            menuStyles.menuPopover,
                            levelStyles.level3Surface,
                        )}
                    >
                        <BaltoThemeProvider>
                            <ReactAriaMenu
                                ref={forwardedRef}
                                {...otherProps}
                                {...stylex.props(
                                    menuStyles.menuContainer,
                                    matchTriggerWidth &&
                                        menuStyles.menuContainerMatchTriggerWidth,
                                    typeof maxListWidth !== 'undefined' &&
                                        menuStyles.menuContainerMaxListWidth(
                                            maxListWidth,
                                        ),
                                )}
                            />
                        </BaltoThemeProvider>
                    </Popover>
                </ReactAriaMenuTrigger>
            </AutoFocusContext>
        );
    },
);
MenuComponent.displayName = 'Menu.Root';

const MenuLoaderIndicator = createLeafComponent(
    'loader',
    function MenuLoaderIndicator(
        props: ListboxLoaderIndicatorProps &
            Pick<LoadingSentinelProps, 'onLoadMore'> & {
                /**
                 * An accessible label for the loading indicator.
                 */
                'aria-label'?: string | undefined;
            },
        ref: ForwardedRef<HTMLDivElement>,
    ) {
        // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
        const state = useContext(MenuStateContext)!;
        const {
            isLoading,
            onLoadMore,
            label,
            'aria-label': ariaLabel = 'Loading more options',
            ...rest
        } = props;

        if (!isLoading) {
            return null;
        }

        return (
            <div {...rest} tabIndex={-1} role="menuitem" ref={ref}>
                <LoadingSentinel
                    onLoadMore={onLoadMore}
                    collection={state.collection}
                />
                <LoaderIndicator aria-label={ariaLabel} label={label} />
            </div>
        );
    },
);

// eslint-disable-next-line @typescript-eslint/no-explicit-any
(MenuLoaderIndicator as any).displayName = 'Menu.LoadingIndicator';

export type { MenuProps };
export type { MenuDividerProps } from './MenuDivider';
export type { MenuItemProps } from './MenuItem';
export type { MenuSectionHeaderProps } from './MenuSectionHeader';
export type { MenuSubProps } from './MenuSub';
export {
    MenuComponent as Root,
    MenuItem as Item,
    MenuSub as Sub,
    MenuDivider as Divider,
    MenuSectionHeader as SectionHeader,
    MenuSection as Section,
    MenuLoaderIndicator as LoadingIndicator,
};
