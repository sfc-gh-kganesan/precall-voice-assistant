import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { HTMLAttributes } from 'react';
import { forwardRef, useContext, useMemo } from 'react';
import { mergeProps, useFocusRing } from 'react-aria';
import type { SwitchProps as SwitchPrimitiveProps } from 'react-aria-components';
import { Switch as SwitchPrimitive } from 'react-aria-components';
import { useMergedStyles } from '../hooks';
import { useAriaLabel } from '../internal/hooks/useLabel';
import { FieldContext, generateFieldId } from './FormContext';

interface SwitchProps extends HTMLAttributes<HTMLLabelElement> {
    /**
     * The default checked value of the switch.
     */
    defaultChecked?: boolean | undefined;
    /**
     * Whether the switch is disabled.
     * @default false
     */
    disabled?: boolean | undefined;
    /**
     * The checked value of the switch.
     */
    checked?: boolean | undefined;
    /**
     * The callback function that is called when the checked value of the switch changes.
     */
    onCheckedChange?: ((value: boolean) => void) | undefined;
    /**
     * The children of the switch.
     */
    children?: never | undefined;
    // div doesn't have name prop so we need to pass them to the Radix component
    /**
     * The name of the switch.
     */
    name?: string | undefined;
}

const styles = stylex.create({
    switch: {
        backgroundColor: {
            default: baltoTheme.componentFormControlBackgroundUnselected,
            ':is([data-disabled])':
                baltoTheme.componentFormControlBackgroundDisabled,
            ':is([data-selected]:not([data-disabled]))':
                baltoTheme.componentFormControlBackgroundSelectedDefault,
            ':is([data-selected]:not([data-disabled])):hover':
                baltoTheme.componentFormControlBackgroundSelectedHover,
            ':is([data-selected][data-disabled])':
                baltoTheme.componentFormControlBackgroundSelectedDisabled,
        },
        borderRadius: tokens['radius-md'] /* 8 */,
        borderWidth: 0,
        cursor: {
            default: 'pointer',
            ':is([data-disabled])': 'not-allowed',
        },
        display: 'inline-block',
        height: tokens['size-2xs'],
        margin: 0,
        outline: {
            ":not([data-disabled]):is([data-focus-visible='true'])": `2px solid ${baltoTheme.reusableBorderFocusedActiveItem}`,
        },
        padding: 0,
        position: 'relative',
        transition: 'background-color 150ms ease-in-out',
        width: tokens['size-md'],
    },
    switchKnob: {
        backgroundColor: {
            default: baltoTheme.componentFormControlKnobDefault,
            ':is([data-disabled])': baltoTheme.componentFormControlKnobDisabled,
            ':is([data-selected][data-disabled])':
                baltoTheme.componentFormControlKnobSelectedDisabled,
        },
        borderRadius: tokens['radius-md'] /* 8 */,
        borderWidth: 0,
        display: 'inline-block',
        height: tokens['size-3xs'],
        left: {
            default: tokens['space-horizontal-3xs'] /* 2 */,
            ':is([data-selected])': `calc(${tokens['space-horizontal-md']} + ${tokens['space-horizontal-xs']})`,
        },
        position: 'absolute',
        top: tokens['space-vertical-3xs'] /* 2 */,
        transition: 'left 0.1s ease-in-out',
        width: tokens['size-3xs'],
    },
    labelDisabled: {
        color: baltoTheme.reusableDisabledText,
        cursor: 'not-allowed',
    },
});

// TODO (APPS-48781): Add optional helper text as per UX.
const Switch = forwardRef<HTMLLabelElement, SwitchProps>(
    (props, forwardedRef) => {
        const {
            className,
            style,
            defaultChecked,
            disabled,
            checked,
            onCheckedChange,
            'aria-label': ariaLabel,
            'aria-labelledby': ariaLabelledBy,
            name,
            id: idProp,
            ...otherProps
        } = props;

        const { focusProps, isFocusVisible } = useFocusRing({});
        const fieldContext = useContext(FieldContext);
        const inputId = useMemo(
            () => fieldContext?.inputId ?? idProp ?? generateFieldId(),
            [fieldContext, idProp],
        );
        const { ariaLabelProps } = useAriaLabel({
            'aria-label': ariaLabel,
            'aria-labelledby': ariaLabelledBy,
            id: idProp,
        });
        const stateProps: SwitchPrimitiveProps = {
            defaultSelected: defaultChecked,
            isDisabled: disabled,
            isSelected: checked,
            onChange: onCheckedChange,
        };
        const styleProps = useMergedStyles(
            className,
            style,
            stylex.props(styles.switch),
        );

        return (
            <SwitchPrimitive
                id={inputId}
                name={name}
                data-focus-visible={isFocusVisible}
                {...mergeProps(
                    stateProps,
                    focusProps,
                    ariaLabelProps,
                    otherProps,
                    styleProps,
                )}
                ref={forwardedRef}
            >
                {({ isDisabled, isSelected }) => (
                    <div
                        {...stylex.props(styles.switchKnob)}
                        data-selected={isSelected || undefined}
                        data-disabled={isDisabled || undefined}
                    />
                )}
            </SwitchPrimitive>
        );
    },
);
Switch.displayName = 'Switch';
export type { SwitchProps };
export { Switch };
