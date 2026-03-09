import type { CollectionNode } from '@react-aria/collections';
import {
    setInteractionModality,
    useFocusWithin,
} from '@react-aria/interactions';
import { useEffectEvent, useLayoutEffect } from '@react-aria/utils';
import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import type { IconType } from '@snowflake/stellar-icons';
import { ChevronDownIcon, IconContextProvider } from '@snowflake/stellar-icons';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import {
    forwardRef,
    useContext,
    useImperativeHandle,
    useRef,
    useState,
} from 'react';
import { useId } from 'react-aria';
import {
    Button,
    ComboBoxStateContext,
    Input,
    Popover,
    ComboBox as ReactAriaComboBox,
    Label as ReactAriaLabel,
} from 'react-aria-components';
import { useSize } from 'use-shared-resize-observer/use-size';

import { BaltoThemeProvider } from '../BaltoProvider';
import { Divider } from '../Divider';
import { HighlightedTextProvider } from '../HighlightedText';
import { useMergedStyles } from '../hooks';
import { ClearButton } from '../internal/ClearButton/ClearButton';
import type { FieldSize } from '../internal/FieldWrapper/FieldWrapper';
import { useFieldWrapper } from '../internal/FieldWrapper/FieldWrapper';
import { useMergedRef } from '../internal/hooks/useMergedRef';
import { useTypeRamp } from '../internal/hooks/useTypeRamp';
import { SharedItem } from '../internal/SharedItem/SharedItem';
import { levelStyles } from '../internal/utils/levelStyles';
import { Flex } from '../Layout';
import { Listbox } from '../Listbox';
import type {
    ListboxLoaderIndicatorProps,
    ListboxProps,
} from '../Listbox/Listbox';
import type { ListboxOptionProps } from '../Listbox/ListboxOption';
import { ListboxItemGeneric, ListboxOption } from '../Listbox/ListboxOption';
import type { ListboxSectionProps } from '../Listbox/ListboxSection';
import { ListboxSection } from '../Listbox/ListboxSection';
import {
    normalizeListboxId,
    useListboxSelection,
} from '../Listbox/useListboxSelection';
import type { PopoverAlign } from '../Popover';
import { Label, Paragraph } from '../Text';
import type { NullableKey } from '../types';
import type {
    ControlledComponent,
    ControlledValueComponent,
} from '../util/Controlled';
import { positionToPlacement } from '../util/positionToPlacement';

const styles = stylex.create({
    popper: {
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
    },
    listBox: {
        minWidth: 0,
        padding: `${tokens['space-vertical-sm']} 0`,
    },
    inputWrapper: {
        cursor: 'text',
        flexGrow: 1,
        position: 'relative',
    },
    disabledInputWrapper: {
        cursor: 'default',
    },
    inputInner: {
        alignItems: 'center',
        display: 'grid',
        gridTemplateAreas: '"input"',
        padding: `0 ${tokens['space-horizontal-md']}`,
        position: 'relative',
        width: '100%',
    },
    inputSizer: {
        gridArea: 'input',
        opacity: 0,
        pointerEvents: 'none',
    },
    input: {
        backgroundColor: 'transparent',
        borderWidth: 0,
        gridArea: 'input',
        minWidth: 0,
        outline: 'none',
        padding: 0,
        width: '100%',

        '::placeholder': {
            color: baltoTheme.reusableTextSecondary,
        },
    },
    inputWithIcon: {
        paddingLeft: {
            ':is(*)': 36,
        },
    },
    inputHasValue: {
        paddingRight: {
            ':is(*)': 36,
        },
    },
    inputHasChevron: {
        paddingRight: {
            ':is(*)': 36,
        },
    },
    inputHasValueAndChevron: {
        paddingRight: {
            ':is(*)': 56,
        },
    },
    searchIcon: {
        left: tokens['space-horizontal-md'],
        position: 'absolute',
        top: '50%',
        transform: 'translateY(-50%)',
    },
    secondToRightIcon: {
        position: 'absolute',
        right: tokens['space-horizontal-3xl'],
        top: '50%',
        transform: 'translateY(-50%)',
    },
    rightmostIcon: {
        position: 'absolute',
        right: tokens['space-horizontal-md'],
        top: '50%',
        transform: 'translateY(-50%)',
    },
    icon: {
        alignItems: 'center',
        backgroundColor: 'transparent',
        borderWidth: 0,
        display: 'flex',
        justifyContent: 'center',
        padding: 0,
    },
    noResults: {
        display: 'flex',
        padding: `${tokens['space-vertical-sm']} ${tokens['space-horizontal-md']}`,
    },
    topOption: {
        backgroundColor: baltoTheme.surfaceLevel_3Background,
        position: 'sticky',
        top: 0,

        '::before': {
            backgroundColor: baltoTheme.surfaceLevel_3Background,
            content: "''",
            height: tokens['size-4xs'],
            left: 0,
            position: 'absolute',
            right: 0,
            top: 0,
            transform: 'translateY(-100%)',
            zIndex: 2,
        },
    },
});

