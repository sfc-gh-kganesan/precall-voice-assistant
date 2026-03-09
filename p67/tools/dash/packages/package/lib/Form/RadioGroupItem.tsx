import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { HTMLAttributes } from 'react';
import { forwardRef, useMemo } from 'react';
import { Radio as AriaRadio, SelectionIndicator } from 'react-aria-components';
import { useMergedStyles } from '../hooks';
import { Flex } from '../Layout/Flex';
import { Paragraph, SingleLine } from '../Text';
import { VisuallyHidden } from '../VisuallyHidden/VisuallyHidden';
import { generateFieldId } from './FormContext';
import { useRadioGroupContext } from './RadioGroupContext';

interface RadioGroupItemProps extends HTMLAttributes<HTMLDivElement> {
    /**
     * The label of the radio group item.
     */
    label: string;
    /**
     * The description of the radio group item.
     */
    description?: string | undefined;
    /**
     * The value of the radio group item.
     */
    value: string;
    /**
     * Whether the radio group item is disabled.
     */
    disabled?: boolean | undefined;
    /**
     * The children of the radio group item.
     */
    children?: never | undefined;
}

const styles = stylex.create({
    radio: {
        backgroundColor: {
            ':is([data-disabled])::before':
                baltoTheme.componentFormControlBackgroundDisabled,
            ':is([data-selected=true])::before':
                baltoTheme.componentFormControlKnobDefault,
            ':is([data-selected=true][data-disabled])::before':
                baltoTheme.componentFormControlKnobSelectedDisabled,
            ':not([data-selected])::before':
                baltoTheme.componentFormControlBackgroundDefault,
        },
        borderColor: {
            ':is([data-disabled])::before':
                baltoTheme.componentFormControlBorderDisabled,
            ':not([data-disabled])::before':
                baltoTheme.componentFormControlBorderDefault,
            ':not([data-disabled]):hover::before':
                baltoTheme.componentFormControlBorderHover,
            ':not([data-disabled]):is([data-focused=true][data-focus-visible=true])::before':
                baltoTheme.componentFormControlBorderActive,

            ':is([data-selected=true]):is([data-disabled])::before':
                baltoTheme.componentFormControlBackgroundSelectedDisabled,
            ':is([data-selected=true]):not([data-disabled])::before':
                baltoTheme.componentFormControlBackgroundSelectedDefault,
            ':is([data-selected=true]):not([data-disabled]):hover::before':
                baltoTheme.componentFormControlBackgroundSelectedHover,
        },
        flexBasis: '0%',
        flexGrow: 1,
        flexShrink: 0,
        minWidth: 0,

        alignItems: 'center',
        borderWidth: {
            ':is([data-selected=true])::before': 4,
            ':not([data-selected])::before': 1,
        },
        cursor: {
            default: 'pointer',
            ':is([data-disabled])': 'not-allowed',
        },
        display: 'flex',
        gap: tokens['space-gap-sm'],
        margin: 0,
        outline: {
            ':not([data-disabled]):is([data-focused=true][data-focus-visible=true])::before': `2px solid ${baltoTheme.reusableBorderFocusedActiveItem}`,
        },
        padding: 0,

        '::before': {
            borderRadius: tokens['radius-xl'],
            borderStyle: 'solid',
            content: '""',
            display: 'block',
            flexShrink: 0,
            height: tokens['size-2xs'],
            width: tokens['size-2xs'],
        },
    },
    radioWithDescription: {
        alignItems: 'start',
        '::before': {
            marginTop: tokens['space-vertical-3xs'],
        },
    },
    label: {
        color: baltoTheme.reusableTextPrimary,
        cursor: 'pointer',
    },
    labelDisabled: {
        color: baltoTheme.reusableDisabledText,
        cursor: 'not-allowed',
    },
});

const RadioGroupItem = forwardRef<HTMLDivElement, RadioGroupItemProps>(
    (props, forwardedRef) => {
        const { className, style, ...otherProps } = props;

        const radioGroupContext = useRadioGroupContext();
        const disabled = radioGroupContext.disabled || otherProps.disabled;

        const inputId = useMemo(() => generateFieldId(), []);
        const labelId = useMemo(() => generateFieldId(), []);
        const descriptionId = useMemo(() => generateFieldId(), []);

        const mergedStyles = useMergedStyles(className, style, stylex.props());

        return (
            // Not using SlottedContainer here because this is a leaf element.
            <Flex
                {...mergedStyles}
                direction="row"
                align={otherProps.description ? 'start' : 'center'}
                gap="1x"
                ref={forwardedRef}
            >
                <AriaRadio
                    id={inputId}
                    aria-label={otherProps.label}
                    aria-labelledby={labelId}
                    aria-describedby={
                        otherProps.description ? descriptionId : undefined
                    }
                    value={otherProps.value}
                    isDisabled={disabled}
                    {...stylex.props(
                        styles.radio,
                        Boolean(otherProps.description) &&
                            styles.radioWithDescription,
                    )}
                >
                    <VisuallyHidden>
                        <SelectionIndicator />
                    </VisuallyHidden>
                    <Flex direction="column" gap="0_5x">
                        <SingleLine
                            {...stylex.props(
                                styles.label,
                                disabled && styles.labelDisabled,
                            )}
                        >
                            {otherProps.label}
                        </SingleLine>
                        {otherProps.description && (
                            <Paragraph
                                variant="secondary"
                                size="small"
                                id={descriptionId}
                            >
                                {otherProps.description}
                            </Paragraph>
                        )}
                    </Flex>
                </AriaRadio>
            </Flex>
        );
    },
);
RadioGroupItem.displayName = 'RadioGroup.Item';
export type { RadioGroupItemProps };
export { RadioGroupItem };
