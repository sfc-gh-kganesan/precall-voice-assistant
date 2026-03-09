import * as React from 'react';
import { useCallback, useMemo, useState } from 'react';

interface LayoutContextValue {
    scrollableParent?: boolean;
    hasSidebar: boolean;
    addSidebar: (id: string) => void;
    removeSidebar: (id: string) => void;
}

const LayoutContext = React.createContext<LayoutContextValue>({
    hasSidebar: false,
    addSidebar: () => null,
    removeSidebar: () => null,
});
const useLayoutContextValue = (
    hasScrollableParent: boolean,
): LayoutContextValue => {
    const [sidebars, setSidebars] = useState<string[]>([]);
    const addSidebar = useCallback((id: string) => {
        setSidebars((prev) => [...prev, id]);
    }, []);
    const removeSidebar = useCallback((id: string) => {
        setSidebars((prev) => prev.filter((currentId) => currentId !== id));
    }, []);
    const hasSidebar = useMemo(() => sidebars.length > 0, [sidebars.length]);
    return {
        hasSidebar,
        scrollableParent: hasScrollableParent,
        addSidebar,
        removeSidebar,
    };
};

export { useLayoutContextValue, LayoutContext };
export type { LayoutContextValue };
