import type {
    CalendarDate,
    CalendarDateTime,
    ZonedDateTime,
} from '@internationalized/date';
import { parseDate, parseTime } from '@internationalized/date';
import type { DateValue, TimeValue } from 'react-aria';
import type {
    DateFieldProps,
    DateRangePickerProps,
} from 'react-aria-components';

import type { DateRange } from '../../Calendar';
import { isBefore } from '../../Calendar/utils';
import type { RangeValue } from '../../types';

// This is from react-aria but they don't expose it
type MappedDateValue<T> = T extends ZonedDateTime
    ? ZonedDateTime
    : T extends CalendarDateTime
      ? CalendarDateTime
      : T extends CalendarDate
        ? CalendarDate
        : never;

/**
 * Parses a date string to a date value.
 */
function maybeParseDate<T extends DateValue>(
    date: string | undefined,
): T | undefined {
    if (date) {
        return parseDate(date) as T;
    }
}

/**
 * The hook that returns the date input props.
 */
function useIsoDate<T extends DateValue>({
    defaultDate,
    date,
    onDateChange: onChange,
    min,
    max,
}: {
    /**
     * The default date of the date input.
     */
    defaultDate: string | undefined;
    /**
     * The date of the date input.
     */
    date: string | undefined;
    /**
     * The callback function that is called when the date input changes.
     */
    onDateChange: ((date: string | undefined) => void) | undefined;
    /**
     * The minimum date of the date input.
     */
    min: string | undefined;
    /**
     * The maximum date of the date input.
     */
    max: string | undefined;
}): Pick<
    DateFieldProps<T>,
    'defaultValue' | 'value' | 'onChange' | 'minValue' | 'maxValue'
> {
    return {
        minValue: maybeParseDate<T>(min),
        maxValue: maybeParseDate<T>(max),
        defaultValue: maybeParseDate<T>(defaultDate),
        value: maybeParseDate<T>(date),
        onChange: onChange
            ? (date: MappedDateValue<T> | null) =>
                  onChange(date ? date.toString() : undefined)
            : undefined,
    };
}

/**
 * Parses a date range string to a date range value.
 */
function maybeParseRange<T extends DateValue>(range: DateRange | undefined) {
    if (range) {
        return {
            start: parseDate(range.start) as T,
            end: parseDate(range.end) as T,
        };
    }
}

/**
 * The hook that returns the range input props.
 */
function useIsoRange<T extends DateValue>({
    defaultRange,
    range,
    onRangeChange,
    min,
    max,
}: {
    /**
     * The default range of the range input.
     */
    defaultRange: DateRange | undefined;
    /**
     * The range of the range input.
     */
    range: DateRange | undefined;
    /**
     * The callback function that is called when the range input changes.
     */
    onRangeChange: ((range: DateRange | undefined) => void) | undefined;
    /**
     * The minimum date of the range input.
     */
    min: string | undefined;
    /**
     * The maximum date of the range input.
     */
    max: string | undefined;
}): Pick<
    DateRangePickerProps<T>,
    'defaultValue' | 'value' | 'onChange' | 'minValue' | 'maxValue'
> {
    const value = maybeParseRange<T>(range);

    return {
        minValue: maybeParseDate<T>(min),
        maxValue: maybeParseDate<T>(max),
        defaultValue: maybeParseRange<T>(defaultRange),
        value,
        onChange: onRangeChange
            ? (newRange: RangeValue<MappedDateValue<T>> | null) => {
                  const startChanged = newRange?.start !== range?.start;

                  let computedRange: DateRange | undefined;

                  if (newRange) {
                      const start = newRange.start.toString();
                      const end = newRange.end.toString();

                      if (isBefore(newRange.end, newRange.start)) {
                          if (startChanged) {
                              computedRange = { start, end: start };
                          } else {
                              computedRange = { start: end, end };
                          }
                      } else {
                          computedRange = { start, end };
                      }
                  }

                  onRangeChange(computedRange);
              }
            : undefined,
    };
}

/**
 *
 */
function maybeParseTime<T extends TimeValue>(time: string | undefined) {
    if (time) {
        return parseTime(time) as T;
    }
}

/**
 *
 */
function useIsoTime<T extends TimeValue>({
    defaultTime,
    time,
    onTimeChange,
    min,
    max,
}: {
    /**
     * The default time of the time input.
     */
    defaultTime: string | undefined;
    /**
     * The time of the time input.
     */
    time: string | undefined;
    /**
     * The callback function that is called when the time input changes.
     */
    onTimeChange: ((time: string | undefined) => void) | undefined;
    /**
     * The minimum time of the time input.
     */
    min: string | undefined;
    /**
     * The maximum time of the time input.
     */
    max: string | undefined;
}) {
    return {
        minValue: maybeParseTime<T>(min),
        maxValue: maybeParseTime<T>(max),
        defaultValue: maybeParseTime<T>(defaultTime),
        value: maybeParseTime<T>(time),
        onChange: onTimeChange
            ? (time: T | null) =>
                  onTimeChange(time ? time.toString() : undefined)
            : undefined,
    };
}

export { useIsoDate, useIsoRange, useIsoTime };
