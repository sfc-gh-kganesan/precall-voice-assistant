import { useId } from '@react-aria/utils';
import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { baseColor } from '@snowflake/balto-themes/baseColor.stylex.js';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { ComponentProps } from 'react';
import { useCallback, useContext, useState } from 'react';
import {
    Slider as SliderPrimitive,
    SliderStateContext,
    SliderThumb as SliderThumbPrimitive,
    SliderTrack as SliderTrackPrimitive,
} from 'react-aria-components';

import { Paragraph } from '../Text';
import type { Direction } from '../types';
import type { ControlledValueComponent } from '../util/Controlled';

const styles = stylex.create({
    root: {
        alignItems: 'center',
        display: 'flex',
        height: tokens['size-2xs'],
        position: 'relative',
        touchAction: 'none',
        userSelect: 'none',
    },
    rootWithSteps: {
        paddingTop: 35,
    },
    rootWithBottomStepLabels: {
        paddingBottom: 35,
    },
    track: {
        backgroundColor: baltoTheme.componentRangeSliderTrackBackgroundDefault,
        borderRadius: tokens['radius-sm'],
        display: 'block',
        flexGrow: 1,
        height: tokens['size-5xs'],
        position: 'relative',
    },
    range: {
        borderRadius: tokens['radius-sm'],
        height: '100%',
        position: 'absolute',

        backgroundColor: {
            default: baseColor.transparent,
            ':is([data-disabled])':
                baltoTheme.componentRangeSliderRangeBackgroundDisabled,
        },
        backgroundImage: {
            default: `linear-gradient(to right, ${baltoTheme.componentRangeSliderRangeBackgroundLeft}, ${baltoTheme.componentRangeSliderRangeBackgroundRight})`,
            ':is([data-disabled])': 'none',
        },
    },
    thumb: {
        backgroundColor: {
            default: baltoTheme.reusableBackgroundComponentSelectedKnockout,
            ':is([data-disabled])':
                baltoTheme.componentRangeSliderThumbBackgroundDisabled,
        },
        borderColor: {
            default: baltoTheme.componentRangeSliderThumbBorderDefault,
            ':is([data-disabled])':
                baltoTheme.componentRangeSliderThumbBorderDisabled,
        },
        borderRadius: '100%',
        borderStyle: 'solid',
        borderWidth: 1,
        boxShadow: {
            default: baltoTheme.elevation_3BoxShadow,
            ':is([data-disabled])': 'none',
        },
        display: 'block',
        height: tokens['size-2xs'],
        top: '50%',
        width: tokens['size-2xs'],
    },
    step: {
        backgroundColor: baltoTheme.componentRangeSliderStepBackgroundDefault,
        borderColor: baltoTheme.componentRangeSliderStepBorderDefault,
        borderRadius: '100%',
        borderStyle: 'solid',
        borderWidth: 1,
        height: tokens['size-4xs'],
        position: 'absolute',
        top: '50%',
        transform: 'translate(-50%, -50%)',
        width: tokens['size-4xs'],
    },
    activeStep: {
        borderColor: baltoTheme.statusInfoUi,
    },
    stepLabel: {
        backgroundColor: baltoTheme.statusNeutralBackground,
        borderRadius: tokens['radius-xs'],
        left: '50%',
        padding: `${tokens['space-vertical-3xs']} ${tokens['space-horizontal-xs']}`,
        position: 'absolute',
        top: -13,
        width: 'max-content',
    },
    stepBottomLabel: {
        bottom: -13,
        left: '50%',
        position: 'absolute',
        width: 'max-content',
    },
});

/**
 * Converts a value to a slider value.
 */
function toSliderValueProp(value: number | [number, number] | undefined) {
    if (value === undefined) {
        return undefined;
    }

    return Array.isArray(value) ? value : [value];
}

/**
 * Checks if a value is a range value.
 */
function isRangeValue(value: number[] | undefined): value is [number, number] {
    return Boolean(value && value.length === 2);
}

/**
 * Scales a value from one range to another.
 */
function linearScale(
    input: readonly [number, number],
    output: readonly [number, number],
) {
    return (value: number) => {
        if (input[0] === input[1] || output[0] === output[1]) return output[0];
        const ratio = (output[1] - output[0]) / (input[1] - input[0]);
        return output[0] + ratio * (value - input[0]);
    };
}

/**
 * Gets the offset of a thumb in bounds.
 */
function getThumbInBoundsOffset(width: number, left: number) {
    const halfWidth = width / 2;
    const halfPercent = 50;
    const offset = linearScale([0, halfPercent], [0, halfWidth]);
    return halfWidth - offset(left);
}

