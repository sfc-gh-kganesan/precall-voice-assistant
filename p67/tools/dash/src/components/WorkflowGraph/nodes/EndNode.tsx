import { Handle, type NodeProps, Position } from '@xyflow/react';
import type { WorkflowFlowNode } from '../types';
import { baseNodeStyle, ExecutionBadge, getExecutionStyle } from './shared';

export function EndNode({ data }: NodeProps<WorkflowFlowNode>) {
    const isSuccess =
        data.endType !== 'failure' && data.endType !== 'cancelled';
    const color = isSuccess ? '#2ea44f' : '#cf222e';
    return (
        <div
            style={{
                ...baseNodeStyle,
                borderRadius: 24,
                border: `1.5px solid ${color}`,
                background: isSuccess
                    ? 'rgba(46,164,79,0.06)'
                    : 'rgba(207,34,46,0.06)',
                color,
                ...getExecutionStyle(data.executionState),
            }}
        >
            <ExecutionBadge state={data.executionState} />
            <Handle
                type="target"
                position={Position.Top}
                style={{ background: color }}
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
                    strokeWidth="2.5"
                >
                    <rect x="6" y="6" width="12" height="12" rx="2" />
                </svg>
                {data.label}
            </div>
        </div>
    );
}
