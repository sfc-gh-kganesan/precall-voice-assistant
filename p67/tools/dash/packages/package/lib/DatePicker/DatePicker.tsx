import { CalendarDateIcon } from '@snowflake/stellar-icons';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type React from 'react';
import { useCallback } from 'react';
import {
    DatePicker as AriaDatePicker,
    DateRangePicker as AriaDateRangePicker,
    Button,
    Dialog,
    Group,
    Popover,
} from 'react-aria-components';

import { BaltoThemeProvider } from '../BaltoProvider';
import { useButtonStyles } from '../Button/useButtonStyles';
import type {
    RangeCalendarProps,
    SelectionType,
    SingleCalendarProps,
} from '../Calendar';
import { Calendar } from '../Calendar';
import type { CalendarProps } from '../Calendar/types';
import { isRangeCalendarProps } from '../Calendar/types';
import { DateInput } from '../DateField';
import type { FieldSize } from '../internal/FieldWrapper/FieldWrapper';
import { useFieldWrapper } from '../internal/FieldWrapper/FieldWrapper';
import { useIsoDate, useIsoRange } from '../internal/hooks/useIsoDate';
import { levelStyles } from '../internal/utils/levelStyles';
import { Listbox } from '../Listbox';
import { ListboxOption } from '../Listbox/ListboxOption';
import type { ListboxSectionProps } from '../Listbox/ListboxSection';
import { ListboxSection } from '../Listbox/ListboxSection';
import type { PopoverAlign } from '../Popover';
import type { Key, Selection } from '../types';
import { positionToPlacement } from '../util/positionToPlacement';

const styles = stylex.create({
    popover: {
        padding: tokens['space-vertical-2xl'],
    },
    iconSpacing: {
        paddingLeft: tokens['space-horizontal-md'],
        paddingRight: tokens['space-horizontal-2xs'],
    },
});

interface DatePickerInnerProps
    extends Pick<CalendarProps, 'markedDate' | 'defaultVisibleDate'> {
    /**
     * The type of selection.
     */
    selectionType?: SelectionType | undefined;
    /**
     * The size of the date picker.
     */
    size?: FieldSize | undefined;
    /**
     * The alignment of the date picker.
     */
    align?: PopoverAlign | undefined;
    /**
     * A day to circle on the map. If not provided, today's date will be used.
     */
    markedDate?: string | undefined;
    /**
     * Whether the date picker is disabled.
     */
    disabled?: boolean | undefined;
}

/**
 * The inner component of the date picker.
 */
function DatePickerInner({
    size,
    align = 'start',
    disabled,
    selectionType,
    ...calendarProps
}: DatePickerInnerProps) {
    const fieldWrapperStyles = useFieldWrapper({ size, disabled });
    const buttonStyles = useButtonStyles({
        variant: 'tertiary',
        size: 'small',
        disabled,
    });

    return (
        <>
            <Group
                {...stylex.props(
                    fieldWrapperStyles.stylexProps,
                    styles.iconSpacing,
                )}
            >
                {selectionType === 'range' ? (
                    <>
                        <DateInput
                            slot="start"
                            size={fieldWrapperStyles.size}
                        />
                        <DateInput slot="end" size={fieldWrapperStyles.size} />
                    </>
                ) : (
                    <DateInput size={fieldWrapperStyles.size} />
                )}
                <Button {...stylex.props(buttonStyles)} isDisabled={disabled}>
                    <CalendarDateIcon />
                </Button>
            </Group>
            <Popover placement={positionToPlacement('bottom', align)}>
                <BaltoThemeProvider>
                    <Dialog
                        {...stylex.props(
                            levelStyles.level3Surface,
                            styles.popover,
                        )}
                    >
                        <Calendar
                            selectionType={selectionType}
                            {...calendarProps}
                        />
                    </Dialog>
                </BaltoThemeProvider>
            </Popover>
        </>
    );
}

interface SharedPickerProps
    extends Omit<DatePickerInnerProps, 'selectionType'> {
    /**
     * The label of the date picker.
     */
    'aria-label'?: string | undefined;
    /**
     * Whether the date picker is disabled.
     * @default false
     */
    disabled?: boolean | undefined;
}

interface SingleDatePickerProps
    extends SingleCalendarProps,
        SharedPickerProps {}

interface DateRangePickerProps extends RangeCalendarProps, SharedPickerProps {}

const SingleDatePicker = ({
    date,
    defaultDate,
    onDateChange,
    min,
    max,
    selectionType,
    disabled,
    'aria-label': ariaLabel,
    ...calendarProps
}: SingleDatePickerProps) => {
    return (
        <AriaDatePicker
            isDisabled={disabled}
            aria-label={ariaLabel}
            {...useIsoDate({ date, defaultDate, onDateChange, min, max })}
        >
            <DatePickerInner
                selectionType={selectionType}
                disabled={disabled}
                {...calendarProps}
            />
        </AriaDatePicker>
    );
};

const DateRangePicker = ({
    range,
    defaultRange,
    onRangeChange,
    min,
    max,
    disabled,
    'aria-label': ariaLabel,
    ...calendarProps
}: DateRangePickerProps) => {
    return (
        <AriaDateRangePicker
            isDisabled={disabled}
            aria-label={ariaLabel}
            {...useIsoRange({ range, defaultRange, onRangeChange, min, max })}
        >
            <DatePickerInner
                selectionType="range"
                disabled={disabled}
                {...calendarProps}
            />
        </AriaDateRangePicker>
    );
};

type DatePickerProps = SingleDatePickerProps | DateRangePickerProps;

const DatePicker = (props: DatePickerProps) => {
    if (isRangeCalendarProps(props)) {
        return <DateRangePicker {...props} />;
    }

    return <SingleDatePicker {...(props as SingleDatePickerProps)} />;
};

DatePicker.displayName = 'DatePicker';

const DatePickerRangeList = ({
    selected,
    onSelectionChange: onSelectionChangeProp,
    ...props
}: React.HTMLAttributes<HTMLDivElement> & {
    /**
     * The selected date range.
     */
    selected?: string | undefined;
    /**
     * A callback called when the selected date range changes.
     */
    onSelectionChange?: ((key: string) => void) | undefined;
}) => {
    const onSelectionChange = useCallback(
        (key: Selection) => {
            if (key === 'all') return;
            onSelectionChangeProp?.(Array.from(key.values())[0] as string);
        },
        [onSelectionChangeProp],
    );

    return (
        <Listbox.Root
            selectionMode="single"
            selection={selected ? [selected as Key] : undefined}
            onSelectionChange={onSelectionChange}
            isVirtualized={false}
            aria-label="Date Range Options"
            {...props}
        />
    );
};

DatePickerRangeList.displayName = 'DatePickerRangeList';

const DatePickerRangeListItem = ({
    id,
    label,
}: {
    /**
     * The id of the date range list item.
     */
    id?: string | undefined;
    /**
     * The label of the date range list item.
     */
    label: string;
}) => {
    return <ListboxOption id={id} label={label} />;
};

DatePickerRangeListItem.displayName = 'DatePickerRangeListItem';

const DatePickerRangeListSection = (props: ListboxSectionProps) => {
    return <ListboxSection {...props} />;
};

DatePickerRangeListSection.displayName = 'DatePickerRangeListSection';

export {
    DatePicker,
    DatePickerRangeList,
    DatePickerRangeListItem,
    DatePickerRangeListSection,
};
