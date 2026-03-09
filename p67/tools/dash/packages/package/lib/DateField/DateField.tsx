import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { CalendarDateIcon } from '@snowflake/stellar-icons';
import * as stylex from '@stylexjs/stylex';
import { useContext, useMemo } from 'react';
import { mergeProps } from 'react-aria';
import type { DateFieldProps, DateValue } from 'react-aria-components';
import {
    DateField as AriaDateField,
    DateInput as AriaDateInput,
    DateRangePicker,
    DateSegment,
    FieldError,
    FieldErrorContext,
} from 'react-aria-components';

import type { RangeCalendarProps, SingleCalendarProps } from '../Calendar';
import { FieldContext, generateFieldId } from '../Form/FormContext';
import { useMergedStyles } from '../hooks';
import type { FieldSize } from '../internal/FieldWrapper/FieldWrapper';
import { useFieldWrapper } from '../internal/FieldWrapper/FieldWrapper';
import { useIsoDate, useIsoRange } from '../internal/hooks/useIsoDate';
import { useAriaLabel } from '../internal/hooks/useLabel';
import { useTypeRamp } from '../internal/hooks/useTypeRamp';
import { Flex } from '../Layout';
import { SingleLine } from '../Text';

const styles = stylex.create({
    segment: {
        color: {
            ':is([data-placeholder])': baltoTheme.reusableTextSecondary,
        },
    },
    rangeInputs: {
        flexGrow: 1,
    },
    rangeWrapper: {
        width: 'fit-content',
    },
});

interface DateFieldInputProps
    extends Omit<SingleCalendarProps, 'selectionType'>,
        React.ComponentPropsWithRef<'div'> {
    /** A label for the date input. */
    'aria-label'?: string | undefined;
    /** A label associated with the date input. */
    'aria-labelledby'?: string | undefined;
    /**
     * The size of the date input.
     * @default "regular"
     */
    size?: FieldSize | undefined;
    /**
     * Whether the date input is disabled.
     * @default false
     */
    disabled?: boolean | undefined;
    /**
     * Whether the date input should be auto focused.
     */
    autoFocus?: boolean | undefined;
}

const DateInput = ({
    slot,
    size,
}: {
    /**
     * The slot of the date input.
     */
    slot?: 'start' | 'end' | undefined;
    /**
     * The size of the date input.
     */
    size: FieldSize;
}) => {
    const inputTextStyle = useTypeRamp(
        size === 'small' ? 'smallSingleLine' : 'regularSingleLine',
    );

    return (
        <AriaDateInput slot={slot}>
            {(segment) => (
                <DateSegment
                    segment={segment}
                    {...stylex.props(styles.segment, inputTextStyle)}
                />
            )}
        </AriaDateInput>
    );
};

const DateField = ({
    'aria-label': ariaLabel,
    'aria-labelledby': ariaLabelledby,
    date: dateProp,
    defaultDate: defaultDateProp,
    onDateChange: onDateChangeProp,
    min,
    max,
    size,
    disabled,
    autoFocus,
    className,
    style,
    ...props
}: DateFieldInputProps) => {
    const textFieldStyles = useFieldWrapper({ size, disabled });
    const date = useIsoDate({
        date: dateProp,
        defaultDate: defaultDateProp,
        onDateChange: onDateChangeProp,
        min,
        max,
    });

    const fieldContext = useContext(FieldContext);
    const labelId = useMemo(
        () => fieldContext?.labelId ?? generateFieldId(),
        [fieldContext],
    );
    const { ariaLabelProps } = useAriaLabel({
        'aria-label': ariaLabel,
        'aria-labelledby': ariaLabelledby || labelId,
    });
    const mergedStyles = useMergedStyles(
        className,
        style,
        stylex.props(textFieldStyles.stylexProps),
    );

    return (
        <AriaDateField
            isDisabled={disabled}
            autoFocus={autoFocus}
            {...mergeProps(
                props,
                ariaLabelProps,
                textFieldStyles.attributes as DateFieldProps<DateValue>,
                mergedStyles,
                date,
            )}
        >
            <DateInput size={textFieldStyles.size} />
            <CalendarDateIcon />
        </AriaDateField>
    );
};

DateField.displayName = 'DateField';

interface DateRangeFieldProps extends RangeCalendarProps {
    /**
     * The aria-label of the date range field.
     */
    'aria-label'?: string | undefined;
    /**
     * The aria-labelledby of the date range field.
     */
    'aria-labelledby'?: string | undefined;
    /**
     * The size of the date range field.
     */
    size?: FieldSize | undefined;
    /**
     * Whether the date range field is disabled.
     */
    disabled?: boolean | undefined;
    /**
     * The suffix of the date range field.
     */
    suffix?: React.ReactNode | undefined;
}

const DateRangeField = ({
    'aria-label': ariaLabel,
    'aria-labelledby': ariaLabelledby,
    min,
    max,
    range: rangeProp,
    defaultRange: defaultRangeProp,
    onRangeChange: onRangeChangeProp,
    disabled,
    size,
    suffix,
}: DateRangeFieldProps) => {
    const fieldContext = useContext(FieldContext);
    const labelId = useMemo(
        () => fieldContext?.labelId ?? generateFieldId(),
        [fieldContext],
    );
    const { ariaLabelProps } = useAriaLabel({
        'aria-label': ariaLabel,
        'aria-labelledby': ariaLabelledby || labelId,
    });

    const range = useIsoRange({
        range: rangeProp,
        defaultRange: defaultRangeProp,
        onRangeChange: onRangeChangeProp,
        min,
        max,
    });

    const textFieldStyles = useFieldWrapper({ size, disabled });
    const fieldErrorContext = useContext(FieldErrorContext);

    return (
        <Flex
            gap="1x"
            direction="column"
            asChild
            {...stylex.props(styles.rangeWrapper)}
        >
            <DateRangePicker
                isDisabled={disabled}
                {...mergeProps(ariaLabelProps, range)}
                validate={() => true}
            >
                <Flex
                    gap="1_5x"
                    {...stylex.props(textFieldStyles.stylexProps)}
                    data-variant={
                        fieldErrorContext?.isInvalid ? 'critical' : undefined
                    }
                >
                    <Flex gap="1x" {...stylex.props(styles.rangeInputs)}>
                        <DateInput slot="start" size={textFieldStyles.size} />
                        <DateInput slot="end" size={textFieldStyles.size} />
                    </Flex>
                    {suffix}
                </Flex>
                <FieldError>
                    {({ validationErrors }) => {
                        const message = validationErrors.join(', ');

                        if (!message) {
                            return null;
                        }

                        return (
                            <SingleLine variant="critical">
                                {message}
                            </SingleLine>
                        );
                    }}
                </FieldError>
            </DateRangePicker>
        </Flex>
    );
};

DateRangeField.displayName = 'DateRangeField';

export type { DateFieldInputProps };
export { DateField, DateInput, DateRangeField };
