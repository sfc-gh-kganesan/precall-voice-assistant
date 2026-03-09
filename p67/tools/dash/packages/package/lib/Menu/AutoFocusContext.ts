import { createContext } from '@radix-ui/react-context';

export const [AutoFocusContext, useAutoFocusContext] = createContext<{
    shouldAutoFocusOnClose: boolean;
    setShouldAutoFocusOnClose: (shouldAutoFocusOnClose: boolean) => void;
}>('MenuClose');
