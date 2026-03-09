import { Button, TextInput } from '@snowflake/stellar-components';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import type { Workflow } from '@/api/types';
import { AppShell } from '@/components/AppShell';
import { useWorkflows } from '@/hooks/useWorkflows';

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
                    <div className="stat-card">
                        <div className="stat-label">Total Workflows</div>
                        <div className="stat-value">{workflows.length}</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-label">Public</div>
                        <div className="stat-value">{publicCount}</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-label">Private</div>
                        <div className="stat-value">{privateCount}</div>
                    </div>
                </div>

                <div className="card">
                    <div className="card-header">
                        <span className="card-title">All Workflows</span>
                        <TextInput
                            placeholder="Search..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            style={{ width: '240px' }}
                            aria-label="Search workflows"
                        />
                    </div>

                    {isLoading && (
                        <div className="card-body">
                            <p style={{ color: 'var(--sf-gray-500)' }}>
                                Loading workflows...
                            </p>
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
                                    <th>Last Updated</th>
                                    <th></th>
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
                                                <div className="empty-state-icon">
                                                    📋
                                                </div>
                                                <div className="empty-state-title">
                                                    No workflows found
                                                </div>
                                                <p>
                                                    Try adjusting your search
                                                    criteria
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

function WorkflowRow({ workflow }: { workflow: Workflow }) {
    return (
        <tr>
            <td>
                <Link to={`/workflow/${workflow.workflowId}`} className="link">
                    {workflow.name || workflow.workflowId}
                </Link>
            </td>
            <td style={{ color: 'var(--sf-gray-500)' }}>{workflow.owner}</td>
            <td>
                <span
                    className={`status-badge ${workflow.visibility === 'Public' ? 'success' : 'default'}`}
                >
                    {workflow.visibility}
                </span>
            </td>
            <td>{workflow.versionCount ?? 1}</td>
            <td style={{ color: 'var(--sf-gray-500)' }}>
                {new Date(workflow.updatedAt).toLocaleDateString()}
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
