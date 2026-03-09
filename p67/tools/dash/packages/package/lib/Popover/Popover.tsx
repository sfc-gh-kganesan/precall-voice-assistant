import { useControlledState } from '@react-stately/utils';
import { baseDimensionNumberStyles } from '@snowflake/balto-tokens';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { DOMAttributes, ReactElement, ReactNode } from 'react';
import { forwardRef, useCallback, useContext, useEffect, useRef } from 'react';
import { mergeProps, Pressable } from 'react-aria';
import {
    Dialog,
    DialogTrigger,
    Popover as PopoverPrimitive,
} from 'react-aria-components';
import { BaltoThemeProvider } from '../BaltoProvider';
import { Arrow } from '../internal/Arrow';
import { ARROW_OFFSET } from '../internal/Arrow/constants';
import { useAriaLabel } from '../internal/hooks/useLabel';
import { levelStyles } from '../internal/utils/levelStyles';
import { TooltipContext } from '../Tooltip/TooltipContext';
import type { FocusableElement } from '../types';
import type { ControlledOpenComponent } from '../util/Controlled';
import { devWarning } from '../util/dev-warning';
import { positionToPlacement } from '../util/positionToPlacement';
import { PopoverContext, PopoverTriggerContext } from './PopoverContext';
import type { PopoverAlign, PopoverPosition, PopoverSize } from './types';

/** Short delay to allow moving to popover content */
const SHOW_ON_HOVER_DELAY = 150;

type PopoverVariant = 'critical' | 'inconsequential' | 'persistent';

interface PopoverBaseProps extends ControlledOpenComponent {
    /**
     * The trigger of the popover.
     *
     * > NOTE: If you are passing a component as the trigger, it must correctly
     * > spread all the props passed to it to a DOM element and forward a ref.
     */
    trigger: ReactElement<DOMAttributes<FocusableElement>, string>;
    /**
     * The position of the popover.
     * @default "top"
     */
    position?: PopoverPosition | undefined;
    /**
     * The alignment of the popover.
     * @default "center"
     */
    align?: PopoverAlign | undefined;
    /**
     * The size of the popover.
     * @default "small"
     */
    size?: PopoverSize | 'auto' | undefined;
    /**
     * The children of the popover.
     */
    children: ReactNode;
    /**
     * The aria label of the popover.
     */
    'aria-label'?: string | undefined;
    /**
     * The aria labelledby of the popover.
     */
    'aria-labelledby'?: string | undefined;
    /**
     * The variant of the popover.
     *
     * - `critical`: The popover is modal and cannot be dismissed by clicking outside.
     * - `inconsequential`: The popover is modal and is easily dismissible.
     * - `persistent`: The popover is non-modal and cannot be dismissed by clicking outside. You need to provide the user with a way to dismiss the popover. Use this variant sparingly, it can impact the accessibility of the page.
     *
     * @default "inconsequential"
     */
    variant?: PopoverVariant | undefined;
    /** Render the content without any padding */
    fullBleed?: boolean | undefined;
    /** Render the content without an arrow */
    showArrow?: boolean | undefined;
    /** Whether to show open the popover when the trigger is hovered */
    showOnHover?: boolean | undefined;
}

interface PopoverAriaLabelProps extends PopoverBaseProps {
    /**
     * The aria label of the popover.
     */
    'aria-label': string;
}

interface PopoverAriaLabelledbyProps extends PopoverBaseProps {
    /**
     * The aria labelledby of the popover.
     */
    'aria-labelledby': string;
}

type PopoverProps = PopoverAriaLabelProps | PopoverAriaLabelledbyProps;

const styles = stylex.create({
    content: {
        outline: 'none',
        overflow: 'visible',
        padding: tokens['space-vertical-lg'],
        width: 'max-content',
    },
    contentSmall: {
        width: 260,
    },
    contentMedium: {
        width: 300,
    },
    contentLarge: {
        width: 480,
    },
    trigger: {
        cursor: 'pointer',
    },
    fullBleed: {
        padding: 0,
    },
});

