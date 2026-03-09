import { useId } from '@react-aria/utils';
import { progressBarTheme } from '@snowflake/balto-themes/progressBarTheme.stylex.js';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { HTMLAttributes } from 'react';
import {
    Label as LabelPrimitive,
    ProgressBar as ProgressBarPrimitive,
} from 'react-aria-components';

import { useMergedStyles } from '../hooks';
import { BadgeIllustration } from '../internal';
import { Flex } from '../Layout';
import { Label } from '../Text';
import type { Size } from '../types';

const styles = stylex.create({
    root: {
        backgroundColor: progressBarTheme.backgroundDefault,
        borderRadius: 100,
        overflow: 'hidden',
        position: 'relative',
        transform: 'translateZ(0)',
        width: '100%',
    },
    small: {
        height: tokens['size-6xs'],
    },
    medium: {
        height: tokens['size-5xs'],
    },
    large: {
        height: tokens['size-4xs'],
    },
    indicator: {
        backgroundColor: progressBarTheme.filledDefault,
        borderRadius: 'inherit',
        height: '100%',
        width: '100%',
    },
    successIndicator: {
        backgroundColor: progressBarTheme.filledSuccess,
    },
    errorIndicator: {
        backgroundColor: progressBarTheme.filledError,
    },
    indicatorPosition: (percentage: number) => ({
        transform: `translateX(-${percentage}%)`,
    }),
    valueLabel: {
        fontVariantNumeric: 'tabular-nums',
    },
    valueLabelWrapper: {
        flexShrink: 0,
        height: 17,
        width: tokens['size-md'],
    },
});

interface ProgressBarProps extends HTMLAttributes<HTMLDivElement> {
    /**
     * The value of the progress bar.
     */
    value: number;
    /**
     * The maximum value of the progress bar.
     */
    max?: number | undefined;
    /**
     * Whether the progress bar has an error.
     * @default false
     */
    hasError?: boolean | undefined;
    /**
     * The helper text of the progress bar.
     */
    helperText?: string | undefined;
    /**
     * The placement of the value label.
     * @default "bar"
     */
    valuePlacement?: 'bar' | 'label' | 'hidden' | undefined;
    /**
     * The size of the progress bar.
     * @default "large"
     */
    size?: Extract<Size, 'small' | 'regular' | 'large'> | undefined;
    /**
     * The label of the progress bar.
     */
    children?: never | undefined;
    /**
     * The label of the progress bar.
     */
    label?: string | undefined;
    /**
     * The aria label of the progress bar.
     */
    'aria-label'?: string | undefined;
}

interface ProgressBarPropsWithLabel extends ProgressBarProps {
    /**
     * The label of the progress bar.
     */
    label: string;
}
interface ProgressBarPropsWithAriaLabel extends ProgressBarProps {
    /**
     * The aria label of the progress bar.
     */
    'aria-label': string;
}
interface ProgressBarPropsWithAriaLabelledby extends ProgressBarProps {
    /**
     * The aria labelledby of the progress bar.
     */
    'aria-labelledby': string;
}

type ProgressBarPropsUnified =
    | ProgressBarPropsWithLabel
    | ProgressBarPropsWithAriaLabel
    | ProgressBarPropsWithAriaLabelledby;

/**
 * A component that displays a progress bar.
 */
function ProgressBar({
    value,
    max = 100,
    hasError,
    helperText,
    valuePlacement = 'bar',
    size = 'large',
    label,
    className,
    style,
    'aria-label': ariaLabel,
    'aria-labelledby': ariaLabelledby,
    ...otherProps
}: ProgressBarPropsUnified) {
    const percentage = ((max - value) / max) * 100;
    const isComplete = value === max;
    const progressId = useId();
    const styleProps = useMergedStyles(className, style, stylex.props());

    return (
        <Flex
            asChild
            direction="column"
            gap={valuePlacement === 'label' ? '1x' : '0_5x'}
            {...otherProps}
            {...styleProps}
        >
            <ProgressBarPrimitive
                value={value}
                maxValue={max}
                aria-label={ariaLabel}
                aria-labelledby={
                    ariaLabelledby ?? (label ? progressId : undefined)
                }
            >
                {({ valueText }) => {
                    const valueDecoration = (
                        <Flex
                            align="center"
                            justify={valuePlacement === 'bar' ? 'start' : 'end'}
                            {...stylex.props(styles.valueLabelWrapper)}
                        >
                            {hasError ? (
                                <BadgeIllustration
                                    variant="critical"
                                    size="xsmall"
                                />
                            ) : isComplete ? (
                                <BadgeIllustration
                                    variant="success"
                                    size="xsmall"
                                />
                            ) : (
                                <span {...stylex.props(styles.valueLabel)}>
                                    {valueText}
                                </span>
                            )}
                        </Flex>
                    );

                    return (
                        <>
                            {label && (
                                <Flex justify="between">
                                    <Label id={progressId} asChild>
                                        <LabelPrimitive>{label}</LabelPrimitive>
                                    </Label>
                                    {valuePlacement === 'label' &&
                                        valueDecoration}
                                </Flex>
                            )}
                            <Flex gap="1x" align="center">
                                <div
                                    {...stylex.props(
                                        styles.root,
                                        size === 'small' && styles.small,
                                        size === 'regular' && styles.medium,
                                        size === 'large' && styles.large,
                                    )}
                                >
                                    <div
                                        {...stylex.props(
                                            styles.indicator,
                                            styles.indicatorPosition(
                                                percentage,
                                            ),
                                            isComplete &&
                                                styles.successIndicator,
                                            hasError && styles.errorIndicator,
                                        )}
                                    />
                                </div>
                                {valuePlacement === 'bar' && valueDecoration}
                            </Flex>
                            {helperText && (
                                <Label
                                    variant={
                                        hasError ? 'critical' : 'secondary'
                                    }
                                    size="small"
                                >
                                    {helperText}
                                </Label>
                            )}
                        </>
                    );
                }}
            </ProgressBarPrimitive>
        </Flex>
    );
}

ProgressBar.displayName = 'ProgressBar';

export type { ProgressBarProps, ProgressBarPropsUnified };
export { ProgressBar };
