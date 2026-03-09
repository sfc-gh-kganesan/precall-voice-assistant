import { createLeafComponent, ItemNode } from '@react-aria/collections';
import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import {
    ChevronDownIcon,
    IconContextProvider,
    type IconType,
} from '@snowflake/stellar-icons';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { ForwardedRef } from 'react';
import React, {
    Fragment,
    forwardRef,
    useContext,
    useMemo,
    useRef,
} from 'react';
import { mergeProps } from 'react-aria';
import type { ButtonProps } from 'react-aria-components';
import {
    Autocomplete,
    Button,
    FieldError,
    FieldErrorContext,
    ListStateContext,
    Popover,
    Select as ReactAriaSelect,
    SelectValue,
    useFilter,
} from 'react-aria-components';
import * as ReactIs from 'react-is';
import { useSize } from 'use-shared-resize-observer/use-size';

import { BaltoThemeProvider } from '../BaltoProvider';
import { FieldContext, generateFieldId } from '../Form/FormContext';
import { useMergedStyles } from '../hooks';
import { BadgeIllustration } from '../internal';
import { ClearButton } from '../internal/ClearButton/ClearButton';
import {
    type FieldSize,
    useFieldWrapper,
} from '../internal/FieldWrapper/FieldWrapper';
import { useAriaLabel } from '../internal/hooks/useLabel';
import { LoaderIndicator, LoadingSentinel } from '../internal/LoaderIndicator';
import { forwardedRefGeneric } from '../internal/utils/forwardRefGeneric';
import { levelStyles } from '../internal/utils/levelStyles';
import type {
    ListboxLoaderIndicatorProps,
    ListboxSectionProps,
} from '../Listbox';
import { Listbox } from '../Listbox';
import type { ListboxOptionProps } from '../Listbox/ListboxOption';
import { ListboxSection } from '../Listbox/ListboxSection';
import { SearchInput, useTypeRamp } from '../main';
import type { PopoverAlign } from '../Popover';
import { SingleLine } from '../Text';
import { TooltipContext } from '../Tooltip/TooltipContext';
import type { Key, NullableKey, Size } from '../types';
import type {
    ControlledOpenComponent,
    ControlledValueComponent,
} from '../util/Controlled';
import { SizeContext } from '../util/context';
import { devError } from '../util/dev-warning';
import { positionToPlacement } from '../util/positionToPlacement';

const styles = stylex.create({
    contents: {
        display: 'contents',
    },
    select: {
        display: 'inline-flex',
        flexDirection: 'column',
        gap: tokens['space-gap-sm'],
        position: 'relative',
    },
    clearButton: {
        position: 'absolute',
        right: tokens['space-horizontal-3xl'],
        top: '50%',
        transform: 'translateY(-50%)',
    },
    wrapper: {
        color: {
            ':is([disabled])': baltoTheme.reusableDisabledText,
            ":not([disabled]):has([data-placeholder='true'])":
                baltoTheme.reusableTextSecondary,
        },
        cursor: {
            default: 'pointer',
            ':is([disabled])': 'not-allowed',
        },
    },
    chevron: {
        height: tokens['size-2xs'],
        width: tokens['size-2xs'],

        color: {
            default: baltoTheme.reusableTextPrimary,
            ":is([data-placeholder='true'] *)": baltoTheme.reusableTextPrimary,
            ':is([disabled] *)': baltoTheme.reusableDisabledText,
        },
    },
    popper: {
        display: 'flex',
        flexDirection: {
            default: 'column',
            ":is([data-placement='top'])": 'column-reverse',
        },
        minWidth: 200,
        overflow: 'hidden',
    },
    list: {
        padding: `${tokens['space-vertical-sm']} 0`,
    },
    popperSearchable: {
        paddingTop: 0,
    },
    triggerValue: {
        alignItems: 'center',
        display: 'flex',
        flexGrow: 1,
        minWidth: 0,
    },
    noResults: {
        padding: tokens['space-vertical-md'],
        paddingBottom: tokens['space-vertical-sm'],
    },
    disabledTriggerValue: {
        color: baltoTheme.reusableDisabledText,
    },

    wrapperHasClearButton: {
        paddingRight: {
            ':has([data-select-value])': tokens['space-horizontal-xl'],
        },
    },
    searchInput: {
        flexShrink: 0,
    },
    value: {
        alignItems: 'center',
        color: baltoTheme.reusableTextPrimary,
        cursor: 'text',
        display: 'flex',
        gap: tokens['space-gap-xs'],
        margin: 0,
        overflow: 'hidden',
        padding: 0,
        textWrap: 'nowrap',
        whiteSpace: 'nowrap',
        whiteSpaceCollapse: 'collapse',
    },
    valueItems: {
        flexGrow: 1,
        minWidth: 0,
    },
    lastPart: {
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
    },
});

