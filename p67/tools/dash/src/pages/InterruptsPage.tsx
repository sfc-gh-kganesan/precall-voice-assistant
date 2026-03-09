import { Button, StatusBadge, TextArea } from '@snowflake/stellar-components';
import { useState } from 'react';
import type { Interrupt } from '@/api/types';
import { AppShell } from '@/components/AppShell';
import { useInterrupts, useResumeInterrupt } from '@/hooks/useInterrupts';

export function InterruptsPage() {
    const { data, isLoading, error } = useInterrupts({ status: 'Pending' });

    return (
        <AppShell>
            <div
                style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '24px',
                }}
            >
                <h2 style={{ fontSize: '24px', fontWeight: 600 }}>
                    Pending Interrupts
                </h2>
                <p style={{ color: 'var(--color-text-secondary)' }}>
                    Human-in-the-loop requests waiting for your input
                </p>

                {isLoading && <p>Loading interrupts...</p>}
                {error && (
                    <p style={{ color: 'red' }}>
                        Error: {(error as Error).message}
                    </p>
                )}

                {!isLoading && !error && data && (
                    <div
                        style={{
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '16px',
                        }}
                    >
                        {data.interrupts.map((interrupt) => (
                            <InterruptCard
                                key={interrupt.id}
                                interrupt={interrupt}
                            />
                        ))}
                        {data.interrupts.length === 0 && (
                            <p style={{ color: 'var(--color-text-secondary)' }}>
                                No pending interrupts
                            </p>
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
            // Use string if not valid JSON
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
        <div
            style={{
                border: '1px solid var(--color-border)',
                borderRadius: '8px',
                padding: '16px',
                backgroundColor: 'var(--color-surface)',
            }}
        >
            <div
                style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                }}
            >
                <div>
                    <div
                        style={{
                            display: 'flex',
                            gap: '8px',
                            alignItems: 'center',
                        }}
                    >
                        <StatusBadge variant={statusVariants[interrupt.status]}>
                            {interrupt.status}
                        </StatusBadge>
                        <span
                            style={{
                                fontFamily: 'monospace',
                                fontSize: '14px',
                            }}
                        >
                            {interrupt.id.slice(0, 8)}...
                        </span>
                    </div>
                    <p
                        style={{
                            color: 'var(--color-text-secondary)',
                            marginTop: '4px',
                            fontSize: '14px',
                        }}
                    >
                        Workflow: {interrupt.workflowId.slice(0, 8)}... •
                        Created:{' '}
                        {new Date(interrupt.createdAt).toLocaleString()}
                        {interrupt.nodeId && ` • Node: ${interrupt.nodeId}`}
                    </p>
                </div>
                <Button
                    size="small"
                    variant="tertiary"
                    onClick={() => setExpanded(!expanded)}
                >
                    {expanded ? 'Collapse' : 'Expand'}
                </Button>
            </div>

            {expanded && (
                <div style={{ marginTop: '16px' }}>
                    <h4 style={{ fontWeight: 600, marginBottom: '8px' }}>
                        Payload
                    </h4>
                    <pre
                        style={{
                            backgroundColor: 'var(--color-surface-secondary)',
                            padding: '12px',
                            borderRadius: '4px',
                            fontSize: '13px',
                            overflow: 'auto',
                            maxHeight: '200px',
                        }}
                    >
                        {JSON.stringify(interrupt.payload, null, 2)}
                    </pre>

                    {interrupt.status === 'Pending' && (
                        <div style={{ marginTop: '16px' }}>
                            <h4
                                style={{ fontWeight: 600, marginBottom: '8px' }}
                            >
                                Response
                            </h4>
                            <TextArea
                                placeholder="Enter your response (JSON or plain text)"
                                value={response}
                                onChange={(e) => setResponse(e.target.value)}
                                style={{
                                    width: '100%',
                                    minHeight: '100px',
                                    marginBottom: '8px',
                                }}
                            />
                            <Button
                                onClick={handleResume}
                                disabled={
                                    resumeInterrupt.isPending ||
                                    !response.trim()
                                }
                            >
                                {resumeInterrupt.isPending
                                    ? 'Resuming...'
                                    : 'Resume Workflow'}
                            </Button>
                        </div>
                    )}

                    {interrupt.response != null && (
                        <div style={{ marginTop: '16px' }}>
                            <h4
                                style={{ fontWeight: 600, marginBottom: '8px' }}
                            >
                                Previous Response
                            </h4>
                            <pre
                                style={{
                                    backgroundColor:
                                        'var(--color-surface-secondary)',
                                    padding: '12px',
                                    borderRadius: '4px',
                                    fontSize: '13px',
                                }}
                            >
                                {JSON.stringify(interrupt.response, null, 2)}
                            </pre>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
