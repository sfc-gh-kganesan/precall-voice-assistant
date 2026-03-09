import { getLocalTimeZone, parseDate, today } from '@internationalized/date';
import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { buttonTheme } from '@snowflake/balto-themes/buttonTheme.stylex.js';
import type { IconType } from '@snowflake/stellar-icons';
import { ChevronLeftIcon, ChevronRightIcon } from '@snowflake/stellar-icons';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import { forwardRef, useContext, useMemo, useRef } from 'react';
import {
    Calendar as AriaCalendar,
    RangeCalendar as AriaRangeCalendar,
    Button,
    ButtonContext,
    CalendarCell,
    CalendarGrid,
    CalendarGridBody,
    CalendarGridHeader,
    CalendarHeaderCell,
    CalendarStateContext,
    DateRangePickerContext,
    Heading,
    useContextProps,
} from 'react-aria-components';

import { useButtonStyles } from '../Button/useButtonStyles';
import { useIsoDate, useIsoRange } from '../internal/hooks/useIsoDate';
import { useMergedRef } from '../internal/hooks/useMergedRef';
import { useTypeRamp } from '../internal/hooks/useTypeRamp';
import { Flex } from '../Layout';
import { Paragraph } from '../Text';
import type { RangeValue } from '../types';
import type {
    CalendarProps,
    RangeCalendarProps,
    SingleCalendarProps,
} from './types';
import { isRangeCalendarProps } from './types';

const styles = stylex.create({
    root: {
        display: 'flex',
        flexDirection: 'column',
        gap: tokens['space-gap-lg'],
        width: 'fit-content',
    },
    header: {
        width: '100%',
    },
    heading: {
        flexGrow: 1,
        textAlign: 'center',
    },
    calendar: {
        borderCollapse: 'collapse',
        borderSpacing: 0,

        padding: { ':is(*) td': `0 ${tokens['space-horizontal-sm']}` },
        position: { ':is(*) td': 'relative' },
        zIndex: { ':is(*) td': 0 },
    },
    singleCalendar: {
        margin: `0 calc(${tokens['space-vertical-sm']} * -1)`,
    },
    cellInRange: {
        '::before': {
            backgroundColor: baltoTheme.reusableSelectedBackground,
            content: "''",
            inset: `0 calc(${tokens['space-vertical-sm']} * -1)`,
            position: 'absolute',
            zIndex: -1,
        },
    },
    cellStartRange: {
        '::before': {
            inset: `0 calc(${tokens['space-vertical-sm']} * -1) 0 0`,
        },
    },
    cellEndRange: {
        '::before': {
            inset: `0 0 0 calc(${tokens['space-vertical-sm']} * -1)`,
        },
    },
    cellEndAndStartRange: {
        '::before': {
            display: 'none',
        },
    },
    headerCell: {
        color: baltoTheme.reusableTextSecondary,
        padding: `0 ${tokens['space-horizontal-sm']}`,
    },
    headerCellContent: {
        display: 'flex',
        justifyContent: 'center',
        width: '100%',
    },
    cell: {
        height: tokens['size-md'],
        padding: 0,
        position: 'relative',
        userSelect: 'none',
        width: tokens['size-md'],

        alignItems: 'center',
        display: 'flex',
        justifyContent: 'center',
    },
    today: {
        borderColor: baltoTheme.reusableBorderDefault,
        borderRadius: '50%',
        borderStyle: 'solid',
        borderWidth: 4,
        inset: 0,
        position: 'absolute',
    },
    cellOutside: {
        color: buttonTheme.secondaryTextDisabled,
    },
    cellSelected: {
        backgroundColor: baltoTheme.reusableSelectedUi,
        color: buttonTheme.primaryTextPress,
    },
    valueCellHover: {
        ':hover': {
            backgroundColor: baltoTheme.reusableSelectedUi,
            color: buttonTheme.primaryTextPress,
        },
    },
});

/**
 *
 */
function ChangeMonthButton({
    icon: Icon,
    slot,
    'aria-label': ariaLabel,
}: {
    /**
     * The icon to display in the button.
     */
    icon: IconType;
    /**
     * The aria-label of the button.
     */
    'aria-label': string;
    /**
     * The slot of the button.
     */
    slot: 'previous' | 'next';
}) {
    const ref = useRef<HTMLButtonElement>(null);
    const [contextProps] = useContextProps({ slot }, ref, ButtonContext);
    const buttonStyles = useButtonStyles({
        variant: 'tertiary',
        size: 'small',
    });

    return (
        <Button
            {...contextProps}
            {...stylex.props(buttonStyles)}
            aria-label={ariaLabel}
        >
            <Icon />
        </Button>
    );
}

