import { createContext, useContext } from 'react';

import type { TextVariant } from '../types';

interface ParagraphContextValue {
    bold: boolean;
    small: boolean;
    variant: TextVariant;
    caps: boolean;
}
const ParagraphContext = createContext<ParagraphContextValue | null>(null);
ParagraphContext.displayName = 'ParagraphContext';

function useParagraphContext() {
    const value = useContext(ParagraphContext);
    if (!value) {
        console.error(
            'No value found for Text context, Please make sure Context is initialized correctly.',
        );
    }
    return useContext(ParagraphContext);
}
export { ParagraphContext, useParagraphContext };
export type { ParagraphContextValue };