/**
 * Add listeners to the trigger and popover content to handle hover events.
 */
function useShowOnHover({
    showOnHover,
    setIsPopoverOpen,
    variant,
}: {
    /**
     * The variant of the popover.
     */
    variant: PopoverVariant | undefined;
    /**
     * Whether to show the popover when the trigger is hovered.
     */
    showOnHover: boolean | undefined;
    /**
     * Set the open state of the popover.
     */
    setIsPopoverOpen: (isOpen: boolean) => void;
}): {
    /**
     * Whether the popover should close.
     */
    checkShouldClose: () => boolean;
    /**
     * Props for the trigger.
     */
    triggerProps: {
        /**
         * Handler for the mouse enter event.
         */
        onMouseEnter?: (() => void) | undefined;
        /**
         * Handler for the mouse leave event.
         */
        onMouseLeave?: (() => void) | undefined;
    };
    /**
     * Props for the popover content.
     */
    popoverContentProps: {
        /**
         * Handler for the mouse enter event.
         */
        onMouseEnter?: (() => void) | undefined;
        /**
         * Handler for the mouse leave event.
         */
        onMouseLeave?: (() => void) | undefined;
    };
} {
    const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const justOpenedRef = useRef(false);
    const justOpenedTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
        null,
    );
    const checkShouldClose = useCallback(() => !justOpenedRef.current, []);

    useEffect(() => {
        /**
         * When the user presses escape we dont want to prevent the close of the popover.
         */
        function handleKeyDown(event: KeyboardEvent) {
            if (event.key !== 'Escape') return;

            justOpenedRef.current = false;
            if (justOpenedTimeoutRef.current) {
                clearTimeout(justOpenedTimeoutRef.current);
                justOpenedTimeoutRef.current = null;
            }
        }

        document.addEventListener('keydown', handleKeyDown, { capture: true });

        return () => {
            document.removeEventListener('keydown', handleKeyDown);
        };
    }, []);

    const handleMouseEnter = useCallback(() => {
        if (timeoutRef.current) {
            clearTimeout(timeoutRef.current);
            timeoutRef.current = null;
        }

        timeoutRef.current = setTimeout(() => {
            setIsPopoverOpen(true);

            if (justOpenedTimeoutRef.current) {
                clearTimeout(justOpenedTimeoutRef.current);
            }

            justOpenedRef.current = true;
            justOpenedTimeoutRef.current = setTimeout(() => {
                justOpenedRef.current = false;
            }, 500);
        }, SHOW_ON_HOVER_DELAY);
    }, [setIsPopoverOpen]);

    const handleMouseLeave = useCallback(() => {
        if (timeoutRef.current) {
            clearTimeout(timeoutRef.current);
        }

        timeoutRef.current = setTimeout(() => {
            setIsPopoverOpen(false);
        }, SHOW_ON_HOVER_DELAY);
    }, [setIsPopoverOpen]);

    const handlePopoverMouseEnter = useCallback(() => {
        if (timeoutRef.current) {
            clearTimeout(timeoutRef.current);
            timeoutRef.current = null;
        }
    }, []);

    const handlePopoverMouseLeave = useCallback(() => {
        if (variant === 'persistent') {
            return;
        }
        setIsPopoverOpen(false);
    }, [setIsPopoverOpen, variant]);

    if (!showOnHover) {
        return {
            checkShouldClose,
            triggerProps: {},
            popoverContentProps: {},
        };
    }

    return {
        checkShouldClose,
        triggerProps: {
            onMouseEnter: handleMouseEnter,
            onMouseLeave: handleMouseLeave,
        },
        popoverContentProps: {
            onMouseEnter: handlePopoverMouseEnter,
            onMouseLeave: handlePopoverMouseLeave,
        },
    };
}

