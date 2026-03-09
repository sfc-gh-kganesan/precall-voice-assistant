import { createContext } from '@radix-ui/react-context';
import { Slottable } from '@radix-ui/react-slot';
import {
    ariaHideOutside,
    useOverlayFocusContain,
    usePreventScroll,
} from '@react-aria/overlays';
import { useEffectEvent, useExitAnimation } from '@react-aria/utils';
import { useControlledState } from '@react-stately/utils';
import type { DOMAttributes } from '@react-types/shared';
import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { SlideLeftIcon, SlideRightIcon } from '@snowflake/stellar-icons';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { ReactElement, ReactNode } from 'react';
import { forwardRef, useContext, useEffect, useRef } from 'react';
import { Overlay, useOverlay } from 'react-aria';
import {
    Button,
    Dialog,
    DialogTrigger,
    Heading as HeadingPrimitive,
    OverlayTriggerStateContext,
    Pressable,
} from 'react-aria-components';
import { useOverlayTriggerState } from 'react-stately';

import { IconButton } from '../Button';
import { useMergedStyles } from '../hooks';
import { useMergedRef } from '../internal/hooks/useMergedRef';
import { levelStyles } from '../internal/utils/levelStyles';
import type { FlexProps } from '../Layout';
import { Flex } from '../Layout';
import type { FocusableElement, Size, SlottedContainerProps } from '../main';
import { BaltoThemeProvider } from '../main';
import { Heading } from '../Text';
import type { ControlledOpenComponent } from '../util/Controlled';

type DrawerSide = 'right' | 'left';
type DrawerVariant = 'inconsequential' | 'critical' | 'persistent';

const slideFromLeft = stylex.keyframes({
    from: {
        transform: 'translate3d(-100%, 0, 0)',
    },
    to: {
        transform: 'translate3d(0, 0, 0)',
    },
});

const slideToLeft = stylex.keyframes({
    to: {
        transform: 'translate3d(-100%, 0, 0)',
    },
});

const slideFromRight = stylex.keyframes({
    from: {
        transform: 'translate3d(100%, 0, 0)',
    },
    to: {
        transform: 'translate3d(0, 0, 0)',
    },
});

const slideToRight = stylex.keyframes({
    to: {
        transform: 'translate3d(100%, 0, 0)',
    },
});

const [DrawerContext, useDrawerContext] = createContext<{
    /**
     * The side the drawer should open from.
     */
    side: DrawerSide;
    /**
     * The variant of the drawer.
     */
    variant?: DrawerVariant | undefined;
}>('Drawer');

type DrawerSize = Extract<Size, 'small' | 'medium' | 'large'> | 'auto';

interface DrawerBaseProps extends ControlledOpenComponent {
    /**
     * The side the drawer should open from.
     */
    side?: DrawerSide | undefined;
    /**
     * The size of the drawer.
     */
    size?: DrawerSize | undefined;
    /**
     * The children of the drawer.
     */
    children: ReactNode;
    /**
     * The type of drawer.
     *
     * - `inconsequential`: Inconsequential sidepanels are purely informational and can be closed at any time.
     * - `critical`: These panels are seen as more required, the user can only dismiss via the close button or
     *               an action in the footer. If you're using this type your should also be controlling the open
     *               state of the drawer.
     * - `persistent`: This panel will stay open as the user interacts with the page. They must manually close it.
     *
     * @default "inconsequential"
     */
    variant?: DrawerVariant | undefined;
    /**
     * The class name of the drawer.
     */
    className?: string | undefined;
    /**
     * The style of the drawer.
     */
    style?: React.CSSProperties | undefined;
    /**
     * A label describing the dialog.
     */
    'aria-describedby'?: string | undefined;
    /**
     * An additional label to describe the dialog.
     * This should only be used if the dialog doesn't have a header, title or trigger.
     */
    'aria-label'?: string | undefined;
    /**
     * An id of an element that labels the dialog.
     * This defaults to the trigger
     */
    'aria-labelledby'?: string | undefined;
    /**
     * A test id for the dialog.
     */
    'data-testid'?: string | undefined;
}

