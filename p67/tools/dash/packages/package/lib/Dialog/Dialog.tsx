import { useEffectEvent } from '@react-aria/utils';
import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import {
    type DOMAttributes,
    type ReactElement,
    type ReactNode,
    useEffect,
    useRef,
} from 'react';
import { Pressable, usePress } from 'react-aria';
import {
    Dialog as DialogPrimitive,
    DialogTrigger,
    Modal,
    ModalOverlay,
} from 'react-aria-components';
import { BaltoThemeProvider } from '../BaltoProvider';
import { levelStyles } from '../internal/utils/levelStyles';
import { Flex } from '../Layout';
import type { FocusableElement } from '../types';
import type { ControlledOpenComponent } from '../util/Controlled';
import { devWarning } from '../util/dev-warning';
import { DialogBody } from './DialogBody';
import { DialogContext, useDialogContext } from './DialogContext';
import { DialogFooter } from './DialogFooter';
import { DialogHeader } from './DialogHeader';
import type { DialogSize } from './types';

interface DialogBaseProps extends ControlledOpenComponent {
    /**
     * The variant of the dialog.
     * @default "inconsequential"
     */
    variant?: 'critical' | 'inconsequential' | undefined;
    /**
     * The size of the dialog.
     * @default "small"
     */
    size?: DialogSize | undefined;
    /**
     * The children of the dialog.
     */
    children: ReactNode;
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

interface DialogTriggerlessProps extends DialogBaseProps {
    /**
     * The trigger of the dialog.
     */
    trigger?: undefined;
    /**
     * The function to call when the dialog is closed.
     */
    onCloseAutoFocus: () => void;
}

interface DialogWithTriggerProps extends DialogBaseProps {
    /**
     * The trigger of the dialog.
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

type DialogProps = DialogTriggerlessProps | DialogWithTriggerProps;

const styles = stylex.create({
    overlay: {
        backgroundColor: baltoTheme.componentDialogOverlay,
        inset: 0,
        position: 'fixed',
    },
    dialog: {
        left: '50%',
        maxHeight: '90%', // constrain max height within viewport
        minWidth: 320,
        outline: {
            default: 'none',
            ':focus-visible': 'none',
        },
        padding: 0,
        pointerEvents: 'auto',
        position: 'fixed',
        top: '50%',
        transform: 'translate(-50%, -50%)',
        width: `calc(100% - ${tokens['size-md']})`, // take up full applicable width (with some breathing room) until constraind by maxWidth based on size.
    },
    dialogSmall: {
        maxWidth: 480, // TODO: confirm sizes with UX.
    },
    dialogMedium: {
        maxWidth: 600,
    },
    dialogLarge: {
        maxWidth: 720,
    },
    dialogXLarge: {
        maxWidth: 960,
    },
    dialogFullscreen: {
        height: `calc(100vh - ${tokens['size-md']})`,
        maxHeight: `calc(100vh - ${tokens['size-md']})`,
        width: `calc(100vw - ${tokens['size-md']})`,
    },
    trigger: {
        cursor: 'pointer',
    },
});

/**
 * This renders a dummy pressable for react-aria.
 * This is solely to silence a warning that makes a test fail in snapps.
 */
function PressablePlaceholder() {
    usePress({});
    return null;
}

/**
 * The root component for the Dialog component.
 */
const DialogComponent = (props: DialogProps) => {
    const { isInDialog } = useDialogContext('DialogRoot');

    if (isInDialog) {
        devWarning('Dialog should not be nested.');
    }

    const {
        trigger,
        size = 'small',
        children,
        'aria-describedby': ariaDescribedBy,
        'aria-label': ariaLabel,
        'aria-labelledby': ariaLabelledBy,
        'data-testid': dataTestId,
        variant,
        defaultOpen,
        open,
        onOpenChange,
        onCloseAutoFocus,
    } = props;

    const pressableRef = useRef<HTMLButtonElement>(null);
    const onCloseAutoFocusRef = useEffectEvent(() => onCloseAutoFocus?.());
    useEffect(() => {
        const el = pressableRef.current;

        if (!el) return;

        const RESTORE_FOCUS_EVENT = 'react-aria-focus-scope-restore';

        const handleRestoreFocus = (e: Event) => {
            e.preventDefault();
            onCloseAutoFocusRef();
        };

        el.addEventListener(RESTORE_FOCUS_EVENT, handleRestoreFocus);

        return () => {
            el.removeEventListener(RESTORE_FOCUS_EVENT, handleRestoreFocus);
        };
    }, [onCloseAutoFocusRef]);

    return (
        <DialogContext
            isInDialog={true}
            ariaDescribedBy={ariaDescribedBy}
            isFullscreenDialog={size === 'fullscreen'}
        >
            <DialogTrigger
                defaultOpen={defaultOpen}
                isOpen={open}
                onOpenChange={onOpenChange}
            >
                {trigger ? (
                    <Pressable
                        ref={pressableRef}
                        {...stylex.props(styles.trigger)}
                    >
                        {trigger}
                    </Pressable>
                ) : (
                    <PressablePlaceholder />
                )}
                <ModalOverlay
                    {...stylex.props(styles.overlay)}
                    data-dialog-overlay
                    isDismissable={variant === 'critical' ? false : true}
                    shouldCloseOnInteractOutside={(element) => {
                        // adds additional checks for valid events on radix and similar portals
                        // TODO - https://snowflakecomputing.atlassian.net/browse/APPS-57778 - migrate Tooltip to react-aria
                        // https://github.com/adobe/react-spectrum/blob/f821086f93125db3a8ea0ca5bb86cadbac3818ad/packages/%40react-aria/interactions/src/useInteractOutside.ts#L127
                        if (
                            element.closest(
                                '[data-radix-popper-content-wrapper]',
                            )
                        ) {
                            // It's a tooltip, so don't close the modal
                            return false;
                        }
                        return variant === 'critical' ? false : true;
                    }}
                    isKeyboardDismissDisabled={variant === 'critical'}
                >
                    <Modal>
                        <BaltoThemeProvider>
                            <Flex
                                asChild
                                direction="column"
                                gap="0x"
                                {...stylex.props(
                                    levelStyles.level3Surface,
                                    styles.dialog,
                                    size === 'small' && styles.dialogSmall,
                                    size === 'medium' && styles.dialogMedium,
                                    size === 'large' && styles.dialogLarge,
                                    size === 'xlarge' && styles.dialogXLarge,
                                    size === 'fullscreen' &&
                                        styles.dialogFullscreen,
                                )}
                            >
                                <DialogPrimitive
                                    aria-describedby={ariaDescribedBy}
                                    aria-label={ariaLabel}
                                    aria-labelledby={ariaLabelledBy}
                                    data-testid={dataTestId}
                                    role={
                                        variant === 'critical'
                                            ? 'alertdialog'
                                            : 'dialog'
                                    }
                                >
                                    {children}
                                </DialogPrimitive>
                            </Flex>
                        </BaltoThemeProvider>
                    </Modal>
                </ModalOverlay>
            </DialogTrigger>
        </DialogContext>
    );
};

DialogComponent.displayName = 'Dialog.Root';

export type { DialogBodyProps } from './DialogBody';
export type { DialogFooterProps } from './DialogFooter';
export type { DialogHeaderProps } from './DialogHeader';
export type { DialogProps };

export {
    DialogComponent as Root,
    DialogBody as Body,
    DialogHeader as Header,
    DialogFooter as Footer,
};
