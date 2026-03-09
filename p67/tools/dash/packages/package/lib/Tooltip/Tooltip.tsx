import { Slot } from '@radix-ui/react-slot';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { DOMAttributes, ReactElement } from 'react';
import { forwardRef, useContext } from 'react';
import { mergeProps, useFocusable, useObjectRef, usePress } from 'react-aria';
import type { TooltipTriggerComponentProps } from 'react-aria-components';
import {
    Tooltip as TooltipContent,
    TooltipTrigger,
} from 'react-aria-components';
import { BaltoThemeProvider } from '../BaltoProvider';
import { Arrow } from '../internal/Arrow';
import { ARROW_OFFSET } from '../internal/Arrow/constants';
import { useTypeRamp } from '../internal/hooks/useTypeRamp';
import { levelStyles } from '../internal/utils/levelStyles';
import type { FocusableElement } from '../types';
import type { ControlledOpenComponent } from '../util/Controlled';
import { devWarning } from '../util/dev-warning';
import { positionToPlacement } from '../util/positionToPlacement';
import { TooltipContext } from './TooltipContext';

interface TooltipProps extends ControlledOpenComponent {
    /**
     * The text of the tooltip.
     */
    text: string;
    /**
     * Changes the position of the tooltip relative to the trigger
     * @default "top"
     */
    position?: 'top' | 'bottom' | 'left' | 'right' | undefined;
    /**
     * Elements to be wrapped by tooltip container
     *
     * > NOTE: If you are passing a component as the trigger, it must correctly
     * > spread all the props passed to it to a DOM element and forward a ref.
     */
    children: ReactElement<DOMAttributes<FocusableElement>, string>;
    /**
     * Determines whether tooltip appears when trigger is hovered or focused
     * @default false
     */
    disabled?: boolean | undefined;
    /**
     * Determines whether tooltip is open by default (uncontrolled)
     */
    defaultOpen?: boolean | undefined;
    /**
     * Determines whether tooltip is open (controlled)
     */
    open?: boolean | undefined;
    /**
     * Callback function that is called when the tooltip is opened or closed (controlled)
     */
    onOpenChange?: ((open: boolean) => void) | undefined;
}

const styles = stylex.create({
    trigger: {
        cursor: 'pointer',
    },
    content: {
        maxWidth: 300,
        padding: `${tokens['space-vertical-sm']} ${tokens['space-horizontal-md']}`,
        width: 'max-content',
        wordBreak: 'break-word',
        // Match the z-index of react-aria
        zIndex: 100000,
    },
});

/**
 * A wrapper for the tooltip trigger that ensures the correct aria attributes are set.
 */
const TooltipTriggerWrapper = forwardRef<
    HTMLButtonElement,
    TooltipTriggerComponentProps &
        Omit<React.ComponentProps<'button'>, 'onClick'> & {
            /**
             * Whether the tooltip trigger is a menu trigger.
             */
            'data-menu-trigger'?: boolean | undefined;
        }
>(function TooltipTriggerWrapper({ children, ...props }, ref) {
    ref = useObjectRef(ref);
    const { pressProps } = usePress({
        ...props,
        ref,
        onPressStart: (e) => e.continuePropagation(),
        onPress: (e) => e.continuePropagation(),
        onPressEnd: (e) => e.continuePropagation(),
    });
    const { focusableProps } = useFocusable(props, ref);

    return (
        <Slot
            {...mergeProps(pressProps, focusableProps, props)}
            aria-haspopup={
                props['data-menu-trigger'] ? props['aria-haspopup'] : undefined
            }
            aria-expanded={
                props['data-menu-trigger'] ? props['aria-expanded'] : undefined
            }
            ref={ref}
        >
            {children}
        </Slot>
    );
});

const Tooltip = forwardRef<HTMLButtonElement, TooltipProps>(
    (
        {
            text,
            position = 'top',
            children,
            open,
            defaultOpen,
            onOpenChange,
            disabled,
            ...props
        },
        forwardedRef,
    ) => {
        const tooltipContext = useContext(TooltipContext);
        if (tooltipContext) {
            devWarning('Tooltip should not be nested.');
        }

        const contentStyleProps = stylex.props(
            useTypeRamp('smallParagraph'),
            levelStyles.level3Surface,
            styles.content,
        );

        const side = position;

        const openProps: Partial<TooltipTriggerComponentProps> = disabled
            ? { isOpen: false }
            : { isOpen: open, defaultOpen, onOpenChange };

        return (
            <TooltipContext.Provider value={!disabled}>
                <TooltipTrigger {...openProps} delay={500}>
                    <TooltipTriggerWrapper
                        {...props}
                        ref={forwardedRef}
                        {...stylex.props(!disabled && styles.trigger)}
                    >
                        {children}
                    </TooltipTriggerWrapper>
                    <BaltoThemeProvider>
                        <TooltipContent
                            containerPadding={4}
                            offset={ARROW_OFFSET}
                            placement={positionToPlacement(side, 'center')}
                        >
                            <div {...contentStyleProps}>
                                {text}
                                <Arrow />
                            </div>
                        </TooltipContent>
                    </BaltoThemeProvider>
                </TooltipTrigger>
            </TooltipContext.Provider>
        );
    },
);

Tooltip.displayName = 'Tooltip';

export type { TooltipProps };
export { Tooltip };
