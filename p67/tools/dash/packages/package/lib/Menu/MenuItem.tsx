import { useId, useLayoutEffect } from '@react-aria/utils';
import type { HTMLAttributes } from 'react';
import { forwardRef, useCallback } from 'react';
import { MenuItem as ReactAriaMenuItem } from 'react-aria-components';
import type {
    SharedItemLabelProps,
    SharedItemSuffix,
} from '../internal/SharedItem/SharedItem';
import { SharedItem } from '../internal/SharedItem/SharedItem';
import { devError, devWarning } from '../util/dev-warning';
import { useAutoFocusContext } from './AutoFocusContext';
import {
    useMenuCheckboxSelectionContext,
    useMenuSectionTypeContext,
} from './MenuCheckboxSelectionContext';

interface MenuItemProps
    extends Omit<
            HTMLAttributes<HTMLLIElement>,
            'onSelect' | 'onAbort' | 'children' | 'onClick'
        >,
        Pick<
            SharedItemLabelProps,
            'label' | 'subLabel' | 'disabled' | 'prefixIcon' | 'selected'
        > {
    /**
     * The function to handle the selection of the menu item.
     */
    onSelect?: (() => void) | undefined;
    /**
     * The suffix of the menu item.
     */
    suffix?: SharedItemSuffix | undefined;
    /**
     * The variant of the menu item.
     * @default "default"
     */
    variant?: 'critical' | 'default' | undefined;
    /**
     * Whether the menu should auto focus on the trigger once closed.
     * @default true
     */
    shouldAutoFocusOnSelect?: boolean | undefined;
    /**
     * Whether the menu should close when the item is selected.
     */
    shouldCloseMenuOnSelect?: boolean | undefined;
}

const MenuItem = forwardRef<HTMLLIElement, MenuItemProps>(
    (props, forwardedRef) => {
        const {
            label,
            subLabel,
            disabled,
            selected,
            prefixIcon: PrefixIcon,
            onSelect: onSelectProp,
            suffix,
            variant = 'default',
            shouldAutoFocusOnSelect = true,
            shouldCloseMenuOnSelect = true,
            id: propId,
            ...otherProps
        } = props;
        const generatedId = useId();
        const id = propId ?? generatedId;
        const { setShouldAutoFocusOnClose } = useAutoFocusContext('MenuItem');
        const { setChecked } = useMenuCheckboxSelectionContext('MenuItem');
        const { type: sectionType } = useMenuSectionTypeContext('MenuItem');

        if (typeof selected === 'boolean') {
            // It will still work without a section type, but we want to warn the dev
            // that they are doing something wrong. And push them to a more accessible
            // pattern.
            if (!sectionType) {
                devWarning(
                    'Menu.Item with selected prop used without a Menu.Section w/type=checkbox. Please wrap this Menu.Item in a Menu.Section.',
                );
            }

            // Without an id the dev has no way to match the id with an item.
            if (!propId && sectionType === 'radio') {
                devError(
                    'Radio Menu.Item must have an id. Please provide an id to the Menu.Item.',
                );
            }
        }

        const onSelect = useCallback(() => {
            // Here we are not using the disabled prop because that makes the item unfocusable
            // If the dev wants to show a tooltip, they cannot do so in a way that is accessible.
            // To get around this, we are disabling it via e.preventDefault() and attrs on the wrapper.
            // This emulates what disabled is, but allows a keyboard user to focus the item and see the tooltip.
            if (disabled) {
                return;
            }

            setShouldAutoFocusOnClose(shouldAutoFocusOnSelect);
            onSelectProp?.();
        }, [
            disabled,
            onSelectProp,
            setShouldAutoFocusOnClose,
            shouldAutoFocusOnSelect,
        ]);

        useLayoutEffect(() => {
            if (!id) {
                return;
            }

            setChecked?.((prev) => {
                if (selected) {
                    prev.add(id);
                } else {
                    prev.delete(id);
                }

                return prev;
            });
        }, [id, selected, setChecked]);

        return (
            <SharedItem.Wrapper ref={forwardedRef} {...otherProps} asChild>
                <ReactAriaMenuItem
                    onAction={onSelect}
                    isDisabled={disabled}
                    // @ts-expect-error - This prop works but is not exposed
                    closeOnSelect={shouldCloseMenuOnSelect}
                    id={id}
                >
                    {({ isSelected }) => {
                        return (
                            <SharedItem.Label
                                label={label}
                                subLabel={subLabel}
                                disabled={disabled}
                                selected={selected || isSelected}
                                prefixIcon={PrefixIcon}
                                suffix={suffix}
                                variant={variant}
                            />
                        );
                    }}
                </ReactAriaMenuItem>
            </SharedItem.Wrapper>
        );
    },
);

MenuItem.displayName = 'Menu.Item';
export type { MenuItemProps };
export { MenuItem };
