import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef, isValidElement } from 'react';
import { mergeProps } from 'react-aria';
import type { ButtonProps } from 'react-aria-components';
import {
    Button,
    ButtonContext,
    Pressable,
    useContextProps,
} from 'react-aria-components';

import { useMergedStyles } from '../hooks';
import { useTypeRamp } from '../internal/hooks/useTypeRamp';
import type { SlottedContainerProps } from '../util/SlottedContainer';

type AccordionTriggerProps<T extends keyof ReactHTML = 'button'> = Omit<
    SlottedContainerProps<T>,
    'role'
>;

const styles = stylex.create({
    trigger: {
        backgroundColor: {
            default: baltoTheme.interactionPressableDefaultBackground,
            ':hover': baltoTheme.interactionPressableHoveredBackground,
            '::selection': baltoTheme.interactionPressablePressedBackground,
        },
        borderRadius: 'unset',
        borderWidth: 0,
        color: baltoTheme.interactionPressableDefaultContent,
        margin: 'unset',
        padding: `${tokens['space-vertical-sm']} ${tokens['space-horizontal-xs']}`,
        textAlign: 'left',
    },
});

const AccordionTrigger = forwardRef<HTMLButtonElement, AccordionTriggerProps>(
    ({ className, style, asChild, children, ...props }, forwardedRef) => {
        const textStyles = useTypeRamp('smallParagraphBold');
        const styleProps = useMergedStyles(
            className,
            style,
            stylex.props(textStyles, styles.trigger),
        );
        const [accordionTriggerProps, ref] = useContextProps(
            { ...props, slot: 'trigger' },
            forwardedRef,
            ButtonContext,
        );

        if (asChild) {
            return (
                <Pressable
                    {...mergeProps(
                        accordionTriggerProps as ButtonProps,
                        styleProps,
                    )}
                    ref={ref}
                >
                    {isValidElement(children) ? (
                        children
                    ) : (
                        <button>{children}</button>
                    )}
                </Pressable>
            );
        }

        return (
            <Button
                {...mergeProps(
                    accordionTriggerProps as ButtonProps,
                    styleProps,
                )}
                ref={ref}
            >
                {children}
            </Button>
        );
    },
);

AccordionTrigger.displayName = 'Accordion.Trigger';
export type { AccordionTriggerProps };
export { AccordionTrigger };
