import { createContext, useContext } from 'react';

import { devError } from '../../util/dev-warning';
import type { StatusVariant } from '../types';

interface StatusContextValue {
    variant: StatusVariant | undefined;
}
const StatusContext = createContext<StatusContextValue | null>(null);

const useCreateStatusContext = (variant: StatusVariant): StatusContextValue => {
    const parentStatus = useContext(StatusContext);
    if (
        parentStatus &&
        parentStatus.variant !== 'neutral' &&
        variant !== 'neutral'
    ) {
        devError('Non Neutral status cannot be nested within each other');
    }
    return {
        variant,
    };
};

export { StatusContext, useCreateStatusContext };
export type { StatusContextValue };