/**
 * The empty state of the combobox.
 */
function EmptyState() {
    return (
        <Paragraph variant="secondary" {...stylex.props(styles.noResults)}>
            No results found
        </Paragraph>
    );
}

/** The way the comobobox handles open is not like how radix does controlled open components so we have to expose via handle */
function ComboboxHandleComponent({
    handle,
}: {
    /**
     * An imperative handle to the combobox.
     */
    handle: React.Ref<ComboboxHandle>;
}) {
    const comboboxContext = useContext(ComboBoxStateContext);

    useImperativeHandle(handle, () => ({
        open: () => comboboxContext?.open(),
        close: () => comboboxContext?.close(),
    }));

    return null;
}

/**
 * The clear button of the combobox.
 */
function ComboboxClearButton({
    inputRef,
    hasChevron,
    disabled,
}: {
    /**
     * The ref of the input element.
     */
    inputRef: React.RefObject<HTMLInputElement>;
    /**
     * Whether the combobox has a chevron.
     */
    hasChevron?: boolean | undefined;
    /**
     * Whether the combobox is disabled.
     */
    disabled: boolean | undefined;
}) {
    const comboboxState = useContext(ComboBoxStateContext);

    if (!comboboxState?.inputValue) {
        return null;
    }

    return (
        <ClearButton
            {...stylex.props(
                hasChevron ? styles.secondToRightIcon : styles.rightmostIcon,
            )}
            onClick={() => {
                comboboxState?.setInputValue('');
                inputRef.current?.focus();
            }}
            disabled={disabled}
        />
    );
}

const InputField = forwardRef<
    HTMLInputElement,
    {
        /**
         * Whether the input field has an icon.
         * @default false
         */
        hasIcon: boolean;
        /**
         * Whether the input field has a chevron.
         * @default false
         */
        hasChevron: boolean;
        /**
         * The placeholder of the input field.
         */
        placeholder?: string | undefined;
        /**
         * The size of the input field.
         * @default "regular"
         */
        size?: FieldSize | undefined;
        /**
         * Whether the input field is disabled.
         * @default false
         */
        disabled: boolean | undefined;
        /**
         * Whether to open the combobox on focus.
         * @default false
         */
        openOnFocus?: boolean | undefined;
    }
>(function InputField(
    { hasChevron, hasIcon, placeholder, size, disabled, openOnFocus },
    ref,
) {
    const fieldWrapper = useFieldWrapper({
        isTextInput: true,
        size,
        disabled,
    });
    const comboboxContext = useContext(ComboBoxStateContext);
    const inputTextStyle = useTypeRamp(
        fieldWrapper.size === 'small' ? 'smallSingleLine' : 'regularSingleLine',
    );

    return (
        <div
            {...fieldWrapper.attributes}
            {...stylex.props(
                fieldWrapper.stylexProps,
                styles.inputInner,
                hasIcon && styles.inputWithIcon,
                Boolean(comboboxContext?.inputValue) && hasChevron
                    ? styles.inputHasValueAndChevron
                    : comboboxContext?.inputValue
                      ? styles.inputHasValue
                      : hasChevron
                        ? styles.inputHasChevron
                        : undefined,
            )}
        >
            <Input
                ref={ref}
                onFocus={() => {
                    // We want focus rings and need data-focus-visible to be set to true
                    // This tells react-aria that we are in a keyboard interaction
                    setInteractionModality('keyboard');

                    if (openOnFocus && !comboboxContext?.isFocused) {
                        comboboxContext?.open();
                    }
                }}
                placeholder={placeholder}
                size={10}
                {...stylex.props(styles.input, inputTextStyle)}
            />
            <div {...stylex.props(styles.inputSizer)}>
                {comboboxContext?.inputValue || placeholder}
            </div>
        </div>
    );
});

