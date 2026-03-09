import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { buttonTheme } from '@snowflake/balto-themes/buttonTheme.stylex.js';
import { filterTheme } from '@snowflake/balto-themes/filterTheme.stylex.js';
import {
    ChevronDownIcon,
    ClearIcon,
    IconContextProvider,
    type IconType,
} from '@snowflake/stellar-icons';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import { forwardRef, useCallback, useContext, useRef } from 'react';
import { mergeProps, useFocusRing } from 'react-aria';

import { useMergedStyles } from '../hooks';
import { useMergedRef } from '../internal/hooks/useMergedRef';
import type { Size } from '../types';
import { SizeContext } from '../util/context';
import { FilterLabel } from './FilterLabel';

const styles = stylex.create({
    wrapper: {
        display: 'flex',
        position: 'relative',
        width: 'max-content',
    },

    filter: {
        alignItems: 'center',
        display: 'flex',
        gap: tokens['space-gap-sm'],

        borderColor: {
            default: buttonTheme.secondaryBorderDefault,
            ':is([data-selected])': filterTheme.activeBackgroundDefault,
            ':is([disabled])': buttonTheme.secondaryBorderDisabled,
        },
        borderRadius: tokens['radius-sm'],
        borderStyle: 'solid',
        borderWidth: 1,

        backgroundColor: {
            default: buttonTheme.secondaryBackgroundDefault,
            ':is([data-selected])': filterTheme.activeBackgroundDefault,
            ':is([disabled])': buttonTheme.secondaryBackgroundDisabled,
        },
        height: tokens['size-md'],
        minWidth: 0,
        outline: {
            default: 'none',
            ":is([data-focus-visible='true'])": `2px solid ${baltoTheme.reusableBorderFocusedActiveItem}`,
        },
        padding: `0 ${tokens['space-horizontal-md']}`,
    },
    filterInteractive: {
        backgroundColor: {
            default: buttonTheme.secondaryBackgroundDefault,
            ':hover:not([disabled])': buttonTheme.secondaryBackgroundHover,
            ':active:not([disabled])': buttonTheme.secondaryBackgroundPress,
            ':is([data-selected])': filterTheme.activeBackgroundDefault,
            ':is([data-selected]):hover:not([disabled]):not(:active)':
                filterTheme.activeBackgroundHover,
            ':is([data-selected]):active:not([disabled])':
                filterTheme.activeBackgroundActive,
            ':is([disabled])': buttonTheme.secondaryBackgroundDisabled,
        },
        borderColor: {
            default: buttonTheme.secondaryBorderDefault,
            ':hover:not([disabled])': buttonTheme.secondaryBorderHover,
            ':active:not([disabled])': buttonTheme.secondaryBorderPress,
            ':is([data-selected])': filterTheme.activeBackgroundDefault,
            ':is([data-selected]):hover:not([disabled]):not(:active)':
                filterTheme.activeBackgroundHover,
            ':is([data-selected]):active:not([disabled])':
                filterTheme.activeBackgroundActive,
            ':is([disabled])': buttonTheme.secondaryBorderDisabled,
        },
        cursor: {
            default: 'pointer',
            ':is([disabled])': 'not-allowed',
        },
    },
    filterSmall: {
        height: tokens['size-sm'],
    },
    filterWithClearButton: {
        paddingRight: 36,
    },
    filterWithClearButtonAndChevron: {
        paddingRight: tokens['space-horizontal-md'],
    },

    value: {
        flexGrow: 1,
        minWidth: 0,
    },
    valueWithClearButtonAndChevron: {
        paddingRight: tokens['space-horizontal-2xl'],
    },

    clearButton: {
        backgroundColor: {
            default: 'transparent',
            ':hover:not([disabled]):not(:active)':
                baltoTheme.reusableBackgroundRowHover,
            ':is([data-selected]):active:not([disabled])':
                filterTheme.activeBackgroundActive,
        },
        borderRadius: tokens['radius-sm'],
        borderWidth: 0,
        cursor: 'pointer',
        height: tokens['size-2xs'],
        padding: tokens['space-vertical-3xs'],
        width: tokens['size-2xs'],

        position: 'absolute',
        right: tokens['space-horizontal-md'],
        top: '50%',
        transform: 'translateY(-50%)',

        alignItems: 'center',
        display: 'flex',
        justifyContent: 'center',

        outline: {
            default: 'none',
            ":is([data-focus-visible='true'])": `2px solid ${baltoTheme.reusableBorderFocusedActiveItem}`,
        },
    },
    clearButtonSelected: {
        backgroundColor: {
            default: filterTheme.activeBackgroundDefault,
            ':hover:not([disabled]):not(:active)':
                filterTheme.activeBackgroundHover,
            ':active:not([disabled])': filterTheme.activeBackgroundActive,
        },
        borderRadius: '50%',
    },
    clearButtonWithChevron: {
        right: `calc(${tokens['space-horizontal-md']} + ${tokens['space-horizontal-2xl']})`,
    },

    activeText: {
        color: {
            default: filterTheme.activeTextColorDefault,
            ':hover:not([disabled])': filterTheme.activeTextColorHover,
            ':active:not([disabled])': filterTheme.activeTextColorActive,
        },
    },
    disabledText: {
        color: baltoTheme.reusableDisabledText,
    },
});