/**
 * The inner component of the calendar.
 */
function CalendarInner({
    visibleMonths,
    isRange = false,
    selectionType = 'exact',
    markedDate,
    hideOutsideDays,
    min,
    max,
}: {
    /**
     * The number of months to display.
     */
    visibleMonths: number;
    /**
     * Whether the calendar is a range calendar.
     */
    isRange: boolean;
    /**
     * The type of selection.
     */
    selectionType?: SelectionType | undefined;
    /**
     * The date to mark.
     */
    markedDate?: string | undefined;
    /**
     * Whether to hide outside days.
     */
    hideOutsideDays?: boolean | undefined;
    /**
     * The minimum date that can be selected.
     */
    min?: string | undefined;
    /**
     * The maximum date that can be selected.
     */
    max?: string | undefined;
}) {
    const calendarState = useContext(CalendarStateContext);
    const todaysDate = useMemo(() => {
        if (markedDate) {
            return parseDate(markedDate);
        }

        return today(getLocalTimeZone());
    }, [markedDate]);
    const cellStyles = useTypeRamp('labelSmall');
    const headerCellStyles = useTypeRamp('smallParagraph');

    return (
        <>
            <Flex asChild align="center" {...stylex.props(styles.header)}>
                <div>
                    <ChangeMonthButton
                        icon={ChevronLeftIcon}
                        slot="previous"
                        aria-label="Previous month"
                    />
                    <Paragraph asChild size="small" variant="secondary" bold>
                        <Heading {...stylex.props(styles.heading)} />
                    </Paragraph>
                    <ChangeMonthButton
                        icon={ChevronRightIcon}
                        slot="next"
                        aria-label="Next month"
                    />
                </div>
            </Flex>

            <Flex gap="4x">
                {Array.from({ length: visibleMonths }).map((_, index) => (
                    <CalendarGrid
                        key={`calendar-grid-${index}`}
                        offset={index === 0 ? undefined : { months: index }}
                        data-test
                        {...stylex.props(
                            styles.calendar,
                            !isRange && styles.singleCalendar,
                        )}
                    >
                        <CalendarGridHeader>
                            {(day) => (
                                <CalendarHeaderCell
                                    {...stylex.props(styles.headerCell)}
                                >
                                    <div
                                        {...stylex.props(
                                            styles.cell,
                                            headerCellStyles,
                                            styles.headerCellContent,
                                        )}
                                    >
                                        {day}
                                    </div>
                                </CalendarHeaderCell>
                            )}
                        </CalendarGridHeader>
                        <CalendarGridBody>
                            {(date) => {
                                let included = false;
                                let isAnchor: 'start' | 'end' | undefined;

                                if (calendarState?.value) {
                                    const comparison =
                                        calendarState.value.compare(date);

                                    if (selectionType === 'before') {
                                        included = comparison > 0;

                                        if (comparison === 0) {
                                            included = true;
                                            isAnchor = 'end';
                                        }
                                    } else if (selectionType === 'after') {
                                        included = comparison < 0;

                                        if (comparison === 0) {
                                            included = true;
                                            isAnchor = 'start';
                                        }
                                    }
                                }

                                return (
                                    <CalendarCell
                                        date={date}
                                        data-selection-included={included}
                                    >
                                        {({
                                            isOutsideVisibleRange,
                                            isSelected,
                                            isSelectionEnd,
                                            isSelectionStart,
                                            isOutsideMonth,
                                        }) => {
                                            if (
                                                hideOutsideDays &&
                                                isOutsideVisibleRange
                                            ) {
                                                return <div />;
                                            }

                                            let hasSelectedBackground = false;

                                            if (isRange) {
                                                if (
                                                    isSelectionEnd ||
                                                    isSelectionStart ||
                                                    isAnchor
                                                ) {
                                                    hasSelectedBackground = true;
                                                }
                                            } else {
                                                hasSelectedBackground =
                                                    isSelected;
                                            }

                                            const isOutside =
                                                isOutsideVisibleRange ||
                                                isOutsideMonth;
                                            const isBeforeMinDate =
                                                min &&
                                                date.compare(parseDate(min)) <
                                                    0;
                                            const isAfterMaxDate =
                                                max &&
                                                date.compare(parseDate(max)) >
                                                    0;

                                            const isSelectable =
                                                !isOutside &&
                                                !isBeforeMinDate &&
                                                !isAfterMaxDate;

                                            return (
                                                <div
                                                    {...stylex.props(
                                                        cellStyles,
                                                        styles.cell,
                                                        isSelectable &&
                                                            styles.valueCellHover,
                                                        (isRange ||
                                                            selectionType !==
                                                                'exact') &&
                                                            (isSelected ||
                                                                included) &&
                                                            !isBeforeMinDate &&
                                                            !isAfterMaxDate &&
                                                            styles.cellInRange,
                                                        hasSelectedBackground &&
                                                            isSelectable &&
                                                            styles.cellSelected,
                                                        (isSelectionStart ||
                                                            isAnchor ===
                                                                'start') &&
                                                            styles.cellStartRange,
                                                        (isSelectionEnd ||
                                                            isAnchor ===
                                                                'end') &&
                                                            styles.cellEndRange,
                                                        isSelectionStart &&
                                                            isSelectionEnd &&
                                                            styles.cellEndAndStartRange,
                                                        !isSelectable &&
                                                            styles.cellOutside,
                                                    )}
                                                    aria-disabled={
                                                        !isSelectable
                                                    }
                                                >
                                                    {date.day}

                                                    {date.compare(
                                                        todaysDate,
                                                    ) === 0 &&
                                                        isSelectable && (
                                                            <div
                                                                {...stylex.props(
                                                                    styles.today,
                                                                )}
                                                            />
                                                        )}
                                                </div>
                                            );
                                        }}
                                    </CalendarCell>
                                );
                            }}
                        </CalendarGridBody>
                    </CalendarGrid>
                ))}
            </Flex>
        </>
    );
}

