import { Button, StatusBadge, TextInput } from '@snowflake/stellar-components';
import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import type { RunEntry, WorkflowRunStatusResponse } from '@/api/types';
import { AppShell } from '@/components/AppShell';
import { CollapsibleSection } from '@/components/CollapsibleSection';
import { SortableHeader } from '@/components/SortableHeader';
import type { WorkflowGraphDef } from '@/components/WorkflowGraph';
import { WorkflowGraph } from '@/components/WorkflowGraph';
import { useRuns } from '@/hooks/useRuns';
import { useSort } from '@/hooks/useSort';
import { useWorkflowGraph } from '@/hooks/useWorkflowGraph';
import {
    useRunStatus,
    useRunWorkflow,
    useSetVisibility,
    useWorkflowManifest,
    useWorkflows,
} from '@/hooks/useWorkflows';
import { formatDuration, timeAgo } from '@/utils/time';

export function WorkflowDetailPage() {
    const { workflowId } = useParams<{ workflowId: string }>();
    const { data: workflowsData } = useWorkflows();
    const { data: manifestData } = useWorkflowManifest(workflowId ?? '');
    const { data: graphData } = useWorkflowGraph(workflowId ?? '');
    const { data: runsData, isLoading: runsLoading } = useRuns(
        workflowId ?? '',
    );
    const runWorkflow = useRunWorkflow();
    const setVisibility = useSetVisibility();
    const {
        sortKey: runSortKey,
        sortDir: runSortDir,
        onSort: onRunSort,
        sortData: sortRuns,
    } = useSort<RunEntry>('startedAt', 'desc');

    const workflow = workflowsData?.workflows.find(
        (w) => w.workflowId === workflowId,
    );
    const [params, setParams] = useState<Record<string, string>>({});
    const [isRunning, setIsRunning] = useState(false);
    const [executionResult, setExecutionResult] =
        useState<WorkflowRunStatusResponse | null>(null);

    const hasGraph = !!graphData?.graph;
    const manifestParams = manifestData?.params ?? {};
    const hasParams = Object.keys(manifestParams).length > 0;

    const latestRunId = useMemo(() => {
        if (!runsData?.runs.length) return null;
        return runsData.runs[0].id;
    }, [runsData]);

    const { data: latestRunStatus } = useRunStatus(
        !executionResult ? latestRunId : null,
    );

    const lastResult = executionResult ?? latestRunStatus ?? null;

    const handleRun = async () => {
        if (!workflowId) return;
        setIsRunning(true);
        setExecutionResult(null);
        try {
            const result = await runWorkflow.mutateAsync({
                workflowId,
                params,
            });
            if ('runId' in result) {
                setExecutionResult(result as WorkflowRunStatusResponse);
            }
        } finally {
            setIsRunning(false);
        }
    };

    const handleVisibilityToggle = () => {
        if (!workflow || !workflowId) return;
        const newVisibility =
            workflow.visibility === 'Public' ? 'Private' : 'Public';
        setVisibility.mutate({ workflowId, visibility: newVisibility });
    };

    const displayName = workflow?.name || workflowId || '';

    if (!workflow) {
        return (
            <AppShell>
                <div className="page-container">
                    <div
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            color: 'var(--sf-gray-500)',
                        }}
                    >
                        <span className="spinner" />
                        Loading workflow...
                    </div>
                </div>
            </AppShell>
        );
    }

    const totalRuns = runsData?.runs.length ?? 0;
    const successfulRuns =
        runsData?.runs.filter((r) => r.status === 'completed').length ?? 0;
    const failedRuns =
        runsData?.runs.filter((r) => r.status === 'failed').length ?? 0;

    return (
        <AppShell>
            <div className="page-container">
                <div className="breadcrumb">
                    <Link to="/">Workflows</Link>
                    <span>/</span>
                    <span
                        style={{ color: 'var(--sf-gray-700)', fontWeight: 500 }}
                    >
                        {displayName}
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
                        <h1 className="page-title">{displayName}</h1>
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
                                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                                    <circle cx="12" cy="7" r="4" />
                                </svg>
                                {workflow.owner}
                            </span>
                            <span
                                className="metadata-item"
                                title={new Date(
                                    workflow.createdAt,
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
                                    <rect
                                        x="3"
                                        y="4"
                                        width="18"
                                        height="18"
                                        rx="2"
                                        ry="2"
                                    />
                                    <line x1="16" y1="2" x2="16" y2="6" />
                                    <line x1="8" y1="2" x2="8" y2="6" />
                                    <line x1="3" y1="10" x2="21" y2="10" />
                                </svg>
                                Created {timeAgo(workflow.createdAt)}
                            </span>
                        </div>
                    </div>
                    <div
                        style={{
                            display: 'flex',
                            gap: '8px',
                            alignItems: 'center',
                        }}
                    >
                        <StatusBadge
                            variant={
                                workflow.visibility === 'Public'
                                    ? 'success'
                                    : 'neutral'
                            }
                        >
                            {workflow.visibility}
                        </StatusBadge>
                        <Button
                            size="small"
                            variant="secondary"
                            onClick={handleVisibilityToggle}
                        >
                            Make{' '}
                            {workflow.visibility === 'Public'
                                ? 'Private'
                                : 'Public'}
                        </Button>
                    </div>
                </div>

                <div className="stats-grid">
                    <div className="stat-card">
                        <div className="stat-label">Total Runs</div>
                        <div className="stat-value">{totalRuns}</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-label">Successful</div>
                        <div
                            className="stat-value"
                            style={{ color: 'var(--sf-green-500)' }}
                        >
                            {successfulRuns}
                        </div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-label">Failed</div>
                        <div
                            className="stat-value"
                            style={{ color: 'var(--sf-red-500)' }}
                        >
                            {failedRuns}
                        </div>
                    </div>
                </div>

                {hasGraph && graphData?.graph && (
                    <CollapsibleSection title="Workflow Graph">
                        <div style={{ padding: 0 }}>
                            <WorkflowGraph
                                graph={graphData.graph as WorkflowGraphDef}
                                height={480}
                            />
                        </div>
                    </CollapsibleSection>
                )}

                {hasParams && (
                    <CollapsibleSection title="Parameters">
                        <div style={{ padding: 20 }}>
                            <div
                                style={{
                                    display: 'grid',
                                    gridTemplateColumns:
                                        'repeat(auto-fit, minmax(280px, 1fr))',
                                    gap: '16px',
                                    marginBottom: 16,
                                }}
                            >
                                {Object.entries(manifestParams).map(
                                    ([key, value]) => (
                                        <div key={key} className="form-group">
                                            <label
                                                htmlFor={`param-${key}`}
                                                className="form-label"
                                            >
                                                {key}
                                                {value.required && (
                                                    <span className="required-indicator">
                                                        {' '}
                                                        *
                                                    </span>
                                                )}
                                            </label>
                                            {value.description && (
                                                <p className="form-hint">
                                                    {value.description}
                                                </p>
                                            )}
                                            <TextInput
                                                id={`param-${key}`}
                                                placeholder={
                                                    value.value ||
                                                    `Enter ${key}`
                                                }
                                                value={params[key] || ''}
                                                onChange={(e) =>
                                                    setParams({
                                                        ...params,
                                                        [key]: e.target.value,
                                                    })
                                                }
                                                aria-label={key}
                                            />
                                        </div>
                                    ),
                                )}
                            </div>
                            <Button onClick={handleRun} disabled={isRunning}>
                                {isRunning ? (
                                    <span
                                        style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '6px',
                                        }}
                                    >
                                        <span className="spinner" />
                                        Running...
                                    </span>
                                ) : (
                                    'Run Workflow'
                                )}
                            </Button>
                        </div>
                    </CollapsibleSection>
                )}

                {!hasParams && (
                    <div className="run-button-area">
                        <Button onClick={handleRun} disabled={isRunning}>
                            {isRunning ? (
                                <span
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '6px',
                                    }}
                                >
                                    <span className="spinner" />
                                    Running...
                                </span>
                            ) : (
                                'Run Workflow'
                            )}
                        </Button>
                    </div>
                )}

                <CollapsibleSection
                    title="Run History"
                    badge={
                        totalRuns > 0 ? (
                            <span className="text-muted text-xs">
                                {totalRuns} runs
                            </span>
                        ) : undefined
                    }
                >
                    {lastResult && (
                        <div
                            style={{
                                padding: 20,
                                borderBottom: '1px solid var(--sf-gray-100)',
                            }}
                        >
                            <div
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'space-between',
                                    marginBottom: 12,
                                }}
                            >
                                <div
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '12px',
                                    }}
                                >
                                    <span
                                        style={{
                                            fontSize: 12,
                                            fontWeight: 600,
                                            color: 'var(--sf-gray-600)',
                                            textTransform: 'uppercase',
                                            letterSpacing: '0.04em',
                                        }}
                                    >
                                        Latest Run
                                    </span>
                                    <Link
                                        to={`/workflow/${workflowId}/run/${lastResult.runId}`}
                                        className="link"
                                        style={{
                                            fontSize: '12px',
                                            fontFamily: 'monospace',
                                        }}
                                    >
                                        {lastResult.runId.slice(0, 8)}
                                    </Link>
                                </div>
                                <StatusBadge
                                    variant={
                                        lastResult.status === 'completed'
                                            ? 'success'
                                            : lastResult.status === 'failed'
                                              ? 'critical'
                                              : 'caution'
                                    }
                                >
                                    {lastResult.status}
                                </StatusBadge>
                            </div>
                            {lastResult.result !== undefined && (
                                <div style={{ marginBottom: '12px' }}>
                                    <p className="form-label">Result</p>
                                    <pre className="code-block">
                                        {typeof lastResult.result === 'string'
                                            ? lastResult.result
                                            : JSON.stringify(
                                                  lastResult.result,
                                                  null,
                                                  2,
                                              )}
                                    </pre>
                                </div>
                            )}
                            {lastResult.stdout &&
                                lastResult.stdout.length > 0 && (
                                    <div style={{ marginBottom: '12px' }}>
                                        <p className="form-label">Output</p>
                                        <pre className="code-block">
                                            {lastResult.stdout.join('\n')}
                                        </pre>
                                    </div>
                                )}
                            {lastResult.errors &&
                                lastResult.errors.length > 0 && (
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
                                            {lastResult.errors
                                                .map(
                                                    (e) =>
                                                        `${e.error}: ${e.message}`,
                                                )
                                                .join('\n')}
                                        </pre>
                                    </div>
                                )}
                            {lastResult.result === undefined &&
                                (!lastResult.stdout ||
                                    lastResult.stdout.length === 0) &&
                                (!lastResult.errors ||
                                    lastResult.errors.length === 0) && (
                                    <p className="text-muted text-sm">
                                        No result data available for this run.
                                    </p>
                                )}
                        </div>
                    )}

                    {runsLoading && (
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
                                Loading runs...
                            </div>
                        </div>
                    )}

                    {!runsLoading && runsData && (
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Run ID</th>
                                    <SortableHeader
                                        label="Started"
                                        sortKey="startedAt"
                                        currentSort={runSortKey as string}
                                        currentDir={runSortDir}
                                        onSort={(k) =>
                                            onRunSort(k as keyof RunEntry)
                                        }
                                    />
                                    <SortableHeader
                                        label="Duration"
                                        sortKey="completedAt"
                                        currentSort={runSortKey as string}
                                        currentDir={runSortDir}
                                        onSort={(k) =>
                                            onRunSort(k as keyof RunEntry)
                                        }
                                    />
                                    <SortableHeader
                                        label="Status"
                                        sortKey="status"
                                        currentSort={runSortKey as string}
                                        currentDir={runSortDir}
                                        onSort={(k) =>
                                            onRunSort(k as keyof RunEntry)
                                        }
                                    />
                                    <th>Logs</th>
                                    <th style={{ width: '60px' }}></th>
                                </tr>
                            </thead>
                            <tbody>
                                {sortRuns(runsData.runs).map((run) => (
                                    <tr key={run.id}>
                                        <td
                                            style={{
                                                fontFamily: 'monospace',
                                                fontSize: '12px',
                                            }}
                                        >
                                            {run.id.slice(0, 8)}
                                        </td>
                                        <td
                                            className="text-muted text-sm"
                                            title={new Date(
                                                run.startedAt,
                                            ).toLocaleString()}
                                        >
                                            {timeAgo(run.startedAt)}
                                        </td>
                                        <td>
                                            <span className="duration-badge">
                                                {formatDuration(
                                                    run.startedAt,
                                                    run.completedAt,
                                                )}
                                            </span>
                                        </td>
                                        <td>
                                            <div
                                                style={{
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '6px',
                                                }}
                                            >
                                                <StatusBadge
                                                    variant={
                                                        run.status ===
                                                        'completed'
                                                            ? 'success'
                                                            : run.status ===
                                                                'failed'
                                                              ? 'critical'
                                                              : run.status ===
                                                                  'interrupted'
                                                                ? 'caution'
                                                                : 'active'
                                                    }
                                                >
                                                    {run.status === 'completed'
                                                        ? 'Success'
                                                        : run.status ===
                                                            'failed'
                                                          ? 'Failed'
                                                          : run.status ===
                                                              'interrupted'
                                                            ? 'Interrupted'
                                                            : 'Running'}
                                                </StatusBadge>
                                                {run.status ===
                                                    'interrupted' && (
                                                    <Link
                                                        to="/interrupts"
                                                        title="View interrupts for this run"
                                                        style={{
                                                            display: 'flex',
                                                            alignItems:
                                                                'center',
                                                            color: 'var(--sf-yellow-500)',
                                                        }}
                                                    >
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
                                                            <circle
                                                                cx="12"
                                                                cy="12"
                                                                r="10"
                                                            />
                                                            <line
                                                                x1="12"
                                                                y1="8"
                                                                x2="12"
                                                                y2="12"
                                                            />
                                                            <line
                                                                x1="12"
                                                                y1="16"
                                                                x2="12.01"
                                                                y2="16"
                                                            />
                                                        </svg>
                                                    </Link>
                                                )}
                                            </div>
                                        </td>
                                        <td className="text-sm">
                                            {run.logCount}
                                        </td>
                                        <td>
                                            <Link
                                                to={`/workflow/${workflowId}/run/${run.id}`}
                                            >
                                                <Button
                                                    size="small"
                                                    variant="secondary"
                                                >
                                                    View
                                                </Button>
                                            </Link>
                                        </td>
                                    </tr>
                                ))}
                                {runsData.runs.length === 0 && (
                                    <tr>
                                        <td colSpan={6}>
                                            <div className="empty-state">
                                                <div className="empty-state-title">
                                                    No runs yet
                                                </div>
                                                <p>
                                                    Click &ldquo;Run
                                                    Workflow&rdquo; to start
                                                    your first execution
                                                </p>
                                            </div>
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    )}
                </CollapsibleSection>
            </div>
        </AppShell>
    );
}
