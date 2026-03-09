import { createContext } from '@radix-ui/react-context';

export const [ControlBarContext, useControlBarContext] = createContext<{
    /**
     * The side of the control bar that the context is for.
     */
    side: 'left' | 'right';
}>('ControlBarContext');
