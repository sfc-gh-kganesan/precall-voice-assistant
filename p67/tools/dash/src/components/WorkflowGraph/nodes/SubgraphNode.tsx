import { Handle, type NodeProps, Position } from '@xyflow/react';
import type { WorkflowFlowNode } from '../types';
import { baseNodeStyle, ExecutionBadge, getExecutionStyle } from './shared';

export function SubgraphNode({ data }: NodeProps<WorkflowFlowNode>) {
    return (
        <div
            style={{
                ...baseNodeStyle,
                border: '1.5px dashed #57606a',
                background: 'rgba(87,96,106,0.04)',
                color: '#424a53',
                ...getExecutionStyle(data.executionState),
            }}
        >
            <ExecutionBadge state={data.executionState} />
            <Handle
                type="target"
                position={Position.Top}
                style={{ background: '#57606a' }}
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
                    <polygon points="12 2 2 7 12 12 22 7 12 2" />
                    <polyline points="2 17 12 22 22 17" />
                    <polyline points="2 12 12 17 22 12" />
                </svg>
                {data.label}
            </div>
            {data.subgraphName && (
                <div style={{ fontSize: 10, color: '#6b7280', marginTop: 2 }}>
                    {data.subgraphName}
                </div>
            )}
            <Handle
                type="source"
                position={Position.Bottom}
                style={{ background: '#57606a' }}
            />
        </div>
    );
}
