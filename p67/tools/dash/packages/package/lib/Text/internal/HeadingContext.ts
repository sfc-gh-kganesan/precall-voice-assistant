import { createContext, useContext, useMemo } from 'react';

type HeadingLevel = 1 | 2 | 3 | 4 | 5 | 6;
interface HeadingContextValue {
    level: HeadingLevel;
}
const HeadingContext = createContext<HeadingContextValue | null>(null);
HeadingContext.displayName = 'HeadingContext';

function useCreateHeadingContext(): HeadingContextValue {
    const value = useContext(HeadingContext);
    return {
        level: useMemo(
            (): HeadingLevel =>
                value === null
                    ? 1
                    : value.level >= 1 && value.level < 6
                      ? ((value.level + 1) as HeadingLevel)
                      : 6,
            [value],
        ),
    };
}

export { HeadingContext, useCreateHeadingContext };
export type { HeadingContextValue, HeadingLevel };
