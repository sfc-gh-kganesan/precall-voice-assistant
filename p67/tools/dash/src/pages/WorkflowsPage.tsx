import { Button, TextInput } from '@snowflake/stellar-components';
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import type { Workflow } from '@/api/types';
import { AppShell } from '@/components/AppShell';
import { SortableHeader } from '@/components/SortableHeader';
import { useSort } from '@/hooks/useSort';
import { useWorkflows } from '@/hooks/useWorkflows';
import { timeAgo } from '@/utils/time';

export function WorkflowsPage() {
    const { data, isLoading, error } = useWorkflows();
    const [search, setSearch] = useState('');
    const [ownerFilter, setOwnerFilter] = useState<string | null>(null);
    const [visibilityFilter, setVisibilityFilter] = useState<
        'Public' | 'Private' | null
    >(null);
    const { sortKey, sortDir, onSort, sortData } = useSort<Workflow>(
        'updatedAt',
        'desc',
    );

    const workflows = data?.workflows ?? [];

    const uniqueOwners = useMemo(
        () => Array.from(new Set(workflows.map((w) => w.owner))).sort(),
        [workflows],
    );

    const filtered = useMemo(() => {
        const base = workflows.filter((w) => {
            const matchesSearch =
                !search ||
                w.name?.toLowerCase().includes(search.toLowerCase()) ||
                w.owner.toLowerCase().includes(search.toLowerCase()) ||
                w.workflowId.toLowerCase().includes(search.toLowerCase());
            const matchesOwner = !ownerFilter || w.owner === ownerFilter;
            const matchesVisibility =
                !visibilityFilter || w.visibility === visibilityFilter;
            return matchesSearch && matchesOwner && matchesVisibility;
        });
        return sortData(base);
    }, [workflows, search, ownerFilter, visibilityFilter, sortData]);

    const publicCount = workflows.filter(
        (w) => w.visibility === 'Public',
    ).length;
    const privateCount = workflows.filter(
        (w) => w.visibility === 'Private',
    ).length;

    const handleVisibilityCardClick = (v: 'Public' | 'Private') => {
        setVisibilityFilter((prev) => (prev === v ? null : v));
    };

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
                        onClick={() => {
                            setOwnerFilter(null);
                            setVisibilityFilter(null);
                        }}
                    />
                    <StatCard
                        label="Public"
                        value={publicCount}
                        color="var(--sf-green-500)"
                        onClick={() => handleVisibilityCardClick('Public')}
                    />
                    <StatCard
                        label="Private"
                        value={privateCount}
                        onClick={() => handleVisibilityCardClick('Private')}
                    />
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

                    <div
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '12px',
                            padding: '8px 20px',
                            borderBottom: '1px solid var(--sf-gray-100)',
                        }}
                    >
                        <select
                            value={ownerFilter ?? ''}
                            onChange={(e) =>
                                setOwnerFilter(e.target.value || null)
                            }
                            style={{
                                fontSize: '12px',
                                padding: '4px 8px',
                                borderRadius: '4px',
                                border: '1px solid var(--sf-gray-200)',
                                background: 'var(--sf-surface)',
                                color: 'var(--sf-gray-700)',
                                cursor: 'pointer',
                            }}
                            aria-label="Filter by owner"
                        >
                            <option value="">All Owners</option>
                            {uniqueOwners.map((owner) => (
                                <option key={owner} value={owner}>
                                    {owner}
                                </option>
                            ))}
                        </select>

                        <div style={{ display: 'flex', gap: '4px' }}>
                            {(['All', 'Public', 'Private'] as const).map(
                                (v) => {
                                    const filterVal = v === 'All' ? null : v;
                                    const isActive =
                                        visibilityFilter === filterVal;
                                    return (
                                        <button
                                            key={v}
                                            type="button"
                                            onClick={() =>
                                                setVisibilityFilter(filterVal)
                                            }
                                            style={{
                                                padding: '4px 10px',
                                                fontSize: '12px',
                                                fontWeight: isActive
                                                    ? 700
                                                    : 500,
                                                borderRadius: '4px',
                                                border: isActive
                                                    ? '1px solid var(--sf-blue-600)'
                                                    : '1px solid var(--sf-gray-200)',
                                                background: isActive
                                                    ? 'var(--sf-blue-50, rgba(37,99,235,0.08))'
                                                    : 'none',
                                                color: isActive
                                                    ? 'var(--sf-blue-600)'
                                                    : 'var(--sf-gray-600)',
                                                cursor: 'pointer',
                                                fontFamily: 'inherit',
                                            }}
                                        >
                                            {v}
                                        </button>
                                    );
                                },
                            )}
                        </div>
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
                                    <SortableHeader
                                        label="Name"
                                        sortKey="name"
                                        currentSort={sortKey as string}
                                        currentDir={sortDir}
                                        onSort={(k) =>
                                            onSort(k as keyof Workflow)
                                        }
                                    />
                                    <SortableHeader
                                        label="Owner"
                                        sortKey="owner"
                                        currentSort={sortKey as string}
                                        currentDir={sortDir}
                                        onSort={(k) =>
                                            onSort(k as keyof Workflow)
                                        }
                                    />
                                    <SortableHeader
                                        label="Visibility"
                                        sortKey="visibility"
                                        currentSort={sortKey as string}
                                        currentDir={sortDir}
                                        onSort={(k) =>
                                            onSort(k as keyof Workflow)
                                        }
                                    />
                                    <SortableHeader
                                        label="Versions"
                                        sortKey="versionCount"
                                        currentSort={sortKey as string}
                                        currentDir={sortDir}
                                        onSort={(k) =>
                                            onSort(k as keyof Workflow)
                                        }
                                    />
                                    <SortableHeader
                                        label="Updated"
                                        sortKey="updatedAt"
                                        currentSort={sortKey as string}
                                        currentDir={sortDir}
                                        onSort={(k) =>
                                            onSort(k as keyof Workflow)
                                        }
                                    />
                                    <th style={{ width: '60px' }}></th>
                                </tr>
                            </thead>
                            <tbody>
                                {filtered.map((workflow) => (
                                    <WorkflowRow
                                        key={workflow.workflowId}
                                        workflow={workflow}
                                        onVisibilityClick={(v) =>
                                            setVisibilityFilter((prev) =>
                                                prev === v ? null : v,
                                            )
                                        }
                                    />
                                ))}
                                {filtered.length === 0 && (
                                    <tr>
                                        <td colSpan={6}>
                                            <div className="empty-state">
                                                <div className="empty-state-title">
                                                    {search ||
                                                    ownerFilter ||
                                                    visibilityFilter
                                                        ? 'No matching workflows'
                                                        : 'No workflows yet'}
                                                </div>
                                                <p>
                                                    {search ||
                                                    ownerFilter ||
                                                    visibilityFilter
                                                        ? 'Try adjusting your search or filters'
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
    onClick,
}: {
    label: string;
    value: number;
    color?: string;
    onClick?: () => void;
}) {
    const Tag = onClick ? 'button' : 'div';
    return (
        <Tag
            type={onClick ? 'button' : undefined}
            className="stat-card"
            onClick={onClick}
            style={{
                cursor: onClick ? 'pointer' : undefined,
                transition: 'filter 150ms ease',
                font: 'inherit',
                textAlign: 'left',
                color: 'inherit',
            }}
            onMouseEnter={(e) => {
                if (onClick)
                    (e.currentTarget as HTMLElement).style.filter =
                        'brightness(0.95)';
            }}
            onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.filter = '';
            }}
        >
            <div className="stat-label">{label}</div>
            <div className="stat-value" style={color ? { color } : undefined}>
                {value}
            </div>
        </Tag>
    );
}

function WorkflowRow({
    workflow,
    onVisibilityClick,
}: {
    workflow: Workflow;
    onVisibilityClick: (v: 'Public' | 'Private') => void;
}) {
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
                <button
                    type="button"
                    className={`status-badge ${workflow.visibility === 'Public' ? 'success' : 'default'}`}
                    onClick={() => onVisibilityClick(workflow.visibility)}
                    style={{
                        cursor: 'pointer',
                        background: 'none',
                        border: 'none',
                        padding: 0,
                        font: 'inherit',
                    }}
                >
                    {workflow.visibility}
                </button>
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