interface DrawerTriggerlessProps extends DrawerBaseProps {
    /**
     * The trigger of the drawer.
     *
     * > NOTE: If you are passing a component as the trigger, it must correctly
     * > spread all the props passed to it to a DOM element and forward a ref.
     */
    trigger?: never | undefined;
    /**
     * The function to call when the dialog is closed.
     */
    onCloseAutoFocus: () => void;
}

interface DrawerWithTriggerProps extends DrawerBaseProps {
    /**
     * The trigger of the drawer.
     *
     * > NOTE: If you are passing a component as the trigger, it must correctly
     * > spread all the props passed to it to a DOM element and forward a ref.
     */
    trigger: ReactElement<DOMAttributes<FocusableElement>, string>;
    /**
     * The function to call when the dialog is closed.
     */
    onCloseAutoFocus?: (() => void) | undefined;
}

type DrawerProps = DrawerTriggerlessProps | DrawerWithTriggerProps;

const styles = stylex.create({
    content: {
        borderRadius: 0,
        borderStyle: 'none',
        outline: 'none',
        // padding: baseDimension.spacing_2x,

        bottom: 0,
        position: 'fixed',
        top: 0,

        display: 'flex',
        flexDirection: 'column',
        maxWidth: `calc(100vw - ${tokens['size-md']})`,

        animationDuration: '0.5s',
        animationTimingFunction: 'cubic-bezier(0.32, 0.72, 0, 1)',
        transition: 'transform 0.5s cubic-bezier(0.32, 0.72, 0, 1)',
        willChange: 'transform',
    },
    contentLeft: {
        borderRightColor: baltoTheme.reusableBorderDefault,
        borderRightStyle: 'solid',
        borderRightWidth: 1,
        left: 0,

        animationName: {
            ":is([data-state='open'])": slideFromLeft,
            ":is([data-state='closed'])": slideToLeft,
        },
    },
    contentRight: {
        borderLeftColor: baltoTheme.reusableBorderDefault,
        borderLeftStyle: 'solid',
        borderLeftWidth: 1,
        right: 0,

        animationName: {
            ":is([data-state='open'])": slideFromRight,
            ":is([data-state='closed'])": slideToRight,
        },
    },
    contentSmall: {
        width: 320,
    },
    contentMedium: {
        width: 640,
    },
    contentLarge: {
        width: 960,
    },
    trigger: {
        cursor: 'pointer',
    },
    footerSpacer: {
        flexGrow: 1,
    },
    header: {
        padding: `${tokens['space-vertical-2xl']} ${tokens['space-horizontal-2xl']} 0 ${tokens['space-horizontal-2xl']}`,
    },
    headerActions: {
        padding: `${tokens['space-vertical-2xl']} ${tokens['space-horizontal-2xl']} 0 ${tokens['space-horizontal-2xl']}`,
    },
    body: {
        flexGrow: 1,
        minHeight: 0,
        overflowY: 'auto',
        padding: `${tokens['space-vertical-lg']} ${tokens['space-horizontal-2xl']} ${tokens['space-vertical-2xl']}`,
    },
    footer: {
        borderTopColor: baltoTheme.reusableBorderDefault,
        borderTopStyle: 'solid',
        borderTopWidth: 1,
        padding: `${tokens['space-vertical-lg']} ${tokens['space-horizontal-2xl']}`,
    },
    hiddenTrigger: {
        height: 0,
        opacity: 0,
        pointerEvents: 'none',
        position: 'absolute',
        width: 0,
    },
});

