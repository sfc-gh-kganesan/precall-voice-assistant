import { Handle, type NodeProps, Position } from '@xyflow/react';
import type { WorkflowFlowNode } from '../types';
import { baseNodeStyle, ExecutionBadge, getExecutionStyle } from './shared';

export function ActionNode({ data }: NodeProps<WorkflowFlowNode>) {
    return (
        <div
            style={{
                ...baseNodeStyle,
                border: '1.5px solid #0969da',
                background: 'rgba(9,105,218,0.04)',
                color: '#0550ae',
                ...getExecutionStyle(data.executionState),
            }}
        >
            <ExecutionBadge state={data.executionState} />
            <Handle
                type="target"
                position={Position.Top}
                style={{ background: '#0969da' }}
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
                    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                </svg>
                {data.label}
            </div>
            {data.actionName && (
                <div style={{ fontSize: 10, color: '#6b7280', marginTop: 2 }}>
                    {data.actionName}
                </div>
            )}
            <Handle
                type="source"
                position={Position.Bottom}
                style={{ background: '#0969da' }}
            />
        </div>
    );
}
