import { useState } from 'react';

export function useSort<T>(
    defaultKey: keyof T,
    defaultDir: 'asc' | 'desc' = 'asc',
) {
    const [sortKey, setSortKey] = useState<keyof T>(defaultKey);
    const [sortDir, setSortDir] = useState<'asc' | 'desc'>(defaultDir);

    const onSort = (key: keyof T) => {
        if (key === sortKey) {
            setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
        } else {
            setSortKey(key);
            setSortDir('asc');
        }
    };

    const sortData = (data: T[]): T[] => {
        return [...data].sort((a, b) => {
            const aVal = a[sortKey];
            const bVal = b[sortKey];
            if (aVal == null && bVal == null) return 0;
            if (aVal == null) return 1;
            if (bVal == null) return -1;
            const cmp =
                typeof aVal === 'string'
                    ? aVal.localeCompare(bVal as string)
                    : (aVal as number) - (bVal as number);
            return sortDir === 'asc' ? cmp : -cmp;
        });
    };

    return { sortKey, sortDir, onSort, sortData };
}
