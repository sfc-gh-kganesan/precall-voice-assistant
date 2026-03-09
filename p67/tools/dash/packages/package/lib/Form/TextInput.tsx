import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { IconContextProvider, type IconType } from '@snowflake/stellar-icons';
import * as stylex from '@stylexjs/stylex';
import type { InputHTMLAttributes } from 'react';
import { forwardRef, useContext, useMemo, useRef } from 'react';
import { mergeProps } from 'react-aria';
import { useMergedStyles } from '../hooks';
import { BadgeIllustration } from '../internal';
import type { FieldSize } from '../internal/FieldWrapper/FieldWrapper';
import { useFieldWrapper } from '../internal/FieldWrapper/FieldWrapper';
import { useAriaLabel } from '../internal/hooks/useLabel';
import { useMergedRef } from '../internal/hooks/useMergedRef';
import { useTypeRamp } from '../internal/hooks/useTypeRamp';
import { Flex } from '../Layout';
import { FieldContext, generateFieldId } from './FormContext';

interface TextInputProps extends InputHTMLAttributes<HTMLInputElement> {
    /**
     * The type of the input.
     */
    type?:
        | 'email'
        | 'number'
        | 'password'
        | 'tel'
        | 'text'
        | 'time'
        | 'url'
        | undefined;
    /**
     * The prefix icon of the input.
     */
    prefixIcon?: IconType | undefined;
    /**
     * Whether the input is full width.
     * @default false
     */
    fullWidth?: boolean | undefined;
    /**
     * The children of the input.
     */
    children?: never | undefined;
    // We don't want to override the native html size attribute
    /**
     * The size of the input.
     */
    sizeVariant?: FieldSize | undefined;
}

const styles = stylex.create({
    input: {
        backgroundColor: 'transparent',
        borderWidth: 0,
        color: baltoTheme.reusableTextPrimary,
        flexGrow: 1,
        margin: 0,
        minWidth: 0,
        outline: 'none',
        padding: 0,

        '::placeholder': {
            color: baltoTheme.reusableTextSecondary,
        },
    },
    inputFullWidth: {
        flexGrow: 1,
        width: '100%',
    },
    /* eslint-disable @stylexjs/valid-styles */
    time: {
        '::-webkit-calendar-picker-indicator': {
            display: 'none',
        },
    },
    badge: {
        flexShrink: 0,
    },
});

const TextInput = forwardRef<HTMLInputElement, TextInputProps>(
    (props, forwardedRef) => {
        const {
            className,
            style,
            type = 'text',
            prefixIcon: PrefixIcon,
            'aria-label': ariaLabel,
            'aria-labelledby': ariaLabelledBy,
            fullWidth,
            sizeVariant,
            ...otherProps
        } = props;
        const fieldContext = useContext(FieldContext);
        const inputId = useMemo(
            () => fieldContext?.inputId ?? generateFieldId(),
            [fieldContext],
        );
        const { ariaLabelProps } = useAriaLabel({
            'aria-label': ariaLabel,
            'aria-labelledby': ariaLabelledBy,
        });

        const inputRef = useRef<HTMLInputElement>();
        const mergedRef = useMergedRef(inputRef, forwardedRef);
        const fieldWrapper = useFieldWrapper({
            isTextInput: true,
            fieldContext: fieldContext ?? undefined,
            size: sizeVariant,
            disabled: otherProps.disabled,
            readOnly: otherProps.readOnly,
        });
        const mergedStyles = useMergedStyles(
            className,
            style,
            stylex.props(
                fieldWrapper.stylexProps,
                (fieldContext !== null || fullWidth) && styles.inputFullWidth,
            ),
        );
        const inputTextStyle = useTypeRamp(
            fieldWrapper.size === 'small'
                ? 'smallSingleLine'
                : 'regularSingleLine',
        );

        return (
            <IconContextProvider color={baltoTheme.reusableIconDefault}>
                <Flex
                    grow={1}
                    data-variant={fieldWrapper.variant}
                    {...fieldWrapper.attributes}
                    {...mergedStyles}
                >
                    {PrefixIcon && <PrefixIcon />}
                    <input
                        id={inputId}
                        data-testid="input"
                        {...mergeProps(otherProps, ariaLabelProps)}
                        type={type}
                        {...stylex.props(
                            styles.input,
                            inputTextStyle,
                            type === 'time' && styles.time,
                        )}
                        ref={mergedRef}
                    />
                    {fieldWrapper.variant && (
                        <BadgeIllustration
                            variant={fieldWrapper.variant}
                            size="xsmall"
                            {...stylex.props(styles.badge)}
                        />
                    )}
                </Flex>
            </IconContextProvider>
        );
    },
);

TextInput.displayName = 'TextInput';
export type { TextInputProps };
export { TextInput };
