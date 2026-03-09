import { Slottable } from '@radix-ui/react-slot';
import { ClearPressResponder } from '@react-aria/interactions';
import { buttonTheme } from '@snowflake/balto-themes/buttonTheme.stylex.js';
import type { IconType } from '@snowflake/stellar-icons';
import { IconContextProvider } from '@snowflake/stellar-icons';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import { forwardRef } from 'react';
import { mergeProps, useFocusRing } from 'react-aria';

import { Flex } from '../Layout';
import type { SlottedButtonContainerProps } from '../util/SlottedContainer';
import { SlottedContainer } from '../util/SlottedContainer';
import type { ButtonSize, ButtonVariant } from './types';
import { useButtonStyles } from './useButtonStyles';

interface ButtonProps extends SlottedButtonContainerProps {
    /**
     * The visual appearance of the button.
     * @default "primary"
     */
    variant?: ButtonVariant | undefined;
    /**
     * The size of the button.
     * @default "regular"
     */
    size?: ButtonSize | undefined;
    /**
     * Whether the button is disabled.
     * @default false
     */
    disabled?: boolean | undefined;
    /**
     * Whether the button is selected.
     * @default false
     */
    selected?: boolean | undefined;
    /**
     * The icon to display before the button text.
     */
    prefixIcon?: IconType | undefined;
    /**
     * The icon to display after the button text.
     */
    suffixIcon?: IconType | undefined;
    /**
     * Whether the button is in a loading state. It will not be interactive and will show a loading spinner.
     * @default false
     */
    isLoading?: boolean | undefined;
    /**
     * Whether the button should take the full width of its container.
     * @default false
     */
    fullWidth?: boolean | undefined;
}

const shimmer = stylex.keyframes({
    '0%': { opacity: 0.2 },
    '40%': { opacity: 1 },
    '80%': { opacity: 0.2 },
    '100%': { opacity: 0.2 },
});

const styles = stylex.create({
    spinnerPrimary: {
        backgroundColor: buttonTheme.primaryBackgroundDisabled,
    },
    spinnerPrimaryCritical: {
        backgroundColor: buttonTheme.primaryCriticalBackgroundDisabled,
    },
    spinnerSecondary: {
        backgroundColor: buttonTheme.secondaryBackgroundDisabled,
    },
    spinnerTertiary: {
        backgroundColor: buttonTheme.secondaryBackgroundDisabled,
    },
    hiddenLabel: {
        opacity: 0,
    },
    spinner: {
        borderRadius: tokens['radius-sm'] /* 6 */,
        inset: 0,
        position: 'absolute',
    },
    dot: {
        animationDuration: '1s',
        animationIterationCount: 'infinite',
        animationName: shimmer,
        borderRadius: '50%',
        flexShrink: 0,
        height: tokens['size-5xs'],
        width: tokens['size-5xs'],
    },
    smallDot: {
        height: tokens['size-6xs'],
        width: tokens['size-6xs'],
    },
    primaryDot: {
        backgroundColor: buttonTheme.primaryTextDisabled,
    },
    secondaryDot: {
        backgroundColor: buttonTheme.secondaryTextDisabled,
    },
    tertiaryDot: {
        backgroundColor: buttonTheme.tertiaryTextDisabled,
    },
    primaryCriticalDot: {
        backgroundColor: buttonTheme.primaryCriticalTextDisabled,
    },
    disabledWrapper: {
        display: 'contents',
    },
    label: {
        display: {
            ':empty': 'none',
        },
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        textWrap: 'nowrap',
        whiteSpace: 'nowrap',
    },
});

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
    (props, forwardedRef) => {
        const { focusProps, isFocusVisible } = useFocusRing();
        const {
            variant = 'primary',
            fullWidth: _fullWidth,
            prefixIcon: PrefixIcon,
            suffixIcon: SuffixIcon,
            children,
            isLoading,
            disabled: disabledProp,
            selected,
            onPointerDown,
            onClick,
            ...otherProps
        } = props;
        const disabled = disabledProp || isLoading;
        const buttonStyles = useButtonStyles({ ...props, disabled });
        const iconOnly = children === undefined;
        const dotStyle = stylex.props(
            styles.dot,
            iconOnly && styles.smallDot,
            (variant === 'primary' && styles.primaryDot) ||
                (variant === 'secondary' && styles.secondaryDot) ||
                (variant === 'tertiary' && styles.tertiaryDot) ||
                styles.primaryCriticalDot,
        );

        return (
            <ClearPressResponder>
                <IconContextProvider>
                    <SlottedContainer
                        {...mergeProps(
                            {
                                ...otherProps,
                                // for button disabling, we explicitly prevent the default behavior and stop propagation
                                // to prevent the default behavior of submitting forms + potentially interfering with other components
                                onPointerDown: disabled
                                    ? (
                                          e: React.PointerEvent<HTMLButtonElement>,
                                      ) => {
                                          e.preventDefault();
                                          e.stopPropagation();
                                      }
                                    : onPointerDown,
                                onClick: disabled
                                    ? (
                                          e: React.MouseEvent<HTMLButtonElement>,
                                      ) => {
                                          e.preventDefault();
                                          e.stopPropagation();
                                      }
                                    : onClick,
                            },
                            focusProps,
                        )}
                        tag="button"
                        role="button"
                        // Actual disabled buttons make it really hard to put tooltips with the disabled state.
                        // So instead we mark the button as disabled and use the aria-disabled prop and prevent the
                        // interactions from happening. This way a user can still know about and focus on the button.
                        aria-disabled={disabled}
                        aria-pressed={selected}
                        data-focus-visible={isFocusVisible || undefined}
                        data-loading={isLoading || undefined}
                        ref={forwardedRef}
                        stylexProps={stylex.props(buttonStyles)}
                    >
                        {PrefixIcon && <PrefixIcon />}
                        {/* 
              Turn off text-overflow for strings or single children, otherwise they are relying on 
              flex w/gap for layout
            */}
                        {!props.asChild &&
                        typeof children === 'string' &&
                        props.fullWidth ? (
                            <div {...stylex.props(styles.label)}>
                                {children}
                            </div>
                        ) : (
                            <Slottable>{children}</Slottable>
                        )}
                        {SuffixIcon && <SuffixIcon />}
                        {isLoading && (
                            <Flex
                                justify="center"
                                align="center"
                                {...stylex.props(
                                    isLoading && styles.spinner,
                                    variant === 'primary' &&
                                        styles.spinnerPrimary,
                                    variant === 'secondary' &&
                                        styles.spinnerSecondary,
                                    variant === 'tertiary' &&
                                        styles.spinnerTertiary,
                                    variant === 'primary-critical' &&
                                        styles.spinnerPrimaryCritical,
                                )}
                            >
                                <Flex gap="0_25x" align="center">
                                    <div
                                        {...dotStyle}
                                        style={{ animationDelay: '-0.2s' }}
                                    />
                                    <div {...dotStyle} />
                                    <div
                                        {...dotStyle}
                                        style={{ animationDelay: '0.2s' }}
                                    />
                                </Flex>
                            </Flex>
                        )}
                    </SlottedContainer>
                </IconContextProvider>
            </ClearPressResponder>
        );
    },
);

Button.displayName = 'Button';
export { Button };
