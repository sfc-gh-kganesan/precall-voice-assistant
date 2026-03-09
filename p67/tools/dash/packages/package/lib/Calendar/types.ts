import type { ContextValue } from 'react-aria-components';

import type { ControlledComponent, RangeValue } from '../main';

interface CalendarSharedProps {
    /** A day to circle on the map. If not provided, today's date will be used. */
    markedDate?: string | undefined;
    /**
     * The number of months to show in the calendar.
     * @default 1
     */
    visibleMonths?: number | undefined;
    /** The minimum date that can be selected. */
    min?: string | undefined;
    /** The maximum date that can be selected. */
    max?: string | undefined;
    /**
     * By default the calendar will show all days that fit even if they are outside the visible range.
     * This prop will hide those days.
     * @default false
     */
    hideOutsideDays?: boolean | undefined;
    /** The date to display when the calendar is first opened. */
    defaultVisibleDate?: string | undefined;
    /** A function that is called when a user focuses a date. */
    onFocusDate?: (date: string) => void;
}

export type SelectionType = 'before' | 'after' | 'exact' | 'range';

export interface SingleCalendarProps
    extends ControlledComponent<'date', string | undefined>,
        CalendarSharedProps {
    /** The type of date selection */
    selectionType?: 'before' | 'after' | 'exact' | undefined;
}

export type DateRange = RangeValue<string>;

export interface RangeCalendarProps
    extends ControlledComponent<'range', DateRange | undefined>,
        CalendarSharedProps {
    /** The type of date selection */
    selectionType?: 'range' | undefined;
}

export type CalendarProps = SingleCalendarProps | RangeCalendarProps;

export function isRangeCalendarProps(
    props: CalendarProps,
    rangeContext?: ContextValue<unknown, HTMLDivElement> | undefined,
): props is RangeCalendarProps {
    return (
        'range' in props ||
        'defaultRange' in props ||
        'onRangeChange' in props ||
        props.selectionType === 'range' ||
        Boolean(rangeContext)
    );
}
