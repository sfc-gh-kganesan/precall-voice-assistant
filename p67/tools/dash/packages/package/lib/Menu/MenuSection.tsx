import type { ReactNode } from 'react';
import { forwardRef, useCallback, useState } from 'react';
import { MenuSection as ReactAriaMenuSection } from 'react-aria-components';

import type { Key, Selection } from '../types';
import { devError, devWarning } from '../util/dev-warning';
import {
    MenuCheckboxSelectionContext,
    MenuSectionTypeContext,
} from './MenuCheckboxSelectionContext';

interface MenuSectionBaseProps {
    /**
     * The items in the section.
     */
    children: ReactNode;
}

interface MenuSectionRadioProps extends MenuSectionBaseProps {
    /**
     * The type of the section.
     */
    variant: 'radio';
    /** The selected radio item. */
    value: string | undefined;
    /** The callback to call when the selected radio item changes. */
    onValueChange: (value?: string) => void;
}

const MenuSectionRadio = forwardRef<
    HTMLDivElement,
    Omit<MenuSectionRadioProps, 'type'>
>(function MenuSectionRadio({ value, onValueChange, ...props }, ref) {
    const onSelectionChange = useCallback(
        (keys: Selection) => {
            if (keys === 'all') {
                devError('All is not a valid value for a radio section');
            } else {
                onValueChange(
                    Array.from(keys.values())[0] as string | undefined,
                );
            }
        },
        [onValueChange],
    );

    return (
        <ReactAriaMenuSection
            {...props}
            ref={ref}
            selectionMode="single"
            selectedKeys={value ? [value] : undefined}
            onSelectionChange={onSelectionChange}
        />
    );
});

interface MenuSectionCheckboxProps extends MenuSectionBaseProps {
    /**
     * The type of the section.
     */
    variant: 'checkbox';
}

const MenuSectionCheckbox = forwardRef<
    HTMLDivElement,
    Omit<MenuSectionCheckboxProps, 'type'>
>(function MenuSectionCheckbox(props, ref) {
    // React aria wants to set up the checkbox state only at the section level.
    // Here we still let the item manage that but update this shared state in the
    // background.
    const [checked, setChecked] = useState<Set<Key>>(new Set());

    return (
        <MenuCheckboxSelectionContext checked={checked} setChecked={setChecked}>
            <ReactAriaMenuSection
                {...props}
                ref={ref}
                selectionMode="multiple"
                selectedKeys={checked}
                onSelectionChange={(v) => {
                    if (v === 'all') {
                        devWarning(
                            'All is not a valid value for a checkbox section',
                        );
                    } else {
                        setChecked(v);
                    }
                }}
            />
        </MenuCheckboxSelectionContext>
    );
});

interface MenuSectionNoTypeProps extends MenuSectionBaseProps {
    /** The type of the section. */
    variant?: never | undefined;
}

type MenuSectionProps =
    | MenuSectionRadioProps
    | MenuSectionCheckboxProps
    | MenuSectionNoTypeProps;

/**
 * A section of a menu.
 */
const MenuSection = forwardRef<HTMLDivElement, MenuSectionProps>(
    function MenuSection({ variant, ...props }, ref) {
        if (variant === 'radio') {
            return (
                <MenuSectionTypeContext type="radio">
                    <MenuSectionRadio
                        {...(props as MenuSectionRadioProps)}
                        ref={ref}
                    />
                </MenuSectionTypeContext>
            );
        }

        if (variant === 'checkbox') {
            return (
                <MenuSectionTypeContext type="checkbox">
                    <MenuSectionCheckbox
                        {...(props as MenuSectionCheckboxProps)}
                        ref={ref}
                    />
                </MenuSectionTypeContext>
            );
        }

        return (
            <MenuSectionTypeContext type={undefined}>
                <ReactAriaMenuSection
                    {...(props as MenuSectionNoTypeProps)}
                    ref={ref}
                />
            </MenuSectionTypeContext>
        );
    },
);

MenuSection.displayName = 'Menu.Section';

export type { MenuSectionProps };
export { MenuSection };