/** A button that clears the filter. */
function ClearButton({
    hasChevron,
    isSelected,
    ...props
}: {
    /** A callback called when the button is clicked. */
    onClick: () => void;
    /** The aria-label of the button. */
    'aria-label': string;
    /** Whether the button has a chevron. */
    hasChevron?: boolean | undefined;
    /** Whether the button is selected. */
    isSelected?: boolean | undefined;
}) {
    const { focusProps, isFocusVisible } = useFocusRing();

    return (
        <button
            {...mergeProps(props, focusProps, {
                onClick: (e: React.MouseEvent<HTMLButtonElement>) =>
                    e.stopPropagation(),
                onPointerDown: (e: React.PointerEvent<HTMLButtonElement>) =>
                    e.stopPropagation(),
            })}
            data-focus-visible={isFocusVisible || undefined}
            type="button"
            {...stylex.props(
                styles.clearButton,
                isSelected && styles.clearButtonSelected,
                hasChevron && styles.clearButtonWithChevron,
            )}
        >
            <ClearIcon />
        </button>
    );
}

interface FilterBaseProps
    extends Omit<
        React.ComponentPropsWithoutRef<'div'>,
        'aria-label' | 'aria-labelledby'
    > {
    /**
     * The icon to display in the filter.
     */
    icon?: IconType | undefined;
    /**
     * The size of the filter.
     * @default "regular"
     */
    size?: Extract<Size, 'small' | 'regular'> | undefined;
    /**
     * Whether the filter is selected.
     * @default false
     */
    isSelected?: boolean | undefined;
    /**
     * A callback called when the filter is selected.
     */
    onSelectChange?: ((selected: boolean) => void) | undefined;
    /**
     * The values of the filter.
     */
    values: string[];
    /**
     * A callback called when the filter is cleared.
     */
    onClear?: (() => void) | undefined;
    /**
     * Whether the filter is disabled.
     * @default false
     */
    disabled?: boolean | undefined;
    /**
     * Whether the filter has a chevron.
     * @default false
     */
    hasChevron?: boolean | undefined;
    /** The value to show when there is no value */
    placeholder?: string | undefined;
}

interface FilterPropsWithLabel extends FilterBaseProps {
    /**
     * The label of the filter.
     */
    label: string;
}

interface FilterPropsWithAriaLabel extends FilterBaseProps {
    /**
     * The aria-label of the filter.
     */
    'aria-label': string;
}

interface FilterPropsWithAriaLabelledby extends FilterBaseProps {
    /**
     * The id of the element that labels the filter.
     */
    'aria-labelledby': string;
}

type FilterProps =
    | FilterPropsWithLabel
    | FilterPropsWithAriaLabel
    | FilterPropsWithAriaLabelledby;

