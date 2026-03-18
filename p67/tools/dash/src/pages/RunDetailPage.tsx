import { StatusBadge } from '@snowflake/stellar-components';
import { useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import type { LogEntry, LogSource } from '@/api/types';
import { AppShell } from '@/components/AppShell';
import { CollapsibleSection } from '@/components/CollapsibleSection';
import type { WorkflowGraphDef } from '@/components/WorkflowGraph';
import { WorkflowGraph } from '@/components/WorkflowGraph';
import { useExecutionOverlay } from '@/hooks/useExecutionOverlay';
import { useInterrupts } from '@/hooks/useInterrupts';
import { useLogs } from '@/hooks/useLogs';
import { useRuns } from '@/hooks/useRuns';
import { useWorkflowGraph } from '@/hooks/useWorkflowGraph';
import { useRunStatus, useWorkflows } from '@/hooks/useWorkflows';
import { formatDuration, timeAgo } from '@/utils/time';

const LOG_SOURCES: Array<{ value: LogSource | undefined; label: string }> = [
    { value: undefined, label: 'All' },
    { value: 'RuntimeHost', label: 'Runtime' },
    { value: 'WorkflowNode', label: 'Workflow' },
    { value: 'ToolCall', label: 'Tool' },
];

export function RunDetailPage() {
    const { workflowId, runId } = useParams<{
        workflowId: string;
        runId: string;
    }>();
    const { data: runsData } = useRuns(workflowId ?? '');
    const { data: workflowsData } = useWorkflows();
    const { data: graphData } = useWorkflowGraph(workflowId ?? '');
    const [sourceFilter, setSourceFilter] = useState<LogSource | undefined>(
        undefined,
    );
    const [autoRefresh, setAutoRefresh] = useState(true);
    const logContainerRef = useRef<HTMLDivElement>(null);

    const { data: logsData, isLoading } = useLogs(
        workflowId ?? '',
        runId ?? '',
        { source: sourceFilter, autoRefresh },
    );

    const { data: runStatus } = useRunStatus(runId ?? null);
    const run = runsData?.runs.find((r) => r.id === runId);

    const isInterrupted =
        run?.status === 'interrupted' || runStatus?.status === 'interrupted';
    const { data: interruptsData } = useInterrupts({
        runId: runId ?? undefined,
    });
    const pendingInterrupts = isInterrupted
        ? (interruptsData?.interrupts ?? [])
        : [];

    const workflow = workflowsData?.workflows.find(
        (w) => w.workflowId === workflowId,
    );
    const workflowName = workflow?.name || workflowId || '';

    const hasGraph = !!graphData?.graph;

    const pendingInterruptNodeId = runStatus?.pendingInterrupt?.nodeId ?? null;
    const executionStates = useExecutionOverlay(
        graphData?.graph as WorkflowGraphDef | null | undefined,
        runStatus?.status ?? run?.status,
        logsData?.logs,
        pendingInterruptNodeId,
    );

    useEffect(() => {
        if (autoRefresh && logContainerRef.current) {
            const el = logContainerRef.current;
            el.scrollTop = el.scrollHeight;
        }
    }, [autoRefresh]);

    return (
        <AppShell>
            <div className="page-container">
                <div className="breadcrumb">
                    <Link to="/">Workflows</Link>
                    <span>/</span>
                    <Link to={`/workflow/${workflowId}`}>{workflowName}</Link>
                    <span>/</span>
                    <span
                        style={{ color: 'var(--sf-gray-700)', fontWeight: 500 }}
                    >
                        Run {runId?.slice(0, 8)}
                    </span>
                </div>

                <div
                    className="page-header"
                    style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'flex-start',
                    }}
                >
                    <div>
                        <h1 className="page-title">Run Details</h1>
                        {run && (
                            <div className="metadata-row">
                                <span
                                    className="metadata-item"
                                    title={new Date(
                                        run.startedAt,
                                    ).toLocaleString()}
                                >
                                    <svg
                                        aria-hidden="true"
                                        width="14"
                                        height="14"
                                        viewBox="0 0 24 24"
                                        fill="none"
                                        stroke="currentColor"
                                        strokeWidth="2"
                                    >
                                        <circle cx="12" cy="12" r="10" />
                                        <polyline points="12 6 12 12 16 14" />
                                    </svg>
                                    Started {timeAgo(run.startedAt)}
                                </span>
                                <span className="metadata-item">
                                    <svg
                                        aria-hidden="true"
                                        width="14"
                                        height="14"
                                        viewBox="0 0 24 24"
                                        fill="none"
                                        stroke="currentColor"
                                        strokeWidth="2"
                                    >
                                        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                                    </svg>
                                    <span className="duration-badge">
                                        {formatDuration(
                                            run.startedAt,
                                            run.completedAt,
                                        )}
                                    </span>
                                </span>
                            </div>
                        )}
                    </div>
                    <div
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 8,
                        }}
                    >
                        {run && (
                            <StatusBadge
                                variant={
                                    run.status === 'completed'
                                        ? 'success'
                                        : run.status === 'failed'
                                          ? 'critical'
                                          : run.status === 'interrupted'
                                            ? 'caution'
                                            : 'active'
                                }
                            >
                                {run.status === 'completed'
                                    ? 'Success'
                                    : run.status === 'failed'
                                      ? 'Failed'
                                      : run.status === 'interrupted'
                                        ? 'Interrupted'
                                        : 'Running'}
                            </StatusBadge>
                        )}
                    </div>
                </div>

                {isInterrupted && pendingInterrupts.length > 0 && (
                    <div
                        className="card"
                        style={{
                            marginBottom: '16px',
                            borderLeft: '3px solid var(--sf-yellow-500)',
                        }}
                    >
                        <div
                            className="card-body"
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                            }}
                        >
                            <div
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '10px',
                                }}
                            >
                                <svg
                                    aria-hidden="true"
                                    width="18"
                                    height="18"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="var(--sf-yellow-500)"
                                    strokeWidth="2"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                >
                                    <circle cx="12" cy="12" r="10" />
                                    <line x1="12" y1="8" x2="12" y2="12" />
                                    <line x1="12" y1="16" x2="12.01" y2="16" />
                                </svg>
                                <span
                                    style={{
                                        fontSize: '13px',
                                        fontWeight: 500,
                                    }}
                                >
                                    This run is waiting for human input (
                                    {pendingInterrupts.length} interrupt
                                    {pendingInterrupts.length !== 1 ? 's' : ''})
                                </span>
                            </div>
                            <Link
                                to="/interrupts"
                                style={{
                                    fontSize: '13px',
                                    fontWeight: 600,
                                    color: 'var(--sf-blue-600)',
                                    textDecoration: 'none',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '4px',
                                }}
                            >
                                View Interrupts
                                <svg
                                    aria-hidden="true"
                                    width="14"
                                    height="14"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="2"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                >
                                    <polyline points="9 18 15 12 9 6" />
                                </svg>
                            </Link>
                        </div>
                    </div>
                )}

                {hasGraph && graphData?.graph && (
                    <CollapsibleSection title="Execution Graph">
                        <div style={{ padding: 0 }}>
                            <WorkflowGraph
                                graph={graphData.graph as WorkflowGraphDef}
                                executionStates={executionStates}
                                height={480}
                            />
                        </div>
                    </CollapsibleSection>
                )}

                {runStatus && runStatus.status !== 'running' && (
                    <CollapsibleSection title="Run Result" defaultOpen={true}>
                        <div style={{ padding: 20 }}>
                            <div
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 12,
                                    marginBottom: 12,
                                }}
                            >
                                <StatusBadge
                                    variant={
                                        runStatus.status === 'completed'
                                            ? 'success'
                                            : runStatus.status === 'failed'
                                              ? 'critical'
                                              : 'caution'
                                    }
                                >
                                    {runStatus.status}
                                </StatusBadge>
                            </div>
                            {runStatus.result !== undefined && (
                                <div style={{ marginBottom: '12px' }}>
                                    <p className="form-label">Result</p>
                                    <pre className="code-block">
                                        {typeof runStatus.result === 'string'
                                            ? runStatus.result
                                            : JSON.stringify(
                                                  runStatus.result,
                                                  null,
                                                  2,
                                              )}
                                    </pre>
                                </div>
                            )}
                            {runStatus.stdout &&
                                runStatus.stdout.length > 0 && (
                                    <div style={{ marginBottom: '12px' }}>
                                        <p className="form-label">Output</p>
                                        <pre className="code-block">
                                            {runStatus.stdout.join('\n')}
                                        </pre>
                                    </div>
                                )}
                            {runStatus.stderr &&
                                runStatus.stderr.length > 0 && (
                                    <div style={{ marginBottom: '12px' }}>
                                        <p className="form-label">Stderr</p>
                                        <pre
                                            className="code-block"
                                            style={{
                                                color: 'var(--sf-red-500)',
                                            }}
                                        >
                                            {runStatus.stderr.join('\n')}
                                        </pre>
                                    </div>
                                )}
                            {runStatus.errors &&
                                runStatus.errors.length > 0 && (
                                    <div>
                                        <p
                                            className="form-label"
                                            style={{
                                                color: 'var(--sf-red-500)',
                                            }}
                                        >
                                            Errors
                                        </p>
                                        <pre
                                            className="code-block"
                                            style={{
                                                color: 'var(--sf-red-500)',
                                            }}
                                        >
                                            {runStatus.errors
                                                .map(
                                                    (e) =>
                                                        `${e.error}: ${e.message}`,
                                                )
                                                .join('\n')}
                                        </pre>
                                    </div>
                                )}
                            {runStatus.result === undefined &&
                                (!runStatus.stdout ||
                                    runStatus.stdout.length === 0) &&
                                (!runStatus.errors ||
                                    runStatus.errors.length === 0) && (
                                    <p className="text-muted text-sm">
                                        No result data available for this run.
                                    </p>
                                )}
                        </div>
                    </CollapsibleSection>
                )}

                <CollapsibleSection
                    title="Logs"
                    badge={
                        <span className="text-muted text-xs">
                            {logsData?.total ?? 0}
                        </span>
                    }
                >
                    <div
                        style={{
                            padding: '8px 16px',
                            display: 'flex',
                            gap: '8px',
                            alignItems: 'center',
                            flexWrap: 'wrap',
                            borderBottom: '1px solid var(--sf-gray-100)',
                        }}
                    >
                        <div className="log-toolbar">
                            {LOG_SOURCES.map((source) => (
                                <button
                                    type="button"
                                    key={source.label}
                                    className={`log-filter-btn ${sourceFilter === source.value ? 'active' : ''}`}
                                    onClick={() =>
                                        setSourceFilter(source.value)
                                    }
                                >
                                    {source.label}
                                </button>
                            ))}
                            <span
                                style={{
                                    width: '1px',
                                    height: '16px',
                                    background: 'var(--sf-gray-200)',
                                    margin: '0 4px',
                                }}
                            />
                            <button
                                type="button"
                                onClick={() => setAutoRefresh(!autoRefresh)}
                                className={`log-live-btn ${autoRefresh ? 'live' : 'paused'}`}
                            >
                                {autoRefresh ? 'Live' : 'Paused'}
                            </button>
                        </div>
                    </div>

                    {isLoading && (
                        <div style={{ padding: 20 }}>
                            <div
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px',
                                    color: 'var(--sf-gray-500)',
                                }}
                            >
                                <span className="spinner" />
                                Loading logs...
                            </div>
                        </div>
                    )}

                    {!isLoading && logsData && (
                        <div className="log-container" ref={logContainerRef}>
                            {logsData.logs.map((log, idx) => (
                                <LogLine
                                    key={log.id}
                                    log={log}
                                    lineNumber={idx + 1}
                                />
                            ))}
                            {logsData.logs.length === 0 && (
                                <p
                                    style={{
                                        color: 'var(--sf-gray-500)',
                                        textAlign: 'center',
                                        padding: '24px',
                                    }}
                                >
                                    No logs found
                                </p>
                            )}
                        </div>
                    )}
                </CollapsibleSection>
            </div>
        </AppShell>
    );
}