interface ComboboxHandle {
    /**
     * Open the combobox.
     */
    open: () => void;
    /**
     * Close the combobox.
     */
    close: () => void;
}

/**
 * The highlighted text provider of the combobox.
 */
function ComboBoxHighlightedTextProvider({
    children,
    wrapperRef,
}: {
    /**
     * The children of the highlighted text provider.
     */
    children: React.ReactNode;
    /**
     * The ref of the wrapper element.
     */
    wrapperRef: HTMLElement | null;
}) {
    const state = useContext(ComboBoxStateContext);
    const inputValue = state?.inputValue || '';

    return (
        <HighlightedTextProvider
            inputValue={inputValue}
            wrapperRef={wrapperRef}
        >
            {children}
        </HighlightedTextProvider>
    );
}

/**
 * The list box of the combobox.
 */
function ComboBoxListBox<T extends object>({
    className,
    style,
    ...props
}: ListboxProps<T>) {
    const state = useContext(ComboBoxStateContext);

    const selectFirstItem = useEffectEvent(() => {
        if (!state) return;

        let firstItemKey = state.collection.getFirstKey();

        if (!firstItemKey) return;

        let item = state.collection.getItem(firstItemKey);

        while (item?.type === 'section') {
            firstItemKey = (item as CollectionNode<object>).firstChildKey;

            if (!firstItemKey) {
                break;
            }

            item = state.collection.getItem(firstItemKey);
        }

        // If opening the combobox without typing we need to set this
        // so the first option looks focused.
        setInteractionModality('keyboard');

        if (firstItemKey) {
            state?.selectionManager.setFocusedKey(firstItemKey);
            return;
        } else {
            state?.selectionManager.setFocusedKey(null);
        }
    });

    // When the input value changes, we want to select the first item
    useLayoutEffect(() => {
        // wait a frame to ensure react-aria has updated it's focused key
        const frame = requestAnimationFrame(selectFirstItem);
        return () => cancelAnimationFrame(frame);
    }, [state?.inputValue, selectFirstItem]);

    const mergedStyles = useMergedStyles(
        className,
        style,
        stylex.props(styles.listBox),
    );

    return (
        <Listbox.Root
            renderEmptyState={EmptyState}
            {...mergedStyles}
            {...props}
        />
    );
}

interface ComboBoxProps
    extends ControlledValueComponent<string>,
        ControlledComponent<'selectedValue', string | null>,
        Omit<
            React.HTMLAttributes<HTMLDivElement>,
            'defaultValue' | 'value' | 'onChange'
        > {
    /**
     * The children of the combobox.
     */
    children: React.ReactNode;
    /**
     * The label of the combobox.
     */
    label?: string | undefined;
    /**
     * Whether the combobox allows custom values (values other than the options provided).
     * @default false
     */
    allowsCustomValue?: boolean | undefined;
    /**
     * The icon of the combobox.
     */
    icon?: IconType | undefined;
    /**
     * Whether the combobox has a chevron.
     * @default false
     */
    hasChevron?: boolean | undefined;
    /**
     * An imperative handle to the combobox.
     */
    handle?: React.Ref<ComboboxHandle> | undefined;
    /**
     * The placeholder of the combobox input.
     */
    placeholder?: string | undefined;
    /**
     * The size of the combobox.
     * @default "regular"
     */
    size?: FieldSize | undefined;
    /**
     * The alignment of the combobox.
     * @default "start"
     */
    align?: PopoverAlign | undefined;
    /**
     * Whether to match the trigger width.
     * @default true
     */
    matchTriggerWidth?: boolean | undefined;
    /** Control the width of the list. The list is virtualized, so this can't be done automatically. */
    maxListWidth?: React.CSSProperties['width'] | undefined;
    /** The maxHeight specified for the overlay element. By default, it will take all space up to the current viewport height. */
    maxListHeight?: number | undefined;
    /** Open the combobox results on focus */
    openOnFocus?: boolean | undefined;
    /** Whether the combobox is disabled. */
    disabled?: boolean | undefined;
}

