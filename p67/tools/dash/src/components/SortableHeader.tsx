interface SortableHeaderProps {
    label: string;
    sortKey: string;
    currentSort: string;
    currentDir: 'asc' | 'desc';
    onSort: (key: string) => void;
}

export function SortableHeader({
    label,
    sortKey,
    currentSort,
    currentDir,
    onSort,
}: SortableHeaderProps) {
    const isActive = currentSort === sortKey;
    const arrow = isActive ? (currentDir === 'asc' ? ' ▲' : ' ▼') : '';
    return (
        <th
            onClick={() => onSort(sortKey)}
            style={{
                cursor: 'pointer',
                userSelect: 'none',
                whiteSpace: 'nowrap',
            }}
        >
            {label}
            {arrow && (
                <span
                    style={{
                        fontSize: '10px',
                        marginLeft: '2px',
                        opacity: 0.7,
                    }}
                >
                    {currentDir === 'asc' ? '▲' : '▼'}
                </span>
            )}
        </th>
    );
}
