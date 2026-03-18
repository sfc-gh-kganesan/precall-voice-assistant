import {
    Background,
    BackgroundVariant,
    Controls,
    MiniMap,
    type NodeTypes,
    ReactFlow,
    useEdgesState,
    useNodesState,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useCallback, useEffect, useMemo } from 'react';
import { convertGraphToReactFlow } from './converter';
import { ActionNode } from './nodes/ActionNode';
import { DecisionNode } from './nodes/DecisionNode';
import { EndNode } from './nodes/EndNode';
import { HumanNode } from './nodes/HumanNode';
import { QueryNode } from './nodes/QueryNode';
import { StartNode } from './nodes/StartNode';
import { SubgraphNode } from './nodes/SubgraphNode';
import type {
    ExecutionState,
    WorkflowFlowNode,
    WorkflowGraphDef,
} from './types';

const nodeTypes = {
    start_node: StartNode,
    end_node: EndNode,
    action_node: ActionNode,
    decision_node: DecisionNode,
    human_node: HumanNode,
    subgraph_node: SubgraphNode,
    query_node: QueryNode,
} as NodeTypes;

interface WorkflowGraphProps {
    graph: WorkflowGraphDef;
    executionStates?: Record<string, ExecutionState>;
    height?: string | number;
}

export function WorkflowGraph({
    graph,
    executionStates,
    height = 500,
}: WorkflowGraphProps) {
    const { nodes: initialNodes, edges: initialEdges } = useMemo(
        () => convertGraphToReactFlow(graph),
        [graph],
    );

    const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

    useEffect(() => {
        setNodes(initialNodes);
        setEdges(initialEdges);
    }, [initialNodes, initialEdges, setNodes, setEdges]);

    useEffect(() => {
        if (!executionStates) return;
        setNodes((nds) =>
            nds.map((node) => {
                const state = executionStates[node.id] ?? 'idle';
                if ((node as WorkflowFlowNode).data.executionState === state)
                    return node;
                return {
                    ...node,
                    data: {
                        ...(node as WorkflowFlowNode).data,
                        executionState: state,
                    },
                };
            }),
        );
        setEdges((eds) =>
            eds.map((edge) => {
                const sourceState = executionStates[edge.source];
                const animated =
                    sourceState === 'running' || sourceState === 'completed';
                if (edge.animated === animated) return edge;
                return {
                    ...edge,
                    animated,
                    style: {
                        ...edge.style,
                        stroke:
                            sourceState === 'completed'
                                ? '#22c55e'
                                : sourceState === 'running'
                                  ? '#3b82f6'
                                  : '#6b7280',
                    },
                };
            }),
        );
    }, [executionStates, setNodes, setEdges]);

    const onInit = useCallback((instance: { fitView: () => void }) => {
        setTimeout(() => instance.fitView(), 50);
    }, []);

    return (
        <div
            style={{
                width: '100%',
                height,
                border: '1px solid var(--sf-gray-200)',
                borderRadius: 8,
                overflow: 'hidden',
            }}
        >
            <ReactFlow
                nodes={nodes}
                edges={edges}
                nodeTypes={nodeTypes}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onInit={onInit}
                fitView
                nodesDraggable={false}
                nodesConnectable={false}
                elementsSelectable={false}
                proOptions={{ hideAttribution: true }}
            >
                <Background
                    variant={BackgroundVariant.Dots}
                    gap={16}
                    size={0.8}
                    color="#e5e7eb"
                />
                <Controls showInteractive={false} />
                <MiniMap
                    nodeStrokeWidth={2}
                    style={{ border: '1px solid #e5e7eb', borderRadius: 4 }}
                    maskColor="rgba(0,0,0,0.05)"
                />
            </ReactFlow>
        </div>
    );
}