type SelectionType = 'before' | 'after' | 'exact' | 'range';

const SingleCalendar = ({
    visibleMonths = 1,
    date,
    defaultDate,
    onDateChange,
    min,
    max,
    selectionType = 'exact',
    markedDate,
    hideOutsideDays,
    defaultVisibleDate,
    onFocusDate,
}: SingleCalendarProps) => {
    return (
        <AriaCalendar
            {...stylex.props(styles.root)}
            {...useIsoDate({ date, defaultDate, onDateChange, min, max })}
            visibleDuration={{ months: visibleMonths }}
            pageBehavior="single"
            defaultFocusedValue={
                defaultVisibleDate ? parseDate(defaultVisibleDate) : undefined
            }
            onFocusChange={(e) => onFocusDate?.(e.toString())}
        >
            <CalendarInner
                visibleMonths={visibleMonths}
                isRange={false}
                selectionType={selectionType}
                markedDate={markedDate}
                hideOutsideDays={hideOutsideDays}
                min={min}
                max={max}
            />
        </AriaCalendar>
    );
};

SingleCalendar.displayName = 'SingleCalendar';

type DateRange = RangeValue<string>;

const RangeCalendar = forwardRef<HTMLDivElement, RangeCalendarProps>(
    function RangeCalendar(
        {
            visibleMonths = 1,
            range,
            defaultRange,
            onRangeChange,
            min,
            max,
            markedDate,
            hideOutsideDays,
            defaultVisibleDate,
            onFocusDate,
        },
        outerRef,
    ) {
        const innerRef = useRef<HTMLDivElement>(null);
        const ref = useMergedRef(outerRef, innerRef);

        return (
            <AriaRangeCalendar
                ref={ref}
                {...stylex.props(styles.root)}
                {...useIsoRange({
                    range,
                    defaultRange,
                    onRangeChange,
                    min,
                    max,
                })}
                visibleDuration={{ months: visibleMonths }}
                pageBehavior="single"
                defaultFocusedValue={
                    defaultVisibleDate
                        ? parseDate(defaultVisibleDate)
                        : undefined
                }
                onFocusChange={(e) => onFocusDate?.(e.toString())}
            >
                <CalendarInner
                    visibleMonths={visibleMonths}
                    isRange={true}
                    markedDate={markedDate}
                    hideOutsideDays={hideOutsideDays}
                    min={min}
                    max={max}
                />
            </AriaRangeCalendar>
        );
    },
);

RangeCalendar.displayName = 'RangeCalendar';

/**
 * A calendar component that can be used to select a single date or a range of dates.
 */
function Calendar(props: CalendarProps) {
    const rangeContext = useContext(DateRangePickerContext);

    if (isRangeCalendarProps(props, rangeContext)) {
        return <RangeCalendar {...props} />;
    }

    return <SingleCalendar {...props} />;
}
Calendar.displayName = 'Calendar';

Calendar.displayName = 'Calendar';

export type {
    DateRange,
    RangeCalendarProps,
    SingleCalendarProps,
    SelectionType,
};
export { Calendar };
