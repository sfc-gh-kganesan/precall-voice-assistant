import { Handle, type NodeProps, Position } from '@xyflow/react';
import type { WorkflowFlowNode } from '../types';
import { ExecutionBadge, getExecutionStyle } from './shared';

export function DecisionNode({ data }: NodeProps<WorkflowFlowNode>) {
    const size = 80;
    return (
        <div
            style={{
                position: 'relative',
                width: size,
                height: size,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
            }}
        >
            <div
                style={{
                    position: 'absolute',
                    width: size * 0.7,
                    height: size * 0.7,
                    transform: 'rotate(45deg)',
                    border: '1.5px solid #8250df',
                    background: 'rgba(130,80,223,0.04)',
                    borderRadius: 4,
                    transition:
                        'box-shadow 200ms ease, background-color 200ms ease, border-color 200ms ease',
                    ...getExecutionStyle(data.executionState),
                }}
            />
            <ExecutionBadge state={data.executionState} />
            <Handle
                type="target"
                position={Position.Top}
                style={{ background: '#8250df', top: -4 }}
            />
            <div
                style={{
                    position: 'relative',
                    zIndex: 1,
                    fontSize: 11,
                    fontWeight: 500,
                    color: '#6e40c9',
                    textAlign: 'center',
                    padding: '0 4px',
                    lineHeight: 1.2,
                    maxWidth: size - 10,
                }}
            >
                {data.label}
            </div>
            <Handle
                type="source"
                position={Position.Bottom}
                style={{ background: '#8250df', bottom: -4 }}
            />
            <Handle
                type="source"
                position={Position.Right}
                id="right"
                style={{ background: '#8250df', right: -4 }}
            />
            <Handle
                type="source"
                position={Position.Left}
                id="left"
                style={{ background: '#8250df', left: -4 }}
            />
        </div>
    );
}