interface StepProps {
    /**
     * The labels of the steps.
     */
    stepsLabels?: string[] | undefined;
    /**
     * Whether to always show the step labels.
     */
    alwaysShowStepLabels?: boolean | undefined;
}

interface SliderBaseProps
    extends StepProps,
        Omit<ComponentProps<'div'>, 'defaultValue' | 'dir'> {
    /**
     * The aria label of the thumb.
     */
    thumbAriaLabel?: string | undefined;
    /**
     * The aria labelledby of the thumb.
     */
    thumbAriaLabelledby?: string | undefined;
    /**
     * The aria label of the second thumb.
     */
    thumb2AriaLabel?: string | undefined;
    /**
     * The aria labelledby of the second thumb.
     */
    thumb2AriaLabelledby?: string | undefined;
    /**
     * Whether the slider is a range slider.
     */
    isRange?: boolean | undefined;
    /**
     * The direction of the slider.
     */
    dir?: Direction | undefined;
    /**
     * The name of the slider. Used for form submission.
     */
    name?: string | undefined;
    /**
     * If the slider is disabled.
     */
    disabled?: boolean | undefined;
    /**
     * The direction of the slider.
     */
    min?: number | undefined;
    /**
     * The maximum value of the slider.
     */
    max?: number | undefined;
    /**
     * The amount between each step.
     */
    step?: number | undefined;
    /**
     * The value of the slider. (controlled)
     */
    value?: number[] | undefined;
    /**
     * The default value of the slider. (uncontrolled)
     */
    defaultValue?: number[] | undefined;
    /**
     * The callback function that is called when the value changes. (controlled)
     */
    onValueChange?(value: number[]): void;
}

/**
 * Converts an index to a step value.
 */
function getStepValue({
    min = 0,
    step = 1,
    index,
}: {
    /**
     * The minimum value of the slider.
     */
    min: number | undefined;
    /**
     * The value of each step.
     */
    step: number | undefined;
    /**
     * The index of the step.
     */
    index: number;
}) {
    return min + index * step;
}

/**
 * Shows the value as a highlight in the slider.
 */
function SliderRange({
    isDisabled,
}: {
    /**
     * Whether the slider is disabled.
     */
    isDisabled: boolean | undefined;
}) {
    const state = useContext(SliderStateContext);

    if (!state) return null;

    return (
        <div
            {...stylex.props(styles.range)}
            data-disabled={isDisabled || undefined}
            style={
                state.values.length === 2
                    ? {
                          left: `${state.getThumbPercent(0) * 100}%`,
                          right: `${100 - state.getThumbPercent(1) * 100}%`,
                      }
                    : { width: `${state.getThumbPercent(0) * 100}%` }
            }
        />
    );
}

/**
 *
 */
