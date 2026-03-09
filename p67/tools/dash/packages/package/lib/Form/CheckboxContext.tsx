import { createContext } from '@radix-ui/react-context';

export const [CheckboxContext, useCheckboxContext] = createContext<{
    /**
     * The slot of the checkbox.
     */
    slot?: string | undefined;
}>('CheckboxContext', {
    slot: undefined,
});
