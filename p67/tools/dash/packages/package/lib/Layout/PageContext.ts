import * as React from 'react';

type PageVariant = 'regular' | 'centered' | 'full';
interface PageContextValue {
    variant?: PageVariant;
}

const PageContext = React.createContext<PageContextValue>({
    variant: 'regular',
});

export { PageContext };
export type { PageContextValue, PageVariant };
