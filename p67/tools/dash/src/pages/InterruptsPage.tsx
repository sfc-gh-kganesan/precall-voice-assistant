import { Button, StatusBadge, TextArea } from '@snowflake/stellar-components';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import type { Interrupt } from '@/api/types';
import { AppShell } from '@/components/AppShell';
import { useInterrupts, useResumeInterrupt } from '@/hooks/useInterrupts';
import { timeAgo } from '@/utils/time';

export function InterruptsPage() {
    const [filter, setFilter] = useState<string>('Pending');
    const { data, isLoading, error } = useInterrupts({ status: filter });

    const filters = ['Pending', 'Resumed', 'Expired'];

    const count = data?.total ?? 0;

    return (
        <AppShell>
            <div className="page-container">
                <div className="page-header">
                    <h1 className="page-title">Interrupts</h1>
                    <p className="page-subtitle">
                        Human-in-the-loop requests waiting for your input
                    </p>
                </div>

                <div className="filter-bar">
                    {filters.map((f) => (
                        <button
                            type="button"
                            key={f}
                            className={`filter-chip ${filter === f ? 'active' : ''}`}
                            onClick={() => setFilter(f)}
                        >
                            {f}
                            {filter === f && count > 0 && (
                                <span
                                    style={{
                                        marginLeft: '6px',
                                        fontSize: '11px',
                                        fontWeight: 700,
                                        background: 'var(--sf-blue-600)',
                                        color: '#fff',
                                        borderRadius: '10px',
                                        padding: '0 6px',
                                        minWidth: '18px',
                                        display: 'inline-flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                    }}
                                >
                                    {count}
                                </span>
                            )}
                        </button>
                    ))}
                </div>

                {isLoading && (
                    <div className="card">
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
                                Loading interrupts...
                            </div>
                        </div>
                    </div>
                )}

                {error && (
                    <div className="card">
                        <div className="card-body">
                            <p style={{ color: 'var(--sf-red-500)' }}>
                                Error: {(error as Error).message}
                            </p>
                        </div>
                    </div>
                )}

                {!isLoading && !error && data && (
                    <div
                        style={{
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '12px',
                        }}
                    >
                        {data.interrupts.map((interrupt) => (
                            <InterruptCard
                                key={interrupt.id}
                                interrupt={interrupt}
                            />
                        ))}
                        {data.interrupts.length === 0 && (
                            <div className="card">
                                <div className="card-body">
                                    <div className="empty-state">
                                        <div className="empty-state-title">
                                            No {filter.toLowerCase()} interrupts
                                        </div>
                                        <p>
                                            {filter === 'Pending'
                                                ? 'All caught up - no workflows are waiting for input'
                                                : `No interrupts with status "${filter}"`}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </AppShell>
    );
}

function InterruptCard({ interrupt }: { interrupt: Interrupt }) {
    const [response, setResponse] = useState('');
    const [expanded, setExpanded] = useState(false);
    const resumeInterrupt = useResumeInterrupt();

    const handleResume = async () => {
        let parsedResponse: unknown = response;
        try {
            parsedResponse = JSON.parse(response);
        } catch {
            // string fallback
        }
        await resumeInterrupt.mutateAsync({
            interruptId: interrupt.id,
            response: parsedResponse,
        });
        setResponse('');
    };

    const statusVariants: Record<string, 'caution' | 'success' | 'critical'> = {
        Pending: 'caution',
        Resumed: 'success',
        Expired: 'critical',
    };

    return (
        <div className="interrupt-card">
            <button
                type="button"
                className="interrupt-header"
                onClick={() => setExpanded(!expanded)}
            >
                <div
                    style={{
                        display: 'flex',
                        gap: '12px',
                        alignItems: 'center',
                        minWidth: 0,
                    }}
                >
                    <StatusBadge variant={statusVariants[interrupt.status]}>
                        {interrupt.status}
                    </StatusBadge>
                    <span
                        style={{
                            fontFamily: 'monospace',
                            fontSize: '12px',
                            color: 'var(--sf-gray-600)',
                        }}
                    >
                        {interrupt.id.slice(0, 8)}
                    </span>
                    {interrupt.nodeId && (
                        <span className="duration-badge">
                            {interrupt.nodeId}
                        </span>
                    )}
                    <span
                        className="text-muted text-xs"
                        style={{
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                        }}
                    >
                        {interrupt.workflowId.slice(0, 12)}...
                    </span>
                    <Link
                        to={`/workflow/${interrupt.workflowId}/run/${interrupt.runId}`}
                        onClick={(e) => e.stopPropagation()}
                        title="View run details"
                        style={{
                            fontSize: '11px',
                            fontFamily: 'monospace',
                            color: 'var(--sf-blue-600)',
                            textDecoration: 'none',
                            whiteSpace: 'nowrap',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '3px',
                        }}
                    >
                        <svg
                            aria-hidden="true"
                            width="12"
                            height="12"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                        >
                            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                        </svg>
                        {interrupt.runId.slice(0, 8)}
                    </Link>
                </div>
                <div
                    style={{
                        display: 'flex',
                        gap: '8px',
                        alignItems: 'center',
                        flexShrink: 0,
                    }}
                >
                    <span
                        className="text-muted text-xs"
                        title={new Date(interrupt.createdAt).toLocaleString()}
                    >
                        {timeAgo(interrupt.createdAt)}
                    </span>
                    <svg
                        aria-hidden="true"
                        width="16"
                        height="16"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="var(--sf-gray-400)"
                        strokeWidth="2"
                        style={{
                            transition: 'transform 150ms ease',
                            transform: expanded
                                ? 'rotate(180deg)'
                                : 'rotate(0)',
                        }}
                    >
                        <polyline points="6 9 12 15 18 9" />
                    </svg>
                </div>
            </button>

            {expanded && (
                <div className="interrupt-body">
                    <div style={{ marginTop: '16px' }}>
                        <p className="form-label">Payload</p>
                        <pre className="code-block">
                            {JSON.stringify(interrupt.payload, null, 2)}
                        </pre>

                        {interrupt.status === 'Pending' && (
                            <div style={{ marginTop: '16px' }}>
                                <p className="form-label">Response</p>
                                <TextArea
                                    aria-label="Interrupt response"
                                    placeholder="Enter your response (JSON or plain text)"
                                    value={response}
                                    onChange={(e) =>
                                        setResponse(e.target.value)
                                    }
                                    style={{
                                        width: '100%',
                                        minHeight: '80px',
                                        marginBottom: '12px',
                                    }}
                                />
                                <Button
                                    onClick={handleResume}
                                    disabled={
                                        resumeInterrupt.isPending ||
                                        !response.trim()
                                    }
                                >
                                    {resumeInterrupt.isPending ? (
                                        <span
                                            style={{
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '6px',
                                            }}
                                        >
                                            <span className="spinner" />
                                            Resuming...
                                        </span>
                                    ) : (
                                        'Resume Workflow'
                                    )}
                                </Button>
                            </div>
                        )}

                        {interrupt.response != null && (
                            <div style={{ marginTop: '16px' }}>
                                <p className="form-label">Previous Response</p>
                                <pre className="code-block">
                                    {JSON.stringify(
                                        interrupt.response,
                                        null,
                                        2,
                                    )}
                                </pre>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