const Root = forwardRef<HTMLButtonElement, DrawerProps>(
    (
        {
            trigger,
            open: openProp,
            defaultOpen,
            onOpenChange,
            side = 'right',
            variant = 'inconsequential',
            onCloseAutoFocus,
            ...props
        },
        forwardedRef,
    ) => {
        const [open, setOpen] = useControlledState(
            openProp,
            defaultOpen ?? false,
            onOpenChange,
        );

        const pressableRef = useRef<HTMLButtonElement>(null);
        const onCloseAutoFocusRef = useEffectEvent(() => onCloseAutoFocus?.());
        useEffect(() => {
            const RESTORE_FOCUS_EVENT = 'react-aria-focus-scope-restore';

            const handleRestoreFocus = (e: Event) => {
                e.preventDefault();
                onCloseAutoFocusRef();
            };

            document.body.addEventListener(
                RESTORE_FOCUS_EVENT,
                handleRestoreFocus,
            );

            return () => {
                document.body.removeEventListener(
                    RESTORE_FOCUS_EVENT,
                    handleRestoreFocus,
                );
            };
        }, [onCloseAutoFocusRef]);

        const combinedRef = useMergedRef(forwardedRef, pressableRef);

        return (
            <DrawerContext side={side} variant={variant}>
                <DialogTrigger isOpen={open} onOpenChange={setOpen}>
                    <Pressable
                        {...stylex.props(styles.trigger)}
                        ref={combinedRef}
                    >
                        {trigger || (
                            <button
                                {...stylex.props(styles.hiddenTrigger)}
                                aria-hidden
                                tabIndex={-1}
                            />
                        )}
                    </Pressable>
                    <DrawerContent {...props} />
                </DialogTrigger>
            </DrawerContext>
        );
    },
);

Root.displayName = 'Drawer.Root';

const DrawerContent = forwardRef<
    HTMLDivElement,
    Omit<
        DrawerProps,
        'trigger' | 'side' | 'variant' | 'open' | 'defaultOpen' | 'onOpenChange'
    >
>(
    (
        {
            size = 'medium',
            children,
            className,
            style,
            'aria-describedby': ariaDescribedBy,
            'aria-label': ariaLabel,
            'aria-labelledby': ariaLabelledBy,
            'data-testid': dataTestId,
        },
        ref,
    ) => {
        const { side, variant } = useDrawerContext('DrawerContent');
        const contentStyles = useMergedStyles(
            className,
            style,
            stylex.props(
                levelStyles.level3Surface,
                styles.content,
                size === 'small' && styles.contentSmall,
                size === 'medium' && styles.contentMedium,
                size === 'large' && styles.contentLarge,
                side === 'left' && styles.contentLeft,
                side === 'right' && styles.contentRight,
            ),
        );

        const modalRef = useRef<HTMLDivElement>(null);
        const localState = useOverlayTriggerState({});
        const state = useContext(OverlayTriggerStateContext) || localState;
        const isOverlayExiting = useExitAnimation(modalRef, state.isOpen);
        const { overlayProps, underlayProps } = useOverlay(
            {
                isDismissable: variant === 'critical' ? false : true,
                isKeyboardDismissDisabled: variant === 'critical',
                shouldCloseOnInteractOutside: (element) => {
                    // adds additional checks for valid events on radix and similar portals
                    // TODO - https://snowflakecomputing.atlassian.net/browse/APPS-57778 - migrate Tooltip to react-aria
                    // https://github.com/adobe/react-spectrum/blob/f821086f93125db3a8ea0ca5bb86cadbac3818ad/packages/%40react-aria/interactions/src/useInteractOutside.ts#L127
                    if (
                        element.closest('[data-radix-popper-content-wrapper]')
                    ) {
                        // It's a tooltip, so don't close the modal
                        return false;
                    }
                    return variant &&
                        ['critical', 'persistent'].includes(variant)
                        ? false
                        : true;
                },
                isOpen: state.isOpen,
                onClose: state.close,
            },
            modalRef,
        );

        useOverlayFocusContain();
        usePreventScroll({
            isDisabled: !state.isOpen && variant !== 'persistent',
        });

        useEffect(() => {
            if (state.isOpen && modalRef.current && variant !== 'persistent') {
                return ariaHideOutside([modalRef.current], {
                    shouldUseInert: true,
                });
            }
        }, [state.isOpen, modalRef, variant]);

        if (!state.isOpen && !isOverlayExiting) {
            return null;
        }

        return (
            <Overlay
                data-dialog-overlay
                shouldContainFocus={variant === 'persistent' ? false : true}
            >
                <BaltoThemeProvider>
                    <div {...underlayProps}>
                        <div {...overlayProps}>
                            <Flex
                                asChild
                                direction="column"
                                gap="0x"
                                {...contentStyles}
                                ref={ref}
                                data-state={state.isOpen ? 'open' : 'closed'}
                            >
                                <Dialog
                                    aria-describedby={ariaDescribedBy}
                                    aria-label={ariaLabel}
                                    aria-labelledby={ariaLabelledBy}
                                    data-testid={dataTestId}
                                    ref={modalRef}
                                    role={
                                        variant === 'critical'
                                            ? 'alertdialog'
                                            : 'dialog'
                                    }
                                >
                                    {children}
                                </Dialog>
                            </Flex>
                        </div>
                    </div>
                </BaltoThemeProvider>
            </Overlay>
        );
    },
);

