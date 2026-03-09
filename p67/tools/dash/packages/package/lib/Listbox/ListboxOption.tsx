import type React from 'react';
import { forwardRef, useMemo } from 'react';
import { useId } from 'react-aria';
import type { ListBoxItemProps } from 'react-aria-components';
import { ListBoxItem } from 'react-aria-components';

import { useHighlightMatch } from '../HighlightedText';
import type {
    SharedItemPrefix,
    SharedItemSuffix,
} from '../internal/SharedItem/SharedItem';
import { SharedItem } from '../internal/SharedItem/SharedItem';
import { useListboxOptionId } from './useListboxSelection';

interface ListboxOptionProps
    extends Omit<React.ComponentProps<'li'>, 'children' | 'value'> {
    /**
     * The label of the option.
     */
    label: string;
    /**
     * The description of the option.
     */
    description?: string | undefined;
    /**
     * The icon of the option.
     */
    icon?: SharedItemPrefix | undefined;
    /**
     * Whether the option is disabled.
     * @default false
     */
    disabled?: boolean | undefined;
    /**
     * The aria-label of the option.
     */
    'aria-label'?: string | undefined;
    /**
     * The aria-labelledby of the option.
     */
    'aria-labelledby'?: string | undefined;
    /**
     * The aria-describedby of the option.
     */
    'aria-describedby'?: string | undefined;
    /**
     * The aria-details of the option.
     */
    'aria-details'?: string | undefined;
    /**
     * The text value of the option.
     */
    textValue?: string | undefined;
    /**
     * The class name of the option.
     */
    className?: string | undefined;
    /**
     * The style of the option.
     */
    style?: React.CSSProperties | undefined;
    /**
     * The id of the option.
     */
    id?: string | undefined;
    /**
     * A component that renders the suffix of the option.
     */
    suffix?: SharedItemSuffix | undefined;
}

const ListboxItemGeneric = forwardRef(function ListboxItemGeneric(
    {
        id: idProp,
        textValue: textValueProp,
        label,
        ...props
    }: ListBoxItemProps<object> & {
        /**
         * The label of the option.
         */
        label: string;
        /**
         * The id of the option.
         */
        id: string | undefined;
    },
    ref?: React.Ref<HTMLLIElement>,
) {
    const genId = useId();
    const id = idProp || label || genId;
    const textValue = textValueProp || label;
    const value = useMemo(
        () => ({ id, label, textValue }),
        [id, label, textValue],
    );

    useHighlightMatch({ labelId: id, label });

    return (
        <ListBoxItem
            ref={ref}
            textValue={textValue}
            data-highlight-id={id}
            id={id}
            value={value}
            {...props}
        />
    );
});

const ListboxOption = forwardRef(function ListboxOption(
    {
        label,
        description,
        icon: Icon,
        disabled,
        'aria-describedby': ariaDescribedBy,
        'aria-details': ariaDetails,
        'aria-label': ariaLabel,
        'aria-labelledby': ariaLabelledBy,
        suffix,
        id: idProp,
        ...props
    }: ListboxOptionProps,
    ref?: React.Ref<HTMLLIElement>,
) {
    const id = useListboxOptionId(idProp, label);

    return (
        <SharedItem.Wrapper asChild>
            <ListboxItemGeneric
                ref={ref}
                {...(props as React.ComponentProps<typeof ListboxItemGeneric>)}
                isDisabled={disabled}
                aria-label={ariaLabel}
                aria-labelledby={ariaLabelledBy}
                aria-describedby={ariaDescribedBy}
                aria-details={ariaDetails}
                label={label}
                id={id}
            >
                {({ isSelected }) => {
                    return (
                        <SharedItem.Label
                            prefixIcon={Icon}
                            label={label}
                            subLabel={description}
                            selected={isSelected}
                            disabled={disabled}
                            suffix={suffix}
                        />
                    );
                }}
            </ListboxItemGeneric>
        </SharedItem.Wrapper>
    );
});

ListboxOption.displayName = 'Listbox.Option';

export type { ListboxOptionProps };
export { ListboxOption, ListboxItemGeneric };
