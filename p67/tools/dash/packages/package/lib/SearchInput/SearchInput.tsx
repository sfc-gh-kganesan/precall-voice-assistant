import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { IconContextProvider, SearchIcon } from '@snowflake/stellar-icons';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { HTMLAttributes } from 'react';
import { forwardRef, useContext, useEffect, useRef, useState } from 'react';
import { mergeProps, useFocusWithin } from 'react-aria';
import type { SearchFieldProps } from 'react-aria-components';
import { Input, InputContext, SearchField } from 'react-aria-components';

import { ClearButton } from '../internal/ClearButton/ClearButton';
import type { FieldSize } from '../internal/FieldWrapper/FieldWrapper';
import { useFieldWrapper } from '../internal/FieldWrapper/FieldWrapper';
import { useTypeRamp } from '../internal/hooks/useTypeRamp';
import { type ControlledValueComponent, useMergedStyles } from '../main';

const styles = stylex.create({
    secondarySearch: {
        borderColor: {
            default: 'transparent',
            ':focus-within': baltoTheme.reusableBorderActive,
        },
    },
    workspaceSearch: {
        backgroundColor: baltoTheme.reusableBackgroundRowHover,
        borderColor: 'transparent',
        borderRadius: tokens['radius-md'],
        borderWidth: 0,
    },
    search: {
        backgroundColor: 'transparent',
        borderWidth: 0,
        gridArea: 'input',
        height: '100%',
        minWidth: 0,
        outline: 'none',
        padding: 0,

        '::-webkit-search-cancel-button': {
            display: 'none',
        },

        color: {
            default: baltoTheme.reusableTextPrimary,
            '::placeholder': baltoTheme.reusableTextSecondary,
        },
    },
    inputWrapper: {
        alignItems: 'center',
        display: 'grid',
        flexGrow: 1,
        gridTemplateAreas: '"input"',
        overflow: 'visible',
        position: 'relative',
    },
    fullWidthInputWrapper: {
        flexGrow: 1,
        minWidth: 0,
        overflow: 'auto',
        // Native html inputs allow for scroll but never show the scrollbar
        // This is needed for MacOs where scrollbars can be set to "always show"
        scrollbarWidth: 'none',
        width: '100%',
    },
    fullWidthSearch: {
        width: '100%',
    },
    inputSizer: {
        gridArea: 'input',
        opacity: 0,
        pointerEvents: 'none',
        width: 'max-content',
    },
});

/**
 * The component that renders the clear button.
 */
function SearchClearButton({
    disabled,
}: {
    /**
     * Whether the clear button is disabled.
     */
    disabled: boolean | undefined;
}) {
    const inputProps = useContext(
        InputContext,
    ) as React.ComponentProps<'input'>;

    if (!inputProps.value) {
        return null;
    }

    return (
        <ClearButton
            disabled={disabled}
            onClick={() =>
                inputProps.onChange?.({
                    target: { value: '' },
                } as React.ChangeEvent<HTMLInputElement>)
            }
        />
    );
}

/**
 * Takes up space to make the input more responsive.
 */
function InputMeasurer({
    placeholder,
    ...props
}: {
    /**
     * The placeholder of the input.
     */
    placeholder: React.ReactNode;
} & Omit<React.HTMLAttributes<HTMLDivElement>, 'children'>) {
    const inputProps = useContext(
        InputContext,
    ) as React.ComponentProps<'input'>;

    return <div {...props}>{inputProps.value || placeholder}</div>;
}

interface SearchInputProps
    extends ControlledValueComponent<string>,
        Omit<
            HTMLAttributes<HTMLDivElement>,
            | 'value'
            | 'defaultValue'
            | 'spellCheck'
            | 'onChange'
            | 'onSubmit'
            | 'children'
        > {
    /**
     * The variant of the search input.
     */
    variant?: 'regular' | 'secondary' | 'workspace' | undefined;
    /**
     * The disabled state of the search input.
     * @default false
     */
    disabled?: boolean | undefined;
    /**
     * The placeholder of the search input.
     */
    placeholder?: string | undefined;
    /**
     * The callback function that is called when the form is submitted.
     */
    onSubmit?: ((value: string) => void) | undefined;
    /**
     * The size of the search input.
     */
    size?: FieldSize | undefined;
    /**
     * Whether the input should take the full width of the parent.
     * @default false
     */
    fullWidth?: boolean | undefined;
    /**
     * Whether to hide the icon.
     * @default true
     */
    showSearchIcon?: boolean | undefined;
}

const SearchInput = forwardRef<HTMLDivElement, SearchInputProps>(
    (
        {
            className,
            style,
            disabled,
            variant,
            autoFocus,
            placeholder,
            size,
            fullWidth,
            showSearchIcon = true,
            onValueChange,
            ...props
        },
        ref,
    ) => {
        const [isFocused, setIsFocused] = useState(false);
        const { focusWithinProps } = useFocusWithin({
            onFocusWithinChange: setIsFocused,
        });
        const fieldWrapper = useFieldWrapper({
            size,
            isTextInput: true,
            disabled,
        });
        const inputRef = useRef<HTMLInputElement>(null);
        const mergedStyles = useMergedStyles(
            className,
            style,
            stylex.props(
                fieldWrapper.stylexProps,
                variant === 'secondary' && styles.secondarySearch,
                variant === 'workspace' && styles.workspaceSearch,
                fullWidth && styles.fullWidthSearch,
            ),
        );
        const inputTextStyle = useTypeRamp(
            fieldWrapper.size === 'small'
                ? 'smallSingleLine'
                : 'regularSingleLine',
        );

        useEffect(() => {
            if (autoFocus && inputRef.current) {
                inputRef.current.focus();
            }
        }, [autoFocus]);

        return (
            <SearchField
                isDisabled={disabled}
                ref={ref}
                {...mergeProps(
                    fieldWrapper.attributes as SearchFieldProps,
                    props,
                    focusWithinProps,
                )}
                onChange={onValueChange}
                {...mergedStyles}
            >
                {showSearchIcon && (
                    <IconContextProvider
                        color={
                            isFocused
                                ? baltoTheme.reusableBorderActive
                                : variant === 'workspace'
                                  ? baltoTheme.reusableDisabledText
                                  : undefined
                        }
                    >
                        <SearchIcon />
                    </IconContextProvider>
                )}
                <div
                    {...stylex.props(
                        styles.inputWrapper,
                        fullWidth && styles.fullWidthInputWrapper,
                    )}
                >
                    <Input
                        ref={inputRef}
                        placeholder={placeholder}
                        size={10}
                        {...stylex.props(
                            styles.search,
                            inputTextStyle,
                            fullWidth && styles.fullWidthSearch,
                        )}
                    />
                    <InputMeasurer
                        placeholder={placeholder}
                        {...stylex.props(styles.inputSizer, inputTextStyle)}
                    />
                </div>
                <SearchClearButton disabled={disabled} />
            </SearchField>
        );
    },
);

SearchInput.displayName = 'SearchInput';

export type { SearchInputProps };
export { SearchInput };
