import type { HTMLAttributes } from 'react';
import { forwardRef, useContext, useMemo } from 'react';
import { type AriaRadioGroupProps, mergeProps } from 'react-aria';
import { RadioGroup as AriaRadioGroup } from 'react-aria-components';
import { useAriaLabel } from '../internal/hooks/useLabel';
import { Flex } from '../Layout/Flex';
import { FieldContext, generateFieldId } from './FormContext';
import { RadioGroupContext } from './RadioGroupContext';
import { RadioGroupItem } from './RadioGroupItem';

interface RadioGroupProps
    extends Omit<
            HTMLAttributes<HTMLDivElement>,
            'onChange' | 'onFocus' | 'onBlur'
        >,
        Partial<Pick<AriaRadioGroupProps, 'onFocus' | 'onBlur'>> {
    /**
     * The default value of the radio group.
     */
    defaultValue?: string | undefined;
    /**
     * The value of the radio group.
     */
    value?: string | undefined;
    /**
     * Whether the radio group is disabled.
     * @default false
     */
    disabled?: boolean | undefined;
    /**
     * The callback function that is called when the value of the radio group changes.
     */
    onValueChange?: ((value: string) => void) | undefined;
    // div doesn't have name/required props so we need to pass them to the Radix component
    /**
     * The name of the radio group.
     */
    name?: string | undefined;
    /**
     * Whether the radio group is required.
     * @default false
     */
    required?: boolean | undefined;
}

const RadioGroupComponent = forwardRef<HTMLDivElement, RadioGroupProps>(
    (props, forwardedRef) => {
        const {
            children,
            required,
            name,
            disabled,
            value,
            defaultValue,
            onValueChange,
            'aria-label': ariaLabel,
            'aria-labelledby': ariaLabelledBy,
            id: idProp,
            ...otherProps
        } = props;
        const fieldContext = useContext(FieldContext);
        const radioGroupId = useMemo(
            () => fieldContext?.inputId ?? idProp ?? generateFieldId(),
            [fieldContext, idProp],
        );
        const { ariaLabelProps } = useAriaLabel({
            'aria-label': ariaLabel,
            'aria-labelledby': ariaLabelledBy,
        });

        return (
            <RadioGroupContext.Provider value={{ disabled }}>
                <Flex direction="column" gap="1x" asChild>
                    <AriaRadioGroup
                        ref={forwardedRef}
                        name={name}
                        isRequired={required}
                        isDisabled={disabled}
                        value={value}
                        defaultValue={defaultValue}
                        onChange={(value) => onValueChange?.(value)}
                        id={radioGroupId}
                        {...mergeProps(otherProps, ariaLabelProps)}
                    >
                        {children}
                    </AriaRadioGroup>
                </Flex>
            </RadioGroupContext.Provider>
        );
    },
);

RadioGroupComponent.displayName = 'RadioGroup.Root';

export type { RadioGroupProps };
export type { RadioGroupItemProps } from './RadioGroupItem';
export { RadioGroupComponent as Root, RadioGroupItem as Item };
