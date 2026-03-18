import dagre from 'dagre';
import type {
    WorkflowFlowEdge,
    WorkflowFlowNode,
    WorkflowGraphDef,
} from './types';

const NODE_WIDTH = 180;
const NODE_HEIGHT = 60;

export function convertGraphToReactFlow(graph: WorkflowGraphDef): {
    nodes: WorkflowFlowNode[];
    edges: WorkflowFlowEdge[];
} {
    const g = new dagre.graphlib.Graph();
    g.setDefaultEdgeLabel(() => ({}));
    g.setGraph({ rankdir: 'TB', nodesep: 50, ranksep: 70 });

    for (const node of graph.nodes) {
        g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
    }
    for (const edge of graph.edges) {
        g.setEdge(edge.from_node, edge.to_node);
    }

    dagre.layout(g);

    const nodes: WorkflowFlowNode[] = graph.nodes.map((node) => {
        const pos = g.node(node.id);
        return {
            id: node.id,
            type: node.type,
            position: {
                x: pos.x - NODE_WIDTH / 2,
                y: pos.y - NODE_HEIGHT / 2,
            },
            data: {
                label: node.name,
                nodeType: node.type,
                description: node.description,
                executionState: 'idle' as const,
                endType: node.end_type,
                humanTask: node.human_task,
                actionName: node.action_name,
                question: node.question,
                subgraphName: node.subgraph_name,
            },
        };
    });

    const edges: WorkflowFlowEdge[] = graph.edges.map((edge) => ({
        id: edge.id,
        source: edge.from_node,
        target: edge.to_node,
        label: edge.label,
        animated: false,
        style: { stroke: '#6b7280', strokeWidth: 1.5 },
        labelStyle: { fontSize: 11, fill: '#6b7280' },
    }));

    return { nodes, edges };
}
