import type { DateValue } from 'react-aria';

export function datesEqual<T extends DateValue>(date1: T, date2: T) {
    return (
        date1.year === date2.year &&
        date1.month === date2.month &&
        date1.day === date2.day
    );
}

export function isBefore<T extends DateValue>(date1: T, date2: T) {
    return date1.compare(date2) < 0;
}