interface ItemData {
    /**
     * The id of the item.
     */
    id: string;
    /**
     * The label of the item.
     */
    label: string;
    /**
     * The text value of the item.
     */
    textValue: string;
}

/**
 * The label of the select value.
 */
function SelectValueLabel({
    size,
    selectedItems,
}: {
    /**
     * The size of the multi-select value.
     */
    size?: FieldSize | undefined;
    /**
     * The selected items of the select.
     */
    selectedItems: Array<ItemData>;
}) {
    const labelTextStyles = useTypeRamp(
        size === 'small' ? 'smallSingleLine' : 'regularSingleLine',
    );
    const availableAreaRef = useRef<HTMLDivElement>(null);
    const upperCaseTextStyles = useTypeRamp(
        size === 'small' ? 'allCapsSmall' : 'allCaps',
    );
    const upperCaseClassName = stylex.props(upperCaseTextStyles).className;
    const items = useMemo(() => {
        if (typeof window === 'undefined') {
            return { visibleItems: selectedItems, removed: 0 };
        }

        const visibleItems = [...selectedItems];

        let removed = 0;
        let lastRemovedItem: ItemData | undefined;

        while (visibleItems.length) {
            const el = document.createElement('div');

            el.style.width = '100%';
            el.style.textWrap = 'auto';

            for (let i = 0; i < visibleItems.length; i++) {
                const item = visibleItems[i];
                const span = document.createElement('span');
                const valueIsAllCaps =
                    item?.textValue?.toUpperCase() === item?.textValue;

                span.textContent = item?.textValue || '';

                if (valueIsAllCaps) {
                    span.className = upperCaseClassName || '';
                }

                if (i < visibleItems.length - 1) {
                    span.textContent += ', ';
                }

                el.appendChild(span);
            }

            if (removed > 0) {
                const span = document.createElement('span');
                span.textContent = `, +${removed}`;
                el.appendChild(span);
            }

            availableAreaRef?.current?.appendChild(el);

            const computedStyle = window.getComputedStyle(el);
            const lineHeight = parseInt(computedStyle.lineHeight);

            // When we have an all caps option the client height will take the children
            // span heights into account and be 20px. Which is taller than the line height of 16px.
            // If the height is larger than 2 lines than the text is broken, if its less it is not.
            const hasBrokenLineOfText = el.clientHeight >= lineHeight * 2;

            availableAreaRef?.current?.removeChild(el);

            if (!hasBrokenLineOfText || visibleItems.length === 1) {
                // Add the last removed item back so that gets clipped with an ellipsis.
                if (lastRemovedItem) {
                    visibleItems.push(lastRemovedItem);
                    removed--;
                }
                break;
            }

            lastRemovedItem = visibleItems.pop();
            removed++;
        }
        return { visibleItems, removed };
    }, [selectedItems, upperCaseClassName]);

    return (
        <div {...stylex.props(labelTextStyles, styles.value)} data-select-value>
            <div
                ref={availableAreaRef}
                {...stylex.props(styles.valueItems, styles.lastPart)}
            >
                {items.visibleItems.map((item, index) => {
                    const valueIsAllCaps =
                        item?.textValue?.toUpperCase() === item?.textValue;

                    return (
                        <Fragment key={item.id}>
                            <span
                                {...stylex.props(
                                    valueIsAllCaps
                                        ? upperCaseTextStyles
                                        : undefined,
                                )}
                            >
                                {item?.textValue}
                            </span>
                            {index < items.visibleItems.length - 1 && ', '}
                        </Fragment>
                    );
                })}
            </div>
            {items.removed > 0 && <span>{`+${items.removed}`}</span>}
        </div>
    );
}

/**
 * The clear button of the select.
 */
function SelectClearButton({
    disabled,
}: {
    /**
     *
     */
    disabled: boolean | undefined;
}) {
    const state = React.useContext(ListStateContext);

    if (!state?.selectionManager.selectedKeys.size) {
        return null;
    }

    const hasValue = Array.from(state.selectionManager.selectedKeys).some(
        (k) => k !== '',
    );

    if (!hasValue) {
        return null;
    }

    return (
        <ClearButton
            data-clear-button
            onClick={() => state?.selectionManager.setSelectedKeys([])}
            disabled={disabled}
            {...stylex.props(styles.clearButton)}
        />
    );
}

