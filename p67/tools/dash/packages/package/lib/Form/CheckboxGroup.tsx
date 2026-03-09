import type { HTMLAttributes } from 'react';
import { forwardRef, useContext, useMemo } from 'react';
import { mergeProps } from 'react-aria';
import { CheckboxGroup as AriaCheckboxGroup } from 'react-aria-components';
import { useAriaLabel } from '../internal/hooks/useLabel';
import { Flex } from '../Layout/Flex';
import type { ControlledComponent } from '../main';
import { FieldContext, generateFieldId } from './FormContext';

type CheckboxGroupProps = HTMLAttributes<HTMLDivElement> &
    ControlledComponent<'value', string[]>;

const CheckboxGroup = forwardRef<HTMLDivElement, CheckboxGroupProps>(
    (
        {
            children,
            id: idProp,
            value,
            defaultValue,
            onValueChange,
            'aria-label': ariaLabel,
            'aria-labelledby': ariaLabelledBy,
            ...otherProps
        },
        forwardedRef,
    ) => {
        const fieldContext = useContext(FieldContext);
        const checkboxGroupId = useMemo(
            () => fieldContext?.inputId ?? idProp ?? generateFieldId(),
            [fieldContext, idProp],
        );
        const { ariaLabelProps } = useAriaLabel({
            'aria-label': ariaLabel,
            'aria-labelledby': ariaLabelledBy,
        });

        return (
            <Flex
                ref={forwardedRef}
                direction="column"
                gap="1x"
                id={checkboxGroupId}
                {...mergeProps(otherProps, ariaLabelProps)}
                asChild
            >
                <AriaCheckboxGroup
                    defaultValue={defaultValue}
                    value={value}
                    onChange={onValueChange}
                >
                    {children}
                </AriaCheckboxGroup>
            </Flex>
        );
    },
);

CheckboxGroup.displayName = 'CheckboxGroup';

export type { CheckboxGroupProps };
export { CheckboxGroup };
