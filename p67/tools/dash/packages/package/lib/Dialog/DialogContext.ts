import { createContext } from '@radix-ui/react-context';

const [DialogContext, useDialogContext] = createContext<{
    isInDialog: boolean;
    isFullscreenDialog: boolean;
    ariaDescribedBy?: string | undefined;
}>('Dialog', {
    isInDialog: false,
    isFullscreenDialog: false,
});

export { DialogContext, useDialogContext };