const Popover = forwardRef<HTMLButtonElement, PopoverProps>(
    (props, forwardedRef) => {
        const popoverContext = useContext(PopoverContext);

        if (popoverContext) {
            devWarning(
                'Popover should not be nested. Think about how you can refactor your code for a more accessible solution. Reach out to the design system team if you need help.',
            );
        }

        const {
            trigger,
            position = 'top',
            size = 'small',
            'aria-label': ariaLabel,
            'aria-labelledby': ariaLabelledby,
            variant = 'inconsequential',
            children,
            open: openProp,
            defaultOpen = false,
            onOpenChange: onOpenChangeProp,
            align,
            fullBleed,
            showArrow,
            showOnHover,
            ...otherProps
        } = props;

        const [open, setOpen] = useControlledState(
            openProp,
            defaultOpen,
            onOpenChangeProp,
        );
        const popoverContentRef = useRef<HTMLDivElement>(null);
        const { triggerProps, popoverContentProps, checkShouldClose } =
            useShowOnHover({
                variant,
                showOnHover,
                setIsPopoverOpen: setOpen,
            });
        const onOpenChange = useCallback(
            (open: boolean) => {
                if (!checkShouldClose()) {
                    return;
                }

                setOpen(open);
            },
            [setOpen, checkShouldClose],
        );

        const { onMouseEnter, onMouseLeave } = popoverContentProps;
        useEffect(() => {
            if (!open) {
                return;
            }

            const popover = popoverContentRef.current;

            if (!popover || !onMouseEnter || !onMouseLeave) {
                return;
            }

            popover.addEventListener('mouseenter', onMouseEnter);
            popover.addEventListener('mouseleave', onMouseLeave);

            return () => {
                popover.removeEventListener('mouseenter', onMouseEnter);
                popover.removeEventListener('mouseleave', onMouseLeave);
            };
        }, [onMouseEnter, onMouseLeave, open]);

        const { ariaLabelProps } = useAriaLabel({
            'aria-label': ariaLabel,
            'aria-labelledby': ariaLabelledby,
        });

        return (
            <PopoverContext.Provider value={true}>
                <DialogTrigger isOpen={open} onOpenChange={onOpenChange}>
                    <PopoverTriggerContext.Provider value={true}>
                        <Pressable
                            ref={forwardedRef}
                            {...mergeProps(otherProps, triggerProps)}
                            {...stylex.props(styles.trigger)}
                        >
                            {trigger}
                        </Pressable>
                    </PopoverTriggerContext.Provider>
                    <TooltipContext.Provider value={false}>
                        <PopoverPrimitive
                            ref={popoverContentRef}
                            containerPadding={4}
                            data-popover-variant={variant}
                            offset={
                                showArrow
                                    ? ARROW_OFFSET
                                    : baseDimensionNumberStyles.spacing_1x
                            }
                            isNonModal={
                                variant === 'persistent'
                                    ? true
                                    : Boolean(showOnHover)
                            }
                            placement={positionToPlacement(position, align)}
                            isKeyboardDismissDisabled={variant === 'critical'}
                            shouldCloseOnInteractOutside={() =>
                                variant === 'critical' ||
                                variant === 'persistent' ||
                                showOnHover
                                    ? false
                                    : true
                            }
                        >
                            <BaltoThemeProvider>
                                <Dialog
                                    {...mergeProps(ariaLabelProps)}
                                    {...stylex.props(
                                        styles.content,
                                        levelStyles.level3Surface,
                                        size === 'small' && styles.contentSmall,
                                        size === 'medium' &&
                                            styles.contentMedium,
                                        size === 'large' && styles.contentLarge,
                                        fullBleed && styles.fullBleed,
                                    )}
                                >
                                    {children}
                                    {showArrow && <Arrow />}
                                </Dialog>
                            </BaltoThemeProvider>
                        </PopoverPrimitive>
                    </TooltipContext.Provider>
                </DialogTrigger>
            </PopoverContext.Provider>
        );
    },
);

Popover.displayName = 'Popover';
export type { PopoverProps };
export { Popover };