function LogLine({ log, lineNumber }: { log: LogEntry; lineNumber: number }) {
    const [expanded, setExpanded] = useState(false);
    const hasAttributes = Object.keys(log.attributes).length > 0;

    const sourceClass: Record<LogSource, string> = {
        RuntimeHost: 'runtime',
        WorkflowNode: 'workflow',
        ToolCall: 'tool',
    };

    return (
        <div style={{ marginBottom: '1px' }}>
            <div className="log-line">
                <span className="log-line-number">{lineNumber}</span>
                <span className="log-time">
                    {new Date(log.timestamp).toLocaleTimeString('en-US', {
                        hour12: false,
                    })}
                </span>
                <span className={`log-source ${sourceClass[log.source]}`}>
                    {log.source.slice(0, 8).padEnd(8)}
                </span>
                <span style={{ flex: 1, wordBreak: 'break-word' }}>
                    {log.message}
                </span>
                {hasAttributes && (
                    <button
                        type="button"
                        onClick={() => setExpanded(!expanded)}
                        style={{
                            padding: '2px 6px',
                            minWidth: 'auto',
                            background: 'transparent',
                            border: 'none',
                            color: 'var(--sf-gray-400)',
                            cursor: 'pointer',
                            fontSize: '11px',
                            flexShrink: 0,
                        }}
                    >
                        {expanded ? '[-]' : '[+]'}
                    </button>
                )}
            </div>
            {expanded && hasAttributes && (
                <pre
                    style={{
                        marginLeft: '60px',
                        marginTop: '2px',
                        padding: '8px 12px',
                        backgroundColor: 'var(--sf-log-attr-bg)',
                        borderRadius: '4px',
                        fontSize: '11px',
                        color: 'var(--sf-gray-400)',
                    }}
                >
                    {JSON.stringify(log.attributes, null, 2)}
                </pre>
            )}
        </div>
    );
}
