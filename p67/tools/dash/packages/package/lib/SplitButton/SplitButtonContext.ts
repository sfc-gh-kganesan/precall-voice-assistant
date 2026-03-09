import { createContext } from 'react';

import type { ButtonSize, ButtonVariant } from '../Button';

interface SplitButtonContextValue {
    variant?: Extract<ButtonVariant, 'primary' | 'secondary'>;
    size?: ButtonSize;
    disabled?: boolean;
}

const defaultValue = { variant: 'primary', size: 'regular' } as const;
const SplitButtonContext = createContext<SplitButtonContextValue>(defaultValue);

SplitButtonContext.displayName = 'SplitButtonContext';
export { SplitButtonContext };
export type { SplitButtonContextValue };