DrawerContent.displayName = 'Drawer.Content';

const Header = forwardRef<HTMLDivElement, Omit<FlexProps<'div'>, 'asChild'>>(
    function DrawerHeader({ children, className, style, ...props }, ref) {
        const { side } = useDrawerContext('Header');
        const mergedStyles = useMergedStyles(
            className,
            style,
            stylex.props(styles.header),
        );

        return (
            <Flex
                ref={ref}
                align="center"
                justify="between"
                gap="2x"
                {...props}
                {...mergedStyles}
            >
                <Slottable>{children}</Slottable>
                <IconButton
                    variant="tertiary"
                    icon={side === 'left' ? SlideLeftIcon : SlideRightIcon}
                    aria-label="Close"
                    asChild
                >
                    <Button slot="close" />
                </IconButton>
            </Flex>
        );
    },
);

Header.displayName = 'Drawer.Header';

const Title = forwardRef<HTMLHeadingElement, SlottedContainerProps<'h3'>>(
    function DrawerTitle({ children, ...props }, ref) {
        return (
            <Heading ref={ref} {...props} size="pageHeader" asChild>
                <HeadingPrimitive>{children}</HeadingPrimitive>
            </Heading>
        );
    },
);

Title.displayName = 'Drawer.Title';

const HeaderActions = forwardRef<HTMLDivElement, FlexProps<'div'>>(
    function DrawerHeaderActions(
        { children, className, style, ...props },
        ref,
    ) {
        const mergedStyles = useMergedStyles(
            className,
            style,
            stylex.props(styles.headerActions),
        );

        return (
            <Flex ref={ref} align="center" {...props} {...mergedStyles}>
                <Slottable>{children}</Slottable>
            </Flex>
        );
    },
);

HeaderActions.displayName = 'Drawer.HeaderActions';

const Body = forwardRef<HTMLDivElement, FlexProps<'div'>>(function DrawerBody(
    { children, className, style, ...props },
    ref,
) {
    const mergedStyles = useMergedStyles(
        className,
        style,
        stylex.props(styles.body),
    );

    return (
        <Flex
            ref={ref}
            direction="column"
            gap="2x"
            tabIndex={0}
            {...props}
            {...mergedStyles}
        >
            <Slottable>{children}</Slottable>
        </Flex>
    );
});

Body.displayName = 'Drawer.Body';

const Footer = forwardRef<HTMLDivElement, FlexProps<'div'>>(
    function DrawerFooter({ children, className, style, ...props }, ref) {
        const mergedStyles = useMergedStyles(
            className,
            style,
            stylex.props(styles.footer),
        );

        return (
            <Flex
                ref={ref}
                align="center"
                gap="2x"
                {...props}
                {...mergedStyles}
            >
                <Slottable>{children}</Slottable>
            </Flex>
        );
    },
);

Footer.displayName = 'Drawer.Footer';

const FooterLeft = forwardRef<HTMLDivElement, FlexProps<'div'>>(
    function DrawerFooterLeft({ children, ...props }, ref) {
        return (
            <Flex ref={ref} align="center" {...props}>
                <Slottable>{children}</Slottable>
            </Flex>
        );
    },
);

FooterLeft.displayName = 'Drawer.FooterLeft';

const FooterRight = forwardRef<HTMLDivElement, FlexProps<'div'>>(
    function DrawerFooterRight({ children, ...props }, ref) {
        return (
            <>
                <div {...stylex.props(styles.footerSpacer)} />
                <Flex ref={ref} align="center" {...props}>
                    <Slottable>{children}</Slottable>
                </Flex>
            </>
        );
    },
);

FooterRight.displayName = 'Drawer.FooterRight';

export type { DrawerProps };
export {
    Root,
    Body,
    Header,
    HeaderActions,
    Title,
    Footer,
    FooterLeft,
    FooterRight,
};
