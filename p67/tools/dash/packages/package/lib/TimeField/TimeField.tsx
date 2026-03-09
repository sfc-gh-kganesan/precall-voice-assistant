import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { ClockIcon } from '@snowflake/stellar-icons';
import * as stylex from '@stylexjs/stylex';
import { useContext, useMemo } from 'react';
import { mergeProps } from 'react-aria';
import type { TimeFieldProps, TimeValue } from 'react-aria-components';
import {
    DateInput as AriaDateInput,
    TimeField as AriaTimeField,
    DateSegment,
} from 'react-aria-components';

import { FieldContext, generateFieldId } from '../Form/FormContext';
import { useMergedStyles } from '../hooks';
import type { FieldSize } from '../internal/FieldWrapper/FieldWrapper';
import { useFieldWrapper } from '../internal/FieldWrapper/FieldWrapper';
import { useIsoTime } from '../internal/hooks/useIsoDate';
import { useAriaLabel } from '../internal/hooks/useLabel';
import { useTypeRamp } from '../internal/hooks/useTypeRamp';

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

interface TimeFieldInputProps extends React.ComponentPropsWithRef<'div'> {
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
    /**
     * The value of the time input.
     */
    time?: string | undefined;
    /**
     * The default value of the time input.
     */
    defaultTime?: string | undefined;
    /**
     * The onChange handler of the time input.
     */
    onTimeChange?: ((time: string | undefined) => void) | undefined;
    /**
     * The minimum value of the time input.
     */
    min?: string | undefined;
    /**
     * The maximum value of the time input.
     */
    max?: string | undefined;
    /**
     * Determines the smallest unit that is displayed in the time picker.
     */
    granularity?: 'hour' | 'minute' | 'second' | undefined;
    /**
     * Whether the input is read only.
     */
    readOnly?: boolean | undefined;
    /**
     * Whether the input is required.
     */
    required?: boolean | undefined;
    /**
     * The name of the input.
     */
    name?: string | undefined;
}

const DateInput = ({
    size,
}: {
    /**
     * The size of the date input.
     */
    size: FieldSize;
}) => {
    const inputTextStyle = useTypeRamp(
        size === 'small' ? 'smallSingleLine' : 'regularSingleLine',
    );

    return (
        <AriaDateInput>
            {(segment) => (
                <DateSegment
                    segment={segment}
                    {...stylex.props(styles.segment, inputTextStyle)}
                />
            )}
        </AriaDateInput>
    );
};

const TimeField = ({
    'aria-label': ariaLabel,
    'aria-labelledby': ariaLabelledby,
    time: timeProp,
    defaultTime,
    onTimeChange,
    min,
    max,
    granularity,
    size,
    disabled,
    autoFocus,
    readOnly,
    required,
    name,
    className,
    style,
    ...props
}: TimeFieldInputProps) => {
    const textFieldStyles = useFieldWrapper({ size, disabled, readOnly });
    const date = useIsoTime({
        time: timeProp,
        defaultTime,
        onTimeChange,
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
        <AriaTimeField
            isDisabled={disabled}
            autoFocus={autoFocus}
            granularity={granularity}
            isReadOnly={readOnly}
            isRequired={required}
            name={name}
            {...mergeProps(
                props,
                ariaLabelProps,
                textFieldStyles.attributes as TimeFieldProps<TimeValue>,
                mergedStyles,
                date,
            )}
        >
            <DateInput size={textFieldStyles.size} />
            <ClockIcon />
        </AriaTimeField>
    );
};

TimeField.displayName = 'TimeField';

export type { TimeFieldInputProps };
export { TimeField };
