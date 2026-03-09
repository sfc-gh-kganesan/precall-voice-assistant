import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { fieldTheme } from '@snowflake/balto-themes/fieldTheme.stylex.js';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import type {
    CompiledStyles,
    InlineStyles,
    StyleXArray,
} from '@stylexjs/stylex';
import * as stylex from '@stylexjs/stylex';
import type { DOMAttributes } from 'react';
import { useContext, useState } from 'react';
import { mergeProps, useFocusRing, useFocusWithin } from 'react-aria';

import type { FieldContextType } from '../../Form/FormContext';
import { SizeContext } from '../../main';
import type { StatusVariant } from '../../Status';
import type { FocusableElement, Size } from '../../types';
import type { IllustrationType } from '../BadgeIllustration';
import { useTypeRamp } from '../hooks/useTypeRamp';

const styles = stylex.create({
    field: {
        alignItems: 'center',
        display: 'inline-flex',
        overflow: 'hidden',
        textAlign: 'left',

        backgroundColor: {
            default: baltoTheme.componentFormControlBackgroundDefault,
            ':is([disabled])':
                baltoTheme.componentFormControlBackgroundDisabled,
        },
        borderColor: {
            default: baltoTheme.componentFormControlBorderDefault,

            ":is([data-focus-visible='true']):not([data-variant])":
                baltoTheme.componentFormControlBorderActive,
            ':is([disabled])': baltoTheme.componentFormControlBorderDisabled,
            ":is([data-hovered='true']):not(:focus):not([disabled]):not([data-variant])":
                baltoTheme.componentFormControlBorderHover,
            ':hover:not([disabled]):not(:focus):not([data-variant])':
                baltoTheme.componentFormControlBorderHover,
            ":is([data-variant='critical'])":
                baltoTheme.componentFormControlBorderCritical,
            ":is([data-variant='critical']):hover":
                baltoTheme.componentFormControlBorderCritical,
            ":is([data-variant='caution'])":
                baltoTheme.componentFormControlBorderCaution,
            ":is([data-variant='success'])":
                baltoTheme.componentFormControlBorderSuccess,
        },
        borderRadius: fieldTheme.borderRadiusDefault,
        borderStyle: 'solid',
        borderWidth: 1,
        boxShadow: {
            ":is([data-focus-visible='true']):not([data-variant])": `0 0 0 2px ${baltoTheme.reusableBorderFocusedActiveItem}`,
            ":is([data-focus-visible='true']):is([data-variant='critical'])": `0 0 0 2px ${baltoTheme.reusableBorderFocusedCriticalItem}`,
            ":is([data-focus-visible='true']):is([data-variant='success'])": `0 0 0 2px ${baltoTheme.reusableBorderFocusedSuccessItem}`,
            ":is([data-focus-visible='true']):is([data-variant='caution'])": `0 0 0 2px ${baltoTheme.reusableBorderFocusedWarningItem}`,
        },
        color: {
            default: baltoTheme.reusableTextPrimary,
            ':is([disabled])': baltoTheme.reusableDisabledText,
        },
        cursor: {
            ':is([disabled])': 'not-allowed',
        },

        outline: {
            default: 'none',
            ':hover': 'none',
        },
    },
    small: {
        gap: tokens['space-gap-2xs'],
        height: tokens['size-sm'],
        minHeight: tokens['size-sm'],
        paddingInlineEnd: tokens['space-horizontal-sm'],
        paddingInlineStart: tokens['space-horizontal-sm'],
    },
    regular: {
        gap: tokens['space-gap-sm'],
        height: tokens['size-md'],
        minHeight: tokens['size-md'],
        paddingInlineEnd: tokens['space-horizontal-md'],
        paddingInlineStart: tokens['space-horizontal-md'],
    },
    textarea: {
        height: 'initial',
    },
    disabledBackground: {
        backgroundColor: baltoTheme.componentFormControlBackgroundDisabled,
        borderColor: baltoTheme.componentFormControlBorderDisabled,
        cursor: {
            default: 'not-allowed',
            ':is(*) *': 'not-allowed',
        },
    },
    disabledText: {
        color: {
            default: baltoTheme.reusableDisabledText,
            ':is(*) *': baltoTheme.reusableDisabledText,
        },
    },
    readOnly: {},
});

type FieldSize = Extract<Size, 'small' | 'regular'>;
interface FieldWrapperProps {
    /**
     * The size of the field.
     */
    size: FieldSize;
    /**
     * Whether the field is focused.
     */
    hasFocus: boolean;
    /**
     * The attributes of the field.
     */
    attributes: DOMAttributes<FocusableElement>;
    /**
     * The stylex props of the field.
     */
    stylexProps: StyleXArray<
        | (null | undefined | CompiledStyles)
        | boolean
        | Readonly<[CompiledStyles, InlineStyles]>
    >;
    /**
     * The variant of the field.
     */
    variant: IllustrationType;
}
/**
 * The function that returns the field wrapper props.
 */
function useFieldWrapper(options: {
    /**
     * Whether the field is a text input.
     */
    isTextInput?: boolean | undefined;
    /**
     * Whether the field is a text area.
     */
    isTextArea?: boolean | undefined;
    /**
     * The field context.
     */
    fieldContext?:
        | Pick<FieldContextType, 'error' | 'warning' | 'success'>
        | undefined;
    /**
     * The size of the field.
     */
    size?: FieldSize | undefined;
    /**
     * Whether the field is disabled.
     */
    disabled?: boolean | undefined;
    /**
     * Whether the field is read only.
     */
    readOnly?: boolean | undefined;
}): FieldWrapperProps {
    const contextSize = useContext(SizeContext);
    const size =
        'size' in options
            ? options.size || contextSize || 'regular'
            : undefined;
    const { isFocusVisible, focusProps } = useFocusRing({
        isTextInput: options.isTextInput,
    });
    const [hasFocusWithin, setHasFocusWithin] = useState(false);
    const { focusWithinProps } = useFocusWithin({
        onFocusWithinChange: setHasFocusWithin,
    });

    const hasFocus = isFocusVisible || hasFocusWithin;

    const textStyles = useTypeRamp(
        size === 'small' ? 'smallSingleLine' : 'regularSingleLine',
    );

    return {
        hasFocus,
        attributes: {
            ...mergeProps(focusProps, focusWithinProps),
            'data-focus-visible': hasFocus,
        } as DOMAttributes<FocusableElement>,
        stylexProps: [
            styles.field,
            options.isTextArea && styles.textarea,
            size === 'small' && styles.small,
            size === 'regular' && styles.regular,
            (options.disabled || options.readOnly) && styles.disabledBackground,
            options.disabled && styles.disabledText,
            options.readOnly && styles.readOnly,
            textStyles,
        ],
        size: size || 'regular',
        variant: (options.fieldContext?.error
            ? 'critical'
            : options.fieldContext?.success
              ? 'success'
              : options.fieldContext?.warning
                ? 'caution'
                : undefined) as Extract<
            StatusVariant,
            'success' | 'caution' | 'critical'
        >,
    };
}

export type { FieldSize, FieldWrapperProps };
export { useFieldWrapper };