/**
 * The trigger of the select.
 */
const Trigger = forwardRef(function Trigger(
    {
        size: sizeProp,
        disabled,
        icon: Icon,
        hasClearButton,
        ...props
    }: Pick<SelectBaseProps, 'size' | 'disabled' | 'icon' | 'hasClearButton'> &
        ButtonProps,
    ref: ForwardedRef<HTMLButtonElement>,
) {
    const contextSize = useContext(SizeContext);
    const size = sizeProp || contextSize || 'regular';
    const fieldErrorContext = useContext(FieldErrorContext);
    const fieldContext = useContext(FieldContext);
    const fieldWrapper = useFieldWrapper({
        size,
        fieldContext: {
            ...fieldContext,
            error:
                (fieldErrorContext &&
                    Boolean(fieldErrorContext.validationErrors.length)) ||
                fieldContext?.error,
        },
        disabled,
    });

    return (
        <Button
            ref={ref}
            isDisabled={disabled}
            data-variant={fieldWrapper.variant}
            {...mergeProps(fieldWrapper.attributes as ButtonProps, props)}
            {...stylex.props(fieldWrapper.stylexProps, styles.wrapper)}
        >
            <IconContextProvider>
                {React.isValidElement(Icon) ? (
                    Icon
                ) : ReactIs.isValidElementType(Icon) ? (
                    <Icon />
                ) : typeof Icon === 'string' || typeof Icon === 'number' ? (
                    Icon
                ) : null}
            </IconContextProvider>
            <SelectValue<ItemData>
                {...stylex.props(
                    styles.triggerValue,
                    disabled && styles.disabledTriggerValue,
                    hasClearButton && styles.wrapperHasClearButton,
                )}
            >
                {({ selectedItems, defaultChildren, isPlaceholder }) => {
                    if (isPlaceholder) {
                        return (
                            <SingleLine size={size} variant="secondary">
                                {defaultChildren}
                            </SingleLine>
                        );
                    }

                    const activeItems = selectedItems.filter(
                        (item): item is ItemData => item !== null,
                    );

                    return (
                        <SelectValueLabel
                            selectedItems={activeItems}
                            size={size}
                        />
                    );
                }}
            </SelectValue>
            {fieldWrapper.variant && (
                <BadgeIllustration
                    variant={fieldWrapper.variant}
                    size="xsmall"
                />
            )}
            <IconContextProvider
                color={disabled ? baltoTheme.reusableDisabledText : undefined}
            >
                <ChevronDownIcon
                    aria-hidden="true"
                    {...stylex.props(styles.chevron)}
                />
            </IconContextProvider>
        </Button>
    );
});

interface SelectBaseProps
    extends ControlledOpenComponent,
        // HTML selects cannot have custom styling. The underlying elements rendered by react-aria
        // are divs, so that's why the HTML props are div props.
        Omit<
            React.HTMLAttributes<HTMLDivElement>,
            'defaultValue' | 'value' | 'onChange'
        > {
    /** The maxHeight specified for the overlay element. By default, it will take all space up to the current viewport height. */
    maxListHeight?: number | undefined;
    /**
     * The name of the select.
     */
    name?: string | undefined;
    /**
     * Whether the select is required.
     * @default false
     */
    required?: boolean | undefined;
    /**
     * The icon of the select.
     */
    icon?: IconType | React.ReactNode | undefined;
    /**
     * Whether the select is disabled.
     * @default false
     */
    disabled?: boolean | undefined;
    /**
     * The children of the select.
     */
    children: React.ReactNode;
    /**
     * The placeholder of the select.
     */
    placeholder?: string | undefined;
    /**
     * The size of the select.
     * @default "regular"
     */
    size?: FieldSize | undefined;
    /**
     * The alignment of the select.
     * @default "start"
     */
    align?: PopoverAlign | undefined;
    /**
     * The selection mode of the select.
     * @default "single"
     */
    selectionMode?: 'single' | 'multiple' | undefined;
    /**
     * The size of the menu.
     * @default "regular"
     */
    menuSize?: Extract<Size, 'small' | 'regular'> | undefined;
    /**
     * Whether the select is searchable.
     * @default false
     */
    isSearchable?: boolean | undefined;
    /**
     * The search value of the select.
     */
    searchValue?: string | undefined;
    /**
     * The default search value of the select.
     */
    defaultSearchValue?: string | undefined;
    /**
     * The function to call when the search value changes.
     */
    onSearchValueChange?: ((searchValue: string) => void) | undefined;
    /** Whether to render a clear button in the trigger to easily clear the selected value. */
    hasClearButton?: boolean | undefined;

    [key: `data-${string}`]: string | undefined;
}

