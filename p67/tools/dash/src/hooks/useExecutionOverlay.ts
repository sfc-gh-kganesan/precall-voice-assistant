import { useMemo } from 'react';
import type { LogEntry, RunStatus } from '@/api/types';
import type {
    ExecutionState,
    WorkflowGraphDef,
} from '@/components/WorkflowGraph';

export function useExecutionOverlay(
    graph: WorkflowGraphDef | null | undefined,
    runStatus: RunStatus | undefined,
    logs: LogEntry[] | undefined,
    pendingInterruptNodeId: string | null | undefined,
): Record<string, ExecutionState> {
    return useMemo(() => {
        if (!graph) return {};
        const states: Record<string, ExecutionState> = {};

        for (const node of graph.nodes) {
            states[node.id] = 'idle';
        }

        if (!runStatus || runStatus === 'running') {
            const mentionedNodes = new Set<string>();
            if (logs) {
                for (const log of logs) {
                    const nodeId = (log.attributes?.nodeId as string) ?? null;
                    if (nodeId && states[nodeId] !== undefined) {
                        mentionedNodes.add(nodeId);
                    }
                }
            }

            const nodeIds = graph.nodes.map((n) => n.id);
            let lastMentioned: string | null = null;
            for (const id of nodeIds) {
                if (mentionedNodes.has(id)) {
                    lastMentioned = id;
                }
            }

            for (const id of mentionedNodes) {
                states[id] = id === lastMentioned ? 'running' : 'completed';
            }

            if (
                pendingInterruptNodeId &&
                states[pendingInterruptNodeId] !== undefined
            ) {
                states[pendingInterruptNodeId] = 'waiting';
            }

            const startNode = graph.nodes.find((n) => n.type === 'start_node');
            if (startNode && runStatus === 'running') {
                if (states[startNode.id] === 'idle') {
                    states[startNode.id] =
                        mentionedNodes.size === 0 ? 'running' : 'completed';
                }
            }
        } else if (runStatus === 'completed') {
            for (const node of graph.nodes) {
                states[node.id] = 'completed';
            }
        } else if (runStatus === 'failed') {
            const mentionedNodes = new Set<string>();
            if (logs) {
                for (const log of logs) {
                    const nodeId = (log.attributes?.nodeId as string) ?? null;
                    if (nodeId && states[nodeId] !== undefined) {
                        mentionedNodes.add(nodeId);
                    }
                }
            }

            const nodeIds = graph.nodes.map((n) => n.id);
            let lastMentioned: string | null = null;
            for (const id of nodeIds) {
                if (mentionedNodes.has(id)) {
                    lastMentioned = id;
                }
            }

            for (const id of mentionedNodes) {
                states[id] = id === lastMentioned ? 'failed' : 'completed';
            }

            const startNode = graph.nodes.find((n) => n.type === 'start_node');
            if (startNode && states[startNode.id] === 'idle') {
                states[startNode.id] = 'completed';
            }
        } else if (runStatus === 'interrupted') {
            const mentionedNodes = new Set<string>();
            if (logs) {
                for (const log of logs) {
                    const nodeId = (log.attributes?.nodeId as string) ?? null;
                    if (nodeId && states[nodeId] !== undefined) {
                        mentionedNodes.add(nodeId);
                    }
                }
            }

            for (const id of mentionedNodes) {
                states[id] = 'completed';
            }

            if (
                pendingInterruptNodeId &&
                states[pendingInterruptNodeId] !== undefined
            ) {
                states[pendingInterruptNodeId] = 'waiting';
            }

            const startNode = graph.nodes.find((n) => n.type === 'start_node');
            if (startNode && states[startNode.id] === 'idle') {
                states[startNode.id] = 'completed';
            }
        }

        return states;
    }, [graph, runStatus, logs, pendingInterruptNodeId]);
}
