import { createContext } from 'react';

const HighlightContext = createContext({
    addHighlight: (_labelId: string, _ranges: [number, number][]) => {},
    removeHighlight: (_labelId: string) => {},
    searchValue: '',
});

export { HighlightContext };