const Filter = forwardRef<HTMLDivElement, FilterProps>(function Filter(
    {
        icon: Icon,
        size: sizeProp,
        isSelected,
        onSelectChange,
        values,
        onClear: onClearProp,
        disabled,
        className,
        style,
        hasChevron,
        placeholder = '--',
        ...props
    },
    outerRef,
) {
    const contextSize = useContext(SizeContext);
    const size = sizeProp ?? contextSize ?? 'regular';
    const { focusProps, isFocusVisible } = useFocusRing();
    const label = 'label' in props ? props.label : undefined;
    const ariaLabel = 'aria-label' in props ? props['aria-label'] : undefined;
    const ariaLabelledby =
        'aria-labelledby' in props ? props['aria-labelledby'] : undefined;
    const showClearButton = Boolean(onClearProp && !disabled && values[0]);
    const innerRef = useRef<HTMLElement>(null);
    const ref = useMergedRef(outerRef, innerRef);
    const onClear = useCallback(() => {
        onClearProp?.();
        innerRef.current?.focus();
    }, [onClearProp]);
    const inInteractive = Boolean(
        onSelectChange || props.onClick || props.onPointerDown,
    );
    const mergedStyles = useMergedStyles(
        className,
        style,
        stylex.props(styles.wrapper),
    );
    const Element = inInteractive ? 'button' : 'div';

    return (
        <IconContextProvider
            color={
                disabled
                    ? baltoTheme.reusableDisabledText
                    : isSelected
                      ? filterTheme.activeTextColorDefault
                      : baltoTheme.reusableTextSecondary
            }
        >
            <div {...mergedStyles}>
                <Element
                    ref={ref}
                    {...mergeProps(props, focusProps, {
                        onClick: () => onSelectChange?.(!isSelected),
                    })}
                    type={inInteractive ? 'button' : undefined}
                    aria-label={ariaLabel}
                    aria-labelledby={ariaLabelledby}
                    disabled={disabled}
                    data-selected={isSelected || undefined}
                    data-focus-visible={isFocusVisible || undefined}
                    {...stylex.props(
                        styles.filter,
                        size === 'small' && styles.filterSmall,
                        showClearButton && styles.filterWithClearButton,
                        inInteractive && styles.filterInteractive,
                        showClearButton &&
                            hasChevron &&
                            styles.filterWithClearButtonAndChevron,
                    )}
                >
                    {Icon && <Icon />}
                    {label &&
                        (disabled ? (
                            <FilterLabel
                                size={size}
                                {...stylex.props(styles.disabledText)}
                            >
                                {label}
                            </FilterLabel>
                        ) : isSelected ? (
                            <FilterLabel
                                size={size}
                                {...stylex.props(styles.activeText)}
                            >
                                {label}
                            </FilterLabel>
                        ) : (
                            <FilterLabel size={size} variant="secondary">
                                {label}
                            </FilterLabel>
                        ))}
                    {values[0] ? (
                        <FilterLabel
                            size={size}
                            bold
                            truncate
                            {...stylex.props(
                                styles.value,
                                disabled && styles.disabledText,
                                isSelected && !disabled && styles.activeText,
                                showClearButton &&
                                    hasChevron &&
                                    styles.valueWithClearButtonAndChevron,
                            )}
                        >
                            {values[0]}
                            {values.length > 1 && ` +${values.length - 1}`}
                        </FilterLabel>
                    ) : (
                        <FilterLabel
                            size={size}
                            {...stylex.props(styles.disabledText)}
                            aria-disabled={true}
                            bold
                            aria-label={
                                placeholder === '--' ? 'No value' : placeholder
                            }
                        >
                            {placeholder}
                        </FilterLabel>
                    )}
                    {hasChevron && <ChevronDownIcon />}
                </Element>
                {showClearButton && (
                    <ClearButton
                        onClick={onClear}
                        aria-label={`clear ${label} filter`}
                        hasChevron={hasChevron}
                        isSelected={isSelected}
                    />
                )}
            </div>
        </IconContextProvider>
    );
});

Filter.displayName = 'Filter';

export type { FilterProps };
export { Filter };
