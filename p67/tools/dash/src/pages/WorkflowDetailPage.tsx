import { Button, StatusBadge, TextInput } from '@snowflake/stellar-components';
import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import type { WorkflowRunStatusResponse } from '@/api/types';
import { AppShell } from '@/components/AppShell';
import { useRuns } from '@/hooks/useRuns';
import {
    useRunStatus,
    useRunWorkflow,
    useSetVisibility,
    useWorkflowManifest,
    useWorkflows,
} from '@/hooks/useWorkflows';

export function WorkflowDetailPage() {
    const { workflowId } = useParams<{ workflowId: string }>();
    const { data: workflowsData } = useWorkflows();
    const { data: manifestData } = useWorkflowManifest(workflowId ?? '');
    const { data: runsData, isLoading: runsLoading } = useRuns(
        workflowId ?? '',
    );
    const runWorkflow = useRunWorkflow();
    const setVisibility = useSetVisibility();

    const workflow = workflowsData?.workflows.find(
        (w) => w.workflowId === workflowId,
    );
    const [params, setParams] = useState<Record<string, string>>({});
    const [isRunning, setIsRunning] = useState(false);
    const [executionResult, setExecutionResult] =
        useState<WorkflowRunStatusResponse | null>(null);

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

    if (!workflow) {
        return (
            <AppShell>
                <div className="page-container">
                    <p style={{ color: 'var(--sf-gray-500)' }}>
                        Loading workflow...
                    </p>
                </div>
            </AppShell>
        );
    }

    const manifestParams = manifestData?.params ?? {};
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
                    <span style={{ color: 'var(--sf-gray-700)' }}>
                        {workflow.name || workflow.workflowId}
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
                        <h1 className="page-title">
                            {workflow.name || workflow.workflowId}
                        </h1>
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
                                Created{' '}
                                {new Date(
                                    workflow.createdAt,
                                ).toLocaleDateString()}
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
                            Toggle
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

                {Object.keys(manifestParams).length > 0 && (
                    <div className="card" style={{ marginBottom: '24px' }}>
                        <div className="card-header">
                            <span className="card-title">Parameters</span>
                        </div>
                        <div className="card-body">
                            <div
                                style={{
                                    display: 'grid',
                                    gridTemplateColumns:
                                        'repeat(auto-fit, minmax(280px, 1fr))',
                                    gap: '16px',
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
                        </div>
                    </div>
                )}

                <div style={{ marginBottom: '24px' }}>
                    <Button onClick={handleRun} disabled={isRunning}>
                        {isRunning ? 'Running...' : 'Run Workflow'}
                    </Button>
                </div>

                {lastResult && (
                    <div className="card" style={{ marginBottom: '24px' }}>
                        <div className="card-header">
                            <div
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '12px',
                                }}
                            >
                                <span className="card-title">
                                    Latest Run Result
                                </span>
                                <Link
                                    to={`/workflow/${workflowId}/run/${lastResult.runId}`}
                                    className="link"
                                    style={{ fontSize: '13px' }}
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
                        <div className="card-body">
                            {lastResult.result !== undefined && (
                                <div style={{ marginBottom: '12px' }}>
                                    <p className="form-label">Result:</p>
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
                                        <p className="form-label">Output:</p>
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
                                            Errors:
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
                                    <p style={{ color: 'var(--sf-gray-500)' }}>
                                        No result data available for this run.
                                    </p>
                                )}
                        </div>
                    </div>
                )}

                <div className="card">
                    <div className="card-header">
                        <span className="card-title">Run History</span>
                    </div>

                    {runsLoading && (
                        <div className="card-body">
                            <p style={{ color: 'var(--sf-gray-500)' }}>
                                Loading runs...
                            </p>
                        </div>
                    )}

                    {!runsLoading && runsData && (
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Run ID</th>
                                    <th>Started</th>
                                    <th>Completed</th>
                                    <th>Status</th>
                                    <th>Logs</th>
                                    <th></th>
                                </tr>
                            </thead>
                            <tbody>
                                {runsData.runs.map((run) => (
                                    <tr key={run.id}>
                                        <td
                                            style={{
                                                fontFamily: 'monospace',
                                                fontSize: '13px',
                                            }}
                                        >
                                            {run.id.slice(0, 8)}
                                        </td>
                                        <td
                                            style={{
                                                color: 'var(--sf-gray-500)',
                                            }}
                                        >
                                            {new Date(
                                                run.startedAt,
                                            ).toLocaleString()}
                                        </td>
                                        <td
                                            style={{
                                                color: 'var(--sf-gray-500)',
                                            }}
                                        >
                                            {run.completedAt
                                                ? new Date(
                                                      run.completedAt,
                                                  ).toLocaleString()
                                                : '—'}
                                        </td>
                                        <td>
                                            <StatusBadge
                                                variant={
                                                    run.status === 'completed'
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
                                                    : run.status === 'failed'
                                                      ? 'Failed'
                                                      : run.status ===
                                                          'interrupted'
                                                        ? 'Interrupted'
                                                        : 'Running'}
                                            </StatusBadge>
                                        </td>
                                        <td>{run.logCount}</td>
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
                                                <div className="empty-state-icon">
                                                    🚀
                                                </div>
                                                <div className="empty-state-title">
                                                    No runs yet
                                                </div>
                                                <p>
                                                    Click "Run Workflow" to
                                                    start your first execution
                                                </p>
                                            </div>
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    )}
                </div>
            </div>
        </AppShell>
    );
}
