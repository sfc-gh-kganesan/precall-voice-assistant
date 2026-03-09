import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import {
    CheckBoldIcon,
    IconContextProvider,
    MinusBoldIcon,
} from '@snowflake/stellar-icons';
import * as stylex from '@stylexjs/stylex';
import type { HTMLAttributes } from 'react';
import { forwardRef, useContext, useMemo } from 'react';
import { Checkbox as ReactAriaCheckbox } from 'react-aria-components';
import { Flex } from '../Layout/Flex';
import { Paragraph, SingleLine } from '../Text';
import { Label } from '../Text/Label';
import { useCheckboxContext } from './CheckboxContext';
import { FieldContext, FormContext, generateFieldId } from './FormContext';
import { useCheckboxStyles } from './useCheckboxStyles';

interface CheckboxBaseProps
    extends Omit<HTMLAttributes<HTMLDivElement>, 'onClick'> {
    /**
     * The description of the checkbox.
     */
    description?: string | undefined;
    /**
     * Whether the checkbox is checked by default (uncontrolled).
     * @default false
     */
    defaultChecked?: boolean | undefined;
    /**
     * Whether the checkbox is disabled.
     * @default false
     */
    disabled?: boolean | undefined;
    /**
     * Whether the checkbox is checked. (Controlled)
     * @default false
     */
    checked?: boolean | undefined;
    /**
     * The callback function that is called when the checkbox is checked. (Controlled)
     */
    onCheckedChange?: ((value: boolean) => void) | undefined;
    /**
     * The name of the checkbox. Used to associate the checkbox with a form field.
     */
    name?: string | undefined;
    /**
     * The callback function that is called when the checkbox is clicked.
     */
    onClick?: ((event: React.MouseEvent) => void) | undefined;
    /**
     * Whether the checkbox is in an indeterminate state.
     * This overrides the appearance of the `Checkbox`, whether selection is controlled or uncontrolled.
     * It is up to you to manage the state updates via the `onCheckedChange` prop.
     */
    isIndeterminate?: boolean | undefined;
    /**
     * The value the checkbox is associated with.
     * This is for usage with a CheckboxGroup, otherwise it not needed.
     */
    value?: string | undefined;
}

interface CheckboxWithLabelProps extends CheckboxBaseProps {
    /**
     * The label of the checkbox.
     */
    label: string;
}

interface CheckboxWithAriaLabelProps extends CheckboxBaseProps {
    /**
     * The aria-label of the checkbox.
     */
    'aria-label': string;
    /**
     * The label of the checkbox.
     */
    label?: never | undefined;
}

type CheckboxProps = CheckboxWithLabelProps | CheckboxWithAriaLabelProps;

const styles = stylex.create({
    label: {
        color: baltoTheme.reusableTextPrimary,
        cursor: 'pointer',
    },
    labelDisabled: {
        color: baltoTheme.reusableDisabledText,
        cursor: 'not-allowed',
    },
});

const Checkbox = forwardRef<HTMLDivElement, CheckboxProps>(
    (props, forwardedRef) => {
        const {
            defaultChecked,
            disabled,
            checked,
            onCheckedChange,
            name,
            label,
            'aria-label': ariaLabel,
            isIndeterminate: isIndeterminateProp,
            value,
            ...otherProps
        } = props;

        const formContext = useContext(FormContext);
        const inputId = useMemo(() => generateFieldId(), []);
        const labelId = useMemo(() => generateFieldId(), []);
        const descriptionId = useMemo(() => generateFieldId(), []);
        const checkboxContext = useCheckboxContext('Checkbox');

        const checkboxStyles = useCheckboxStyles();
        const isField = useContext(FieldContext);

        return (
            // Not using SlottedContainer here because this is a leaf element.
            <Flex
                {...otherProps}
                direction="row"
                align={otherProps.description ? 'start' : 'center'}
                gap="1x"
                ref={forwardedRef}
                asChild
            >
                <ReactAriaCheckbox
                    id={inputId}
                    defaultSelected={defaultChecked}
                    isSelected={checked}
                    onChange={onCheckedChange}
                    isDisabled={disabled}
                    name={name}
                    isIndeterminate={isIndeterminateProp}
                    aria-label={ariaLabel ?? label}
                    aria-labelledby={labelId}
                    aria-describedby={
                        otherProps.description ? descriptionId : undefined
                    }
                    slot={checkboxContext.slot}
                    value={value}
                >
                    {({ isSelected, isIndeterminate, isDisabled }) => {
                        return (
                            <>
                                <Flex
                                    align="center"
                                    justify="center"
                                    inline
                                    {...stylex.props(checkboxStyles)}
                                    data-disabled={isDisabled || undefined}
                                    data-state={
                                        isIndeterminate
                                            ? 'indeterminate'
                                            : isSelected
                                              ? 'checked'
                                              : 'unchecked'
                                    }
                                >
                                    <IconContextProvider>
                                        {isIndeterminate ? (
                                            <MinusBoldIcon />
                                        ) : isSelected ? (
                                            <CheckBoldIcon />
                                        ) : null}
                                    </IconContextProvider>
                                </Flex>
                                {(label || otherProps.description) && (
                                    <Flex direction="column" gap="0_5x">
                                        {label &&
                                            (formContext && isField ? (
                                                <SingleLine asChild>
                                                    <label
                                                        id={labelId}
                                                        htmlFor={inputId}
                                                        {...stylex.props(
                                                            styles.label,
                                                            disabled &&
                                                                styles.labelDisabled,
                                                        )}
                                                    >
                                                        {label}
                                                    </label>
                                                </SingleLine>
                                            ) : (
                                                <Label
                                                    id={labelId}
                                                    htmlFor={inputId}
                                                    {...stylex.props(
                                                        styles.label,
                                                        disabled &&
                                                            styles.labelDisabled,
                                                    )}
                                                >
                                                    {label}
                                                </Label>
                                            ))}
                                        {otherProps.description && (
                                            <Paragraph
                                                variant="secondary"
                                                size="small"
                                                id={descriptionId}
                                            >
                                                {otherProps.description}
                                            </Paragraph>
                                        )}
                                    </Flex>
                                )}
                            </>
                        );
                    }}
                </ReactAriaCheckbox>
            </Flex>
        );
    },
);
Checkbox.displayName = 'Checkbox';
export type { CheckboxProps };
export { Checkbox };
