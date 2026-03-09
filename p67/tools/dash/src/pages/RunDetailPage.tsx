import { StatusBadge } from '@snowflake/stellar-components';
import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import type { LogEntry, LogSource } from '@/api/types';
import { AppShell } from '@/components/AppShell';
import { useLogs } from '@/hooks/useLogs';
import { useRuns } from '@/hooks/useRuns';
import { useRunStatus } from '@/hooks/useWorkflows';

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
    const [sourceFilter, setSourceFilter] = useState<LogSource | undefined>(
        undefined,
    );
    const [autoRefresh, setAutoRefresh] = useState(true);

    const { data: logsData, isLoading } = useLogs(
        workflowId ?? '',
        runId ?? '',
        {
            source: sourceFilter,
            autoRefresh,
        },
    );

    const { data: runStatus } = useRunStatus(runId ?? null);

    const run = runsData?.runs.find((r) => r.id === runId);

    return (
        <AppShell>
            <div className="page-container">
                <div className="breadcrumb">
                    <Link to="/">Workflows</Link>
                    <span>/</span>
                    <Link to={`/workflow/${workflowId}`}>{workflowId}</Link>
                    <span>/</span>
                    <span style={{ color: 'var(--sf-gray-700)' }}>
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
                                        <circle cx="12" cy="12" r="10" />
                                        <polyline points="12 6 12 12 16 14" />
                                    </svg>
                                    Started{' '}
                                    {new Date(run.startedAt).toLocaleString()}
                                </span>
                                {run.completedAt && (
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
                                            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                                            <polyline points="22 4 12 14.01 9 11.01" />
                                        </svg>
                                        Completed{' '}
                                        {new Date(
                                            run.completedAt,
                                        ).toLocaleString()}
                                    </span>
                                )}
                            </div>
                        )}
                    </div>
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

                {runStatus && runStatus.status !== 'running' && (
                    <div className="card" style={{ marginBottom: '24px' }}>
                        <div className="card-header">
                            <span className="card-title">Run Result</span>
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
                        <div className="card-body">
                            {runStatus.result !== undefined && (
                                <div style={{ marginBottom: '12px' }}>
                                    <p className="form-label">Result:</p>
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
                                        <p className="form-label">Output:</p>
                                        <pre className="code-block">
                                            {runStatus.stdout.join('\n')}
                                        </pre>
                                    </div>
                                )}
                            {runStatus.stderr &&
                                runStatus.stderr.length > 0 && (
                                    <div style={{ marginBottom: '12px' }}>
                                        <p className="form-label">Stderr:</p>
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
                                            Errors:
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
                                    <p style={{ color: 'var(--sf-gray-500)' }}>
                                        No result data available for this run.
                                    </p>
                                )}
                        </div>
                    </div>
                )}

                <div className="card">
                    <div
                        className="card-header"
                        style={{ flexWrap: 'wrap', gap: '12px' }}
                    >
                        <span className="card-title">
                            Logs ({logsData?.total ?? 0})
                        </span>
                        <div
                            style={{
                                display: 'flex',
                                gap: '8px',
                                alignItems: 'center',
                            }}
                        >
                            <span
                                style={{
                                    fontSize: '13px',
                                    color: 'var(--sf-gray-500)',
                                }}
                            >
                                Filter:
                            </span>
                            {LOG_SOURCES.map((source) => (
                                <button
                                    type="button"
                                    key={source.label}
                                    className={`tab ${sourceFilter === source.value ? 'active' : ''}`}
                                    onClick={() =>
                                        setSourceFilter(source.value)
                                    }
                                    style={{
                                        padding: '6px 12px',
                                        fontSize: '13px',
                                        fontWeight: 500,
                                        color:
                                            sourceFilter === source.value
                                                ? 'var(--sf-blue-600)'
                                                : 'var(--sf-gray-500)',
                                        cursor: 'pointer',
                                        border: '1px solid',
                                        borderColor:
                                            sourceFilter === source.value
                                                ? 'var(--sf-blue-600)'
                                                : 'var(--sf-gray-200)',
                                        borderRadius: '6px',
                                        background:
                                            sourceFilter === source.value
                                                ? 'var(--sf-gray-50)'
                                                : 'var(--sf-surface)',
                                    }}
                                >
                                    {source.label}
                                </button>
                            ))}
                            <span
                                style={{
                                    margin: '0 8px',
                                    color: 'var(--sf-gray-300)',
                                }}
                            >
                                |
                            </span>
                            <button
                                type="button"
                                onClick={() => setAutoRefresh(!autoRefresh)}
                                style={{
                                    padding: '6px 12px',
                                    fontSize: '13px',
                                    fontWeight: 500,
                                    color: autoRefresh
                                        ? 'var(--sf-green-500)'
                                        : 'var(--sf-gray-500)',
                                    cursor: 'pointer',
                                    border: '1px solid',
                                    borderColor: autoRefresh
                                        ? 'var(--sf-green-500)'
                                        : 'var(--sf-gray-200)',
                                    borderRadius: '6px',
                                    background: 'var(--sf-surface)',
                                }}
                            >
                                {autoRefresh ? '● Live' : '○ Paused'}
                            </button>
                        </div>
                    </div>

                    {isLoading && (
                        <div className="card-body">
                            <p style={{ color: 'var(--sf-gray-500)' }}>
                                Loading logs...
                            </p>
                        </div>
                    )}

                    {!isLoading && logsData && (
                        <div className="log-container">
                            {logsData.logs.map((log) => (
                                <LogLine key={log.id} log={log} />
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
                </div>
            </div>
        </AppShell>
    );
}

function LogLine({ log }: { log: LogEntry }) {
    const [expanded, setExpanded] = useState(false);
    const hasAttributes = Object.keys(log.attributes).length > 0;

    const sourceClass: Record<LogSource, string> = {
        RuntimeHost: 'runtime',
        WorkflowNode: 'workflow',
        ToolCall: 'tool',
    };

    return (
        <div style={{ marginBottom: '2px' }}>
            <div className="log-line">
                <span className="log-time">
                    {new Date(log.timestamp).toLocaleTimeString('en-US', {
                        hour12: false,
                    })}
                </span>
                <span className={`log-source ${sourceClass[log.source]}`}>
                    [{log.source.padEnd(12)}]
                </span>
                <span style={{ flex: 1 }}>{log.message}</span>
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
                            fontSize: '12px',
                        }}
                    >
                        {expanded ? '▼' : '▶'}
                    </button>
                )}
            </div>
            {expanded && hasAttributes && (
                <pre
                    style={{
                        marginLeft: '180px',
                        marginTop: '4px',
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
