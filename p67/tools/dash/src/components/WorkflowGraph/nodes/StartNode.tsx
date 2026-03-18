import { Handle, type NodeProps, Position } from '@xyflow/react';
import type { WorkflowFlowNode } from '../types';
import { baseNodeStyle, ExecutionBadge, getExecutionStyle } from './shared';

export function StartNode({ data }: NodeProps<WorkflowFlowNode>) {
    return (
        <div
            style={{
                ...baseNodeStyle,
                borderRadius: 24,
                border: '1.5px solid #2ea44f',
                background: 'rgba(46,164,79,0.06)',
                color: '#1a7f37',
                ...getExecutionStyle(data.executionState),
            }}
        >
            <ExecutionBadge state={data.executionState} />
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
                    fill="currentColor"
                >
                    <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
                {data.label}
            </div>
            <Handle
                type="source"
                position={Position.Bottom}
                style={{ background: '#2ea44f' }}
            />
        </div>
    );
}