const Root = forwardRef<HTMLDivElement, ComboBoxProps>(function ComboBox(
    {
        children,
        value,
        defaultValue,
        onValueChange: onValueChangeProp,
        defaultSelectedValue,
        onSelectedValueChange: onSelectedValueChangeProp,
        selectedValue,
        label,
        allowsCustomValue,
        icon: Icon,
        hasChevron,
        handle,
        placeholder,
        size,
        align = 'start',
        matchTriggerWidth = true,
        maxListWidth,
        maxListHeight,
        openOnFocus = false,
        disabled,
        ...props
    },
    ref?,
) {
    const triggerWrapperRef = useRef<HTMLDivElement>(null);
    const [isFocused, setIsFocused] = useState(false);
    const { focusWithinProps } = useFocusWithin({
        onFocusWithinChange: setIsFocused,
    });
    const [wrapperRef, setWrapperRef] = useState<HTMLElement | null>(null);
    const inputRef = useRef<HTMLInputElement>(null);
    const inputWrapperRef = useRef<HTMLDivElement>(null);
    const inputWrapperSize = useSize(inputWrapperRef);
    const mergedRef = useMergedRef(ref, inputWrapperRef);
    const onSelectedValueChange = useListboxSelection({
        onSelectedIdChange: onSelectedValueChangeProp,
    });

    return (
        <Flex asChild direction="column" gap="1x" inline {...props}>
            <ReactAriaComboBox
                ref={mergedRef}
                defaultInputValue={defaultValue}
                inputValue={value}
                onInputChange={onValueChangeProp}
                defaultSelectedKey={defaultSelectedValue ?? undefined}
                selectedKey={normalizeListboxId(selectedValue)}
                onSelectionChange={
                    onSelectedValueChange as (key: NullableKey | null) => void
                }
                allowsCustomValue={allowsCustomValue}
                allowsEmptyCollection={true}
                isDisabled={disabled}
            >
                {handle && <ComboboxHandleComponent handle={handle} />}
                {label && (
                    <Label asChild>
                        <ReactAriaLabel>{label}</ReactAriaLabel>
                    </Label>
                )}
                <Flex
                    {...stylex.props(
                        styles.inputWrapper,
                        disabled && styles.disabledInputWrapper,
                    )}
                    {...focusWithinProps}
                    ref={triggerWrapperRef}
                    onClick={() => {
                        inputRef.current?.focus();
                    }}
                >
                    <InputField
                        ref={inputRef}
                        hasChevron={hasChevron || false}
                        hasIcon={!!Icon}
                        placeholder={placeholder}
                        size={size}
                        openOnFocus={openOnFocus}
                        disabled={disabled}
                    />
                    {Icon && (
                        <IconContextProvider
                            color={
                                isFocused
                                    ? baltoTheme.reusableBorderActive
                                    : undefined
                            }
                        >
                            <Icon {...stylex.props(styles.searchIcon)} />
                        </IconContextProvider>
                    )}
                    <IconContextProvider>
                        {isFocused && (
                            <ComboboxClearButton
                                hasChevron={hasChevron}
                                inputRef={inputRef}
                                disabled={disabled}
                            />
                        )}
                        {hasChevron && (
                            <Button
                                {...stylex.props(
                                    styles.icon,
                                    styles.rightmostIcon,
                                )}
                            >
                                <IconContextProvider
                                    color={
                                        disabled
                                            ? baltoTheme.reusableDisabledText
                                            : undefined
                                    }
                                >
                                    <ChevronDownIcon />
                                </IconContextProvider>
                            </Button>
                        )}
                    </IconContextProvider>
                </Flex>
                <ComboBoxHighlightedTextProvider wrapperRef={wrapperRef}>
                    <Popover
                        {...stylex.props(
                            levelStyles.level3Surface,
                            styles.popper,
                        )}
                        ref={setWrapperRef}
                        triggerRef={triggerWrapperRef}
                        placement={positionToPlacement('bottom', align)}
                        maxHeight={maxListHeight}
                        style={
                            {
                                width: matchTriggerWidth
                                    ? `${inputWrapperSize.width}px`
                                    : undefined,
                                maxWidth:
                                    typeof maxListWidth === 'undefined'
                                        ? undefined
                                        : maxListWidth,
                            } as React.CSSProperties
                        }
                    >
                        <BaltoThemeProvider>
                            <ComboBoxListBox>{children}</ComboBoxListBox>
                        </BaltoThemeProvider>
                    </Popover>
                </ComboBoxHighlightedTextProvider>
            </ReactAriaComboBox>
        </Flex>
    );
});

