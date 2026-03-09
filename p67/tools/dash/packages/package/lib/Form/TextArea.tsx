import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { IconContextProvider } from '@snowflake/stellar-icons';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { TextareaHTMLAttributes } from 'react';
import { forwardRef, useContext, useMemo, useRef } from 'react';
import { mergeProps } from 'react-aria';
import { useMergedStyles } from '../hooks';
import { BadgeIllustration } from '../internal';
import { useFieldWrapper } from '../internal/FieldWrapper/FieldWrapper';
import { useAriaLabel } from '../internal/hooks/useLabel';
import { useMergedRef } from '../internal/hooks/useMergedRef';
import { useTypeRamp } from '../internal/hooks/useTypeRamp';
import { Flex } from '../Layout';
import { FieldContext, generateFieldId } from './FormContext';
import { useAutoresizeTextarea } from './useAutoresizeTextarea';

interface TextAreaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
    /**
     * Whether the text area is full width.
     * @default false
     */
    fullWidth?: boolean | undefined;
    /**
     * Whether the text area is resizable.
     * @default false
     */
    resizable?: boolean | undefined;
    /**
     * Whether the text area should automatically resize its height based on content.
     * When enabled, the textarea will grow/shrink to fit its content.
     * @default false
     */
    autoResize?: boolean | undefined;
    /**
     * Minimum height for the textarea when autoResize is enabled (in pixels).
     * @default undefined
     */
    minHeight?: number | undefined;
    /**
     * Maximum height for the textarea when autoResize is enabled (in pixels).
     * @default undefined
     */
    maxHeight?: number | undefined;
}

const styles = stylex.create({
    textareaContainer: {
        position: 'relative',
    },
    suffixIcon: {
        flexShrink: 0,
        position: 'absolute',
        right: tokens['space-horizontal-md'],
        top: tokens['space-vertical-sm'],
    },
    textarea: {
        fontFamily: baltoTheme.fontFamilyBody,
        margin: 0,
        overflow: 'auto',
        padding: `${tokens['space-vertical-sm']} ${tokens['space-horizontal-md']}` /* 8 12 */,
        resize: 'none',

        '::placeholder': {
            color: baltoTheme.reusableTextSecondary,
        },
    },
    textareaResizable: {
        resize: 'both',
    },
    textareaFullWidth: {
        flexGrow: 1,
    },
    textareaWithSuffixIcon: {
        paddingInlineEnd: `calc(${tokens['space-horizontal-md']} + ${tokens['space-horizontal-sm']} + 1em)`,
    },
});

const TextArea = forwardRef<HTMLTextAreaElement, TextAreaProps>(
    (props, forwardedRef) => {
        const {
            className,
            style,
            'aria-label': ariaLabel,
            'aria-labelledby': ariaLabelledBy,
            resizable = false,
            fullWidth,
            autoResize = false,
            minHeight,
            maxHeight,
            value,
            ...otherProps
        } = props;
        const fieldContext = useContext(FieldContext);
        const fieldId = useMemo(
            () => fieldContext?.inputId ?? generateFieldId(),
            [fieldContext],
        );
        const { ariaLabelProps } = useAriaLabel({
            'aria-label': ariaLabel,
            'aria-labelledby': ariaLabelledBy,
        });

        const textareaRef = useRef<HTMLTextAreaElement>();
        const mergedRef = useMergedRef(textareaRef, forwardedRef);

        // Auto-resize functionality
        useAutoresizeTextarea({
            textareaRef,
            value,
            enabled: autoResize,
            minHeight,
            maxHeight,
        });

        const mergedStyles = useMergedStyles(
            className,
            style,
            stylex.props(styles.textareaContainer),
        );

        const fieldWrapper = useFieldWrapper({
            isTextArea: true,
            fieldContext: fieldContext ?? undefined,
            disabled: otherProps.disabled,
            readOnly: otherProps.readOnly,
        });
        const inputTextStyles = useTypeRamp('paragraph');

        return (
            <IconContextProvider color={baltoTheme.reusableIconDefault}>
                <Flex grow={1} {...mergedStyles}>
                    <textarea
                        id={fieldId}
                        data-testid="textarea"
                        {...mergeProps(
                            otherProps,
                            fieldWrapper.attributes,
                            ariaLabelProps,
                        )}
                        data-variant={fieldWrapper.variant}
                        value={value}
                        {...stylex.props(
                            fieldWrapper.stylexProps,
                            styles.textarea,
                            inputTextStyles,
                            resizable &&
                                !autoResize &&
                                styles.textareaResizable,
                            (fieldContext !== null || fullWidth) &&
                                styles.textareaFullWidth,
                            fieldWrapper.variant &&
                                styles.textareaWithSuffixIcon,
                        )}
                        ref={mergedRef}
                    />
                    {fieldWrapper.variant && (
                        <BadgeIllustration
                            variant={fieldWrapper.variant}
                            size="xsmall"
                            {...stylex.props(styles.suffixIcon)}
                        />
                    )}
                </Flex>
            </IconContextProvider>
        );
    },
);

TextArea.displayName = 'TextArea';
export type { TextAreaProps };
export { TextArea };
