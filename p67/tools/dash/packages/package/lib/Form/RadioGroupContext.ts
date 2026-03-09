import { createContext, useContext } from 'react';

interface RadioGroupContextValue {
    disabled?: boolean;
}

const defaultValue = {} as const;
const RadioGroupContext = createContext<RadioGroupContextValue>(defaultValue);

RadioGroupContext.displayName = 'RadioGroupContext';
export { RadioGroupContext };
export type { RadioGroupContextValue };

export function useRadioGroupContext() {
    const value = useContext(RadioGroupContext);
    return value;
}
