import { Button, TextInput } from '@snowflake/stellar-components';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import type { Workflow } from '@/api/types';
import { AppShell } from '@/components/AppShell';
import { useWorkflows } from '@/hooks/useWorkflows';
import { timeAgo } from '@/utils/time';

export function WorkflowsPage() {
    const { data, isLoading, error } = useWorkflows();
    const [search, setSearch] = useState('');

    const workflows = data?.workflows ?? [];
    const filtered = workflows.filter(
        (w) =>
            w.name?.toLowerCase().includes(search.toLowerCase()) ||
            w.owner.toLowerCase().includes(search.toLowerCase()) ||
            w.workflowId.toLowerCase().includes(search.toLowerCase()),
    );

    const publicCount = workflows.filter(
        (w) => w.visibility === 'Public',
    ).length;
    const privateCount = workflows.filter(
        (w) => w.visibility === 'Private',
    ).length;

    return (
        <AppShell>
            <div className="page-container">
                <div
                    className="page-header"
                    style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'flex-start',
                    }}
                >
                    <div>
                        <h1 className="page-title">Workflows</h1>
                        <p className="page-subtitle">
                            Manage and monitor your automated workflows
                        </p>
                    </div>
                </div>

                <div className="stats-grid">
                    <StatCard
                        label="Total Workflows"
                        value={workflows.length}
                    />
                    <StatCard
                        label="Public"
                        value={publicCount}
                        color="var(--sf-green-500)"
                    />
                    <StatCard label="Private" value={privateCount} />
                </div>

                <div className="card">
                    <div className="card-header">
                        <span className="card-title">All Workflows</span>
                        <TextInput
                            placeholder="Search workflows..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            style={{ width: '260px' }}
                            aria-label="Search workflows"
                        />
                    </div>

                    {isLoading && (
                        <div className="card-body">
                            <div
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px',
                                    color: 'var(--sf-gray-500)',
                                }}
                            >
                                <span className="spinner" />
                                Loading workflows...
                            </div>
                        </div>
                    )}

                    {error && (
                        <div className="card-body">
                            <p style={{ color: 'var(--sf-red-500)' }}>
                                Error: {(error as Error).message}
                            </p>
                        </div>
                    )}

                    {!isLoading && !error && (
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Name</th>
                                    <th>Owner</th>
                                    <th>Visibility</th>
                                    <th>Versions</th>
                                    <th>Updated</th>
                                    <th style={{ width: '60px' }}></th>
                                </tr>
                            </thead>
                            <tbody>
                                {filtered.map((workflow) => (
                                    <WorkflowRow
                                        key={workflow.workflowId}
                                        workflow={workflow}
                                    />
                                ))}
                                {filtered.length === 0 && (
                                    <tr>
                                        <td colSpan={6}>
                                            <div className="empty-state">
                                                <div className="empty-state-title">
                                                    {search
                                                        ? 'No matching workflows'
                                                        : 'No workflows yet'}
                                                </div>
                                                <p>
                                                    {search
                                                        ? 'Try adjusting your search criteria'
                                                        : 'Deploy a workflow to get started'}
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

function StatCard({
    label,
    value,
    color,
}: {
    label: string;
    value: number;
    color?: string;
}) {
    return (
        <div className="stat-card">
            <div className="stat-label">{label}</div>
            <div className="stat-value" style={color ? { color } : undefined}>
                {value}
            </div>
        </div>
    );
}

function WorkflowRow({ workflow }: { workflow: Workflow }) {
    return (
        <tr>
            <td>
                <Link
                    to={`/workflow/${workflow.workflowId}`}
                    className="link"
                    style={{ fontSize: '13px' }}
                >
                    {workflow.name || workflow.workflowId}
                </Link>
            </td>
            <td className="text-muted text-sm">{workflow.owner}</td>
            <td>
                <span
                    className={`status-badge ${workflow.visibility === 'Public' ? 'success' : 'default'}`}
                >
                    {workflow.visibility}
                </span>
            </td>
            <td className="text-sm">{workflow.versionCount ?? 1}</td>
            <td
                className="text-muted text-sm"
                title={new Date(workflow.updatedAt).toLocaleString()}
            >
                {timeAgo(workflow.updatedAt)}
            </td>
            <td>
                <Link to={`/workflow/${workflow.workflowId}`}>
                    <Button size="small" variant="secondary">
                        View
                    </Button>
                </Link>
            </td>
        </tr>
    );
}
