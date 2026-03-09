import { createContext } from 'react';

const PopoverContext = createContext<boolean | null>(null);
const PopoverTriggerContext = createContext<boolean | null>(null);

export { PopoverContext, PopoverTriggerContext };
