import { Handle, type NodeProps, Position } from '@xyflow/react';
import type { WorkflowFlowNode } from '../types';
import { baseNodeStyle, ExecutionBadge, getExecutionStyle } from './shared';

export function HumanNode({ data }: NodeProps<WorkflowFlowNode>) {
    return (
        <div
            style={{
                ...baseNodeStyle,
                border: '1.5px solid #bf8700',
                background: 'rgba(191,135,0,0.05)',
                color: '#9a6700',
                borderRadius: 12,
                ...getExecutionStyle(data.executionState),
            }}
        >
            <ExecutionBadge state={data.executionState} />
            <Handle
                type="target"
                position={Position.Top}
                style={{ background: '#bf8700' }}
            />
            <div
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    justifyContent: 'center',
                }}
            >
                <svg
                    aria-hidden="true"
                    width="12"
                    height="12"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                >
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                </svg>
                {data.label}
            </div>
            {data.humanTask && (
                <div style={{ fontSize: 10, color: '#6b7280', marginTop: 2 }}>
                    {data.humanTask}
                </div>
            )}
            <Handle
                type="source"
                position={Position.Bottom}
                style={{ background: '#bf8700' }}
            />
        </div>
    );
}