Root.displayName = 'ComboBox.Root';

const ComboBoxOption = forwardRef<HTMLLIElement, ListboxOptionProps>(
    function ComboBoxOption(props, ref) {
        return <ListboxOption {...props} ref={ref} />;
    },
);

ComboBoxOption.displayName = 'ComboBox.Option';

const ComboBoxSection = forwardRef<HTMLAreaElement, ListboxSectionProps>(
    function ComboBoxSection(props, ref) {
        return <ListboxSection {...props} ref={ref} />;
    },
);

ComboBoxSection.displayName = 'ComboBox.Section';

const ComboBoxTopOption = forwardRef<HTMLLIElement, ListboxOptionProps>(
    function ComboBoxTopSection(
        {
            className,
            style,
            label,
            description,
            disabled,
            textValue,
            icon: Icon,
            suffix,
            'aria-describedby': ariaDescribedBy,
            'aria-details': ariaDetails,
            'aria-label': ariaLabel,
            'aria-labelledby': ariaLabelledBy,
            id: idProp,
            ...props
        },
        ref,
    ) {
        const genId = useId();
        const id = idProp || label || genId;
        const mergedStyles = useMergedStyles(
            className,
            style,
            stylex.props(styles.topOption),
        );

        return (
            <ListboxItemGeneric
                ref={ref}
                isDisabled={disabled}
                textValue={textValue}
                aria-describedby={ariaDescribedBy}
                aria-details={ariaDetails}
                aria-label={ariaLabel}
                aria-labelledby={ariaLabelledBy}
                label={label}
                data-sticky={true}
                id={id}
                {...mergedStyles}
            >
                {({ isSelected }) => {
                    return (
                        <>
                            <SharedItem.Wrapper
                                {...props}
                                style={{
                                    marginBottom: tokens['space-vertical-3xs'],
                                }}
                                asChild
                            >
                                <div>
                                    <SharedItem.Label
                                        prefixIcon={Icon}
                                        label={label}
                                        subLabel={description}
                                        selected={isSelected}
                                        disabled={disabled}
                                        suffix={suffix}
                                    />
                                </div>
                            </SharedItem.Wrapper>
                            <Divider style={{ marginBottom: 0 }} />
                        </>
                    );
                }}
            </ListboxItemGeneric>
        );
    },
);

ComboBoxTopOption.displayName = 'ComboBox.TopOption';

const ComboBoxLoaderIndicator = forwardRef<
    HTMLDivElement,
    ListboxLoaderIndicatorProps
>(function ComboBoxLoaderIndicator(props, ref) {
    return <Listbox.LoaderIndicator {...props} ref={ref} />;
});

ComboBoxLoaderIndicator.displayName = 'ComboBox.LoadingIndicator';

export type { ComboBoxProps, ComboboxHandle };
export {
    Root,
    ComboBoxOption as Option,
    ComboBoxTopOption as TopOption,
    ComboBoxSection as Section,
    ComboBoxLoaderIndicator as LoadingIndicator,
};
