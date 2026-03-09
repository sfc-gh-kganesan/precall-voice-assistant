import { useContext, useEffect } from 'react';

import { HighlightContext } from './context';

function findRangesToHighlight({
    label,
    searchValue,
}: {
    label: string;
    searchValue: string;
}) {
    const ranges: [number, number][] = [];
    let startIndex = 0;

    while (true) {
        const index = label
            .toLowerCase()
            .indexOf(searchValue.toLowerCase(), startIndex);

        if (index === -1) {
            break;
        }

        ranges.push([index, index + searchValue.length]);
        startIndex = index + 1;
    }

    return ranges;
}

function useHighlightMatch({
    labelId,
    label,
    onMatch,
}: {
    labelId: string;
    label: string;
    onMatch?: () => void;
}) {
    const { addHighlight, removeHighlight, searchValue } =
        useContext(HighlightContext);

    useEffect(() => {
        if (typeof CSS.highlights === 'undefined') {
            return;
        }

        if (!searchValue) {
            return;
        }

        const ranges: [number, number][] = findRangesToHighlight({
            label,
            searchValue,
        });

        if (!ranges?.[0]) {
            removeHighlight(labelId);
            return;
        } else {
            onMatch?.();
            addHighlight(labelId, ranges);
        }

        return () => {
            removeHighlight(labelId);
        };
    }, [addHighlight, removeHighlight, searchValue, labelId, label, onMatch]);
}

export { useHighlightMatch };