interface SelectPropsWithMatchTriggerWidth extends SelectBaseProps {
    /**
     * Whether the select should match the width of the trigger.
     * @default false
     */
    matchTriggerWidth?: true | undefined;
    /**
     * The maximum width of the list.
     */
    maxListWidth?: never | undefined;
}

interface SelectPropsWithMaxListWidth extends SelectBaseProps {
    /**
     * The maximum width of the list.
     */
    maxListWidth?: string | number | undefined;
    /**
     * Whether the select should match the width of the trigger.
     * @default false
     */
    matchTriggerWidth?: false | undefined;
}

type SelectWithListDimensions =
    | SelectPropsWithMatchTriggerWidth
    | SelectPropsWithMaxListWidth;

type SingleSelectWithModeProp<T> = SelectWithListDimensions &
    ControlledValueComponent<T> & {
        /**
         * The selection mode of the single select.
         * @default "single"
         */
        selectionMode?: 'single' | undefined;
    };

type MultiSelectWithModeProps<T> = SelectWithListDimensions &
    ControlledValueComponent<T> & {};

type Input = Key[] | NullableKey;
type SelectProps<T extends Input> =
    | MultiSelectWithModeProps<T>
    | SingleSelectWithModeProp<T>;

const Root = forwardedRefGeneric(
    <T extends Input>(
        {
            selectionMode,
            children,
            disabled,
            required,
            value,
            defaultValue,
            onValueChange,
            open,
            defaultOpen,
            onOpenChange,
            'aria-label': ariaLabel,
            'aria-labelledby': ariaLabelledby,
            'aria-describedby': ariaDescribedby,
            'aria-details': ariaDetails,
            name,
            id,
            placeholder,
            isSearchable,
            searchValue,
            defaultSearchValue,
            onSearchValueChange,
            maxListWidth,
            maxListHeight,
            align = 'start',
            matchTriggerWidth = typeof maxListWidth === 'undefined',
            className,
            style,
            menuSize: menuSizeProp,
            hasClearButton,
            ...props
        }: SelectProps<T>,
        ref?: React.Ref<HTMLDivElement>,
    ) => {
        const fieldContext = useContext(FieldContext);

        if (fieldContext?.inputId && id) {
            devError('id should be set on Field instead of Select.');
        }

        const fieldId = useMemo(
            () => fieldContext?.inputId ?? id ?? generateFieldId(),
            [fieldContext, id],
        );
        const { ariaLabelProps } = useAriaLabel({
            'aria-label': ariaLabel,
            'aria-labelledby': ariaLabelledby,
        });
        const contextSize = useContext(SizeContext);
        const mergedStyles = useMergedStyles(
            className,
            style,
            stylex.props(styles.select),
        );
        const menuSize = menuSizeProp ?? contextSize ?? 'regular';
        const buttonRef = useRef<HTMLButtonElement>(null);
        const buttonSize = useSize({
            ref: buttonRef,
            options: { box: 'border-box' },
        });
        const popoverRef = useRef<HTMLDivElement>(null);
        const { contains } = useFilter({ sensitivity: 'base' });
        const menuStyles = useMemo(() => {
            // The list is virtualized so it's content has no bearing on the layout.
            // When a maxListWidth is provided, we need to make the list stretch as wide as it can.
            // This makes it so the maxListWidth does somethings, but also means the list might be wider than needed,
            // since it's full controlled by the maxListWidth.
            if (maxListWidth) {
                return {
                    width: '100vw',
                    maxWidth: `min(${typeof maxListWidth === 'number' ? `${maxListWidth}px` : maxListWidth}, calc(100vw - ${tokens['size-md']}))`,
                };
            }

            if (matchTriggerWidth) {
                return {
                    width: buttonSize.width,
                };
            }

            return {};
        }, [matchTriggerWidth, buttonSize.width, maxListWidth]);

        return (
            <ReactAriaSelect
                ref={ref}
                isInvalid={fieldContext?.error}
                // If an empty string is passed treat that as no value selected
                value={value}
                defaultValue={defaultValue}
                onChange={(value) => onValueChange?.(value as T)}
                isRequired={required}
                isOpen={open}
                defaultOpen={defaultOpen}
                onOpenChange={onOpenChange}
                {...ariaLabelProps}
                aria-describedby={
                    fieldContext?.descriptionId ?? ariaDescribedby
                }
                aria-details={ariaDetails}
                name={name}
                id={fieldId}
                placeholder={placeholder}
                isDisabled={disabled}
                validationBehavior="native"
                selectionMode={selectionMode}
                {...mergedStyles}
            >
                <Trigger
                    ref={buttonRef}
                    {...(props as ButtonProps)}
                    hasClearButton={hasClearButton}
                    disabled={disabled}
                />
                {hasClearButton && <SelectClearButton disabled={disabled} />}
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
                <SizeContext.Provider value={menuSize}>
                    <TooltipContext.Provider value={false}>
                        <BaltoThemeProvider>
                            <Popover
                                ref={popoverRef}
                                {...stylex.props(
                                    levelStyles.level3Surface,
                                    styles.popper,
                                    isSearchable && styles.popperSearchable,
                                )}
                                maxHeight={maxListHeight}
                                style={menuStyles}
                                placement={positionToPlacement('bottom', align)}
                                containerPadding={8}
                            >
                                {isSearchable ? (
                                    <Autocomplete
                                        filter={contains}
                                        inputValue={searchValue}
                                        defaultInputValue={defaultSearchValue}
                                        onInputChange={onSearchValueChange}
                                    >
                                        <SearchInput
                                            variant="secondary"
                                            autoFocus
                                            aria-label="Search options"
                                            fullWidth={matchTriggerWidth}
                                            {...stylex.props(
                                                styles.searchInput,
                                            )}
                                        />
                                        <Listbox.Root
                                            {...stylex.props(styles.list)}
                                            renderEmptyState={() => (
                                                <SingleLine
                                                    {...stylex.props(
                                                        styles.noResults,
                                                    )}
                                                >
                                                    No results found
                                                </SingleLine>
                                            )}
                                        >
                                            {children}
                                        </Listbox.Root>
                                    </Autocomplete>
                                ) : (
                                    <Listbox.Root
                                        {...stylex.props(styles.list)}
                                    >
                                        {children}
                                    </Listbox.Root>
                                )}
                            </Popover>
                        </BaltoThemeProvider>
                    </TooltipContext.Provider>
                </SizeContext.Provider>
            </ReactAriaSelect>
        );
    },
);

