import { Handle, type NodeProps, Position } from '@xyflow/react';
import type { WorkflowFlowNode } from '../types';
import { baseNodeStyle, ExecutionBadge, getExecutionStyle } from './shared';

export function QueryNode({ data }: NodeProps<WorkflowFlowNode>) {
    return (
        <div
            style={{
                ...baseNodeStyle,
                border: '1.5px solid #0550ae',
                background: 'rgba(5,80,174,0.04)',
                color: '#0550ae',
                ...getExecutionStyle(data.executionState),
            }}
        >
            <ExecutionBadge state={data.executionState} />
            <Handle
                type="target"
                position={Position.Top}
                style={{ background: '#0550ae' }}
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
                    <ellipse cx="12" cy="5" rx="9" ry="3" />
                    <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
                    <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
                </svg>
                {data.label}
            </div>
            {data.question && (
                <div
                    style={{
                        fontSize: 10,
                        color: '#6b7280',
                        marginTop: 2,
                        maxWidth: 160,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                    }}
                >
                    {data.question}
                </div>
            )}
            <Handle
                type="source"
                position={Position.Bottom}
                style={{ background: '#0550ae' }}
            />
        </div>
    );
}