function SliderBase({
    onValueChange,
    value,
    defaultValue,
    name,
    max: maxProp,
    min,
    step,
    disabled,
    stepsLabels,
    alwaysShowStepLabels,
    thumbAriaLabel,
    thumbAriaLabelledby,
    thumb2AriaLabel,
    thumb2AriaLabelledby,
    isRange,
    ...props
}: SliderBaseProps) {
    const [currentValue, setCurrentValue] = useState(
        value || defaultValue || [0],
    );
    const onValueChangeInternal = useCallback(
        (newValue: number[]) => {
            setCurrentValue(newValue);
            onValueChange?.(newValue);
        },
        [onValueChange],
    );
    const leftThumbLabelId = useId();
    const rightThumbLabelId = useId();
    const max = maxProp ?? (stepsLabels ? stepsLabels.length - 1 : undefined);

    return (
        <SliderPrimitive
            {...props}
            {...stylex.props(
                styles.root,
                stepsLabels && styles.rootWithSteps,
                stepsLabels &&
                    alwaysShowStepLabels &&
                    styles.rootWithBottomStepLabels,
            )}
            onChange={onValueChangeInternal}
            value={value}
            defaultValue={defaultValue}
            minValue={min}
            maxValue={max}
            step={step}
            isDisabled={disabled}
        >
            <SliderTrackPrimitive {...stylex.props(styles.track)}>
                <SliderRange isDisabled={disabled} />
                {stepsLabels && (
                    <>
                        {stepsLabels.map((label, index) => {
                            const percent =
                                (index / (stepsLabels.length - 1)) * 100;
                            const isFirst = index === 0;
                            const isLast = index === stepsLabels.length - 1;
                            const startValue = currentValue[0];
                            const endValue = currentValue[1];
                            const stepValue = getStepValue({
                                min,
                                step,
                                index,
                            });
                            const isInRange =
                                startValue !== undefined &&
                                endValue !== undefined
                                    ? startValue <= stepValue &&
                                      endValue >= stepValue
                                    : startValue !== undefined
                                      ? startValue >= stepValue
                                      : false;
                            const isStartValue = startValue === stepValue;
                            const isEndValue = endValue === stepValue;
                            const isActive =
                                startValue === stepValue ||
                                endValue === stepValue;
                            const offset = getThumbInBoundsOffset(16, percent);

                            return (
                                <div
                                    key={index}
                                    {...stylex.props(
                                        styles.step,
                                        isInRange && styles.activeStep,
                                    )}
                                    style={{
                                        left: `calc(${percent}% + ${isFirst || isLast ? offset : 0}px + ${isFirst ? -4 : isLast ? 4 : 0}px)`,
                                    }}
                                >
                                    {isActive && (
                                        <div
                                            {...stylex.props(styles.stepLabel)}
                                            style={{
                                                transform: isFirst
                                                    ? `translate(calc(${tokens['size-4xs']} * -1), -100%)`
                                                    : isLast
                                                      ? `translate(calc(-100% + ${tokens['size-4xs']}), -100%)`
                                                      : 'translate(-50%, -100%)',
                                            }}
                                            id={
                                                isStartValue
                                                    ? leftThumbLabelId
                                                    : isEndValue
                                                      ? rightThumbLabelId
                                                      : undefined
                                            }
                                        >
                                            <Paragraph bold size="small">
                                                {label}
                                            </Paragraph>
                                        </div>
                                    )}
                                    {alwaysShowStepLabels && (
                                        <Paragraph
                                            {...stylex.props(
                                                styles.stepBottomLabel,
                                            )}
                                            variant="secondary"
                                            style={{
                                                transform: isFirst
                                                    ? `translate(calc(${tokens['size-4xs']} * -1), 100%)`
                                                    : isLast
                                                      ? `translate(calc(-100% + ${tokens['size-4xs']}), 100%)`
                                                      : 'translate(-50%, 100%)',
                                            }}
                                        >
                                            {label}
                                        </Paragraph>
                                    )}
                                </div>
                            );
                        })}
                    </>
                )}

                <SliderThumbPrimitive
                    name={name}
                    index={0}
                    {...stylex.props(styles.thumb)}
                    aria-labelledby={
                        thumbAriaLabelledby ??
                        (isRange ? leftThumbLabelId : undefined)
                    }
                    aria-label={thumbAriaLabel}
                />

                {(isRangeValue(value) || isRangeValue(defaultValue)) && (
                    <SliderThumbPrimitive
                        name={name}
                        index={1}
                        {...stylex.props(styles.thumb)}
                        aria-labelledby={
                            thumb2AriaLabelledby ??
                            (isRange ? rightThumbLabelId : undefined)
                        }
                        aria-label={thumb2AriaLabel}
                    />
                )}
            </SliderTrackPrimitive>
        </SliderPrimitive>
    );
}

interface SliderSharedProps extends Omit<ComponentProps<'div'>, 'dir'> {
    /**
     * The name of the slider.
     */
    name?: string | undefined;
    /**
     * The minimum value of the slider.
     */
    min?: number | undefined;
    /**
     * The maximum value of the slider.
     */
    max?: number | undefined;
    /**
     * The step value of the slider.
     */
    step?: number | undefined;
    /**
     * Whether the slider is disabled.
     */
    disabled?: boolean | undefined;
}

interface SliderProps
    extends StepProps,
        Omit<SliderSharedProps, 'defaultValue'>,
        ControlledValueComponent<number> {}

/**
 * A component that displays a slider.
 */
function Slider({
    onValueChange: onValueChangeProp,
    value,
    defaultValue,
    ...props
}: SliderProps &
    Pick<SliderBaseProps, 'thumbAriaLabel' | 'thumbAriaLabelledby'>) {
    const onValueChange = useCallback(
        ([newValue]: [number]) => {
            onValueChangeProp?.(newValue);
        },
        [onValueChangeProp],
    );

    return (
        <SliderBase
            {...props}
            value={toSliderValueProp(value)}
            defaultValue={toSliderValueProp(defaultValue)}
            onValueChange={onValueChange}
        />
    );
}
Slider.displayName = 'Slider';

Slider.displayName = 'Slider';

interface RangeSliderProps
    extends StepProps,
        Omit<SliderSharedProps, 'defaultValue'>,
        Pick<
            SliderBaseProps,
            | 'thumbAriaLabel'
            | 'thumbAriaLabelledby'
            | 'thumb2AriaLabel'
            | 'thumb2AriaLabelledby'
        >,
        ControlledValueComponent<[number, number]> {}

const RangeSlider = (props: RangeSliderProps) => {
    return <SliderBase {...props} isRange />;
};

RangeSlider.displayName = 'RangeSlider';

export { RangeSlider, Slider };
export type { RangeSliderProps, SliderProps };