// @ts-expect-error - Couldn't get displayName to work with forwardedRefGeneric
// We can't cast to any because it influences the generated type
Root.displayName = 'Select.Root';

const SelectOption = forwardRef<HTMLLIElement, ListboxOptionProps>(
    function SelectOption(props, ref) {
        if (!props.label) {
            devError(
                'Select.Option must have a readable label. If you need an option that is represented by an empty string, provide the value as the ID and include a label that is not empty.',
            );
        }

        return <Listbox.Option {...props} ref={ref} />;
    },
);

SelectOption.displayName = 'Select.Option';

type SelectOptionProps = ListboxOptionProps;

const SelectLoaderIndicator = createLeafComponent(
    ItemNode,
    function ComboBoxLoaderIndicator(
        {
            onLoadMore,
            isLoading,
            label,
            'aria-label': ariaLabel,
            ...props
        }: ListboxLoaderIndicatorProps,
        ref: ForwardedRef<HTMLDivElement>,
    ) {
        const state = useContext(ListStateContext);

        if (!state || !isLoading) {
            return null;
        }

        return (
            <div {...props} tabIndex={-1} role="option" ref={ref}>
                <LoadingSentinel
                    onLoadMore={onLoadMore}
                    collection={state.collection}
                />
                <LoaderIndicator aria-label={ariaLabel} label={label} />
            </div>
        );
    },
);

// eslint-disable-next-line @typescript-eslint/no-explicit-any
(SelectLoaderIndicator as any).displayName = 'Select.LoadingIndicator';

const SelectSection = forwardRef<HTMLAreaElement, ListboxSectionProps>(
    function SelectSection(props, ref) {
        return <ListboxSection {...props} ref={ref} />;
    },
);

SelectSection.displayName = 'Select.Section';

export type { SelectProps, SelectOptionProps };
export {
    Root,
    SelectOption as Option,
    SelectLoaderIndicator as LoadingIndicator,
    SelectSection as Section,
};
