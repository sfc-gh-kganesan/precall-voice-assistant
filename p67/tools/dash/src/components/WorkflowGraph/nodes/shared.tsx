import type { CSSProperties } from 'react';
import type { ExecutionState } from '../types';

const EXECUTION_COLORS: Record<
    ExecutionState,
    { border: string; bg?: string; shadow?: string }
> = {
    idle: { border: 'transparent' },
    running: { border: '#3b82f6', shadow: '0 0 8px rgba(59,130,246,0.5)' },
    completed: { border: '#22c55e', bg: 'rgba(34,197,94,0.08)' },
    failed: { border: '#ef4444', bg: 'rgba(239,68,68,0.08)' },
    waiting: { border: '#f59e0b', shadow: '0 0 8px rgba(245,158,11,0.5)' },
};

export function getExecutionStyle(state: ExecutionState): CSSProperties {
    const c = EXECUTION_COLORS[state];
    return {
        boxShadow: c.shadow,
        backgroundColor: c.bg,
        borderColor: c.border !== 'transparent' ? c.border : undefined,
    };
}

export function ExecutionBadge({ state }: { state: ExecutionState }) {
    if (state === 'idle') return null;
    const icons: Record<string, string> = {
        completed: '\u2713',
        failed: '\u2717',
        running: '\u25CF',
        waiting: '\u25CF',
    };
    const colors: Record<string, string> = {
        completed: '#22c55e',
        failed: '#ef4444',
        running: '#3b82f6',
        waiting: '#f59e0b',
    };
    return (
        <div
            style={{
                position: 'absolute',
                top: -6,
                right: -6,
                width: 18,
                height: 18,
                borderRadius: '50%',
                backgroundColor: colors[state],
                color: '#fff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 11,
                fontWeight: 700,
                lineHeight: 1,
                border: '2px solid #fff',
            }}
        >
            {icons[state]}
        </div>
    );
}

export const baseNodeStyle: CSSProperties = {
    padding: '10px 16px',
    borderRadius: 8,
    border: '1.5px solid #d0d7de',
    background: '#fff',
    fontSize: 12,
    fontWeight: 500,
    textAlign: 'center',
    position: 'relative',
    minWidth: 140,
    transition:
        'box-shadow 200ms ease, background-color 200ms ease, border-color 200ms ease',
};
