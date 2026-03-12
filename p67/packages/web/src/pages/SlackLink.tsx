import { Button, Card, Container, Loader, Text, Title } from '@mantine/core';
import { useEffect, useState } from 'react';

type LinkState = 'loading' | 'success' | 'error';

export function SlackLink() {
    const [state, setState] = useState<LinkState>('loading');
    const [message, setMessage] = useState('');

    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const token = params.get('token');
        const slackUser = params.get('slack_user');
        const slackTeam = params.get('slack_team');

        if (!token || !slackUser || !slackTeam) {
            setState('error');
            setMessage(
                'Missing required parameters. Please run /workflow link again in Slack.',
            );
            return;
        }

        fetch(
            `/api/auth/slack/link?token=${token}&slack_user=${slackUser}&slack_team=${slackTeam}`,
            {
                method: 'POST',
            },
        )
            .then(async (res) => {
                const data = await res.json();
                if (data.success) {
                    setState('success');
                    setMessage(data.message);
                } else {
                    setState('error');
                    setMessage(data.message || 'Failed to link account.');
                }
            })
            .catch((err) => {
                setState('error');
                setMessage(
                    err.message || 'Network error. Is controld running?',
                );
            });
    }, []);

    return (
        <Container size="sm" py="xl">
            <Card shadow="sm" padding="lg" radius="md" withBorder>
                <Title order={2} mb="md">
                    Slack Account Linking
                </Title>
                {state === 'loading' && (
                    <>
                        <Loader size="sm" />
                        <Text mt="sm">Linking your Slack account...</Text>
                    </>
                )}
                {state === 'success' && (
                    <>
                        <Text c="green" fw={600} size="lg">
                            {message}
                        </Text>
                        <Text mt="sm" c="dimmed">
                            You can close this tab and return to Slack.
                        </Text>
                    </>
                )}
                {state === 'error' && (
                    <>
                        <Text c="red" fw={600} size="lg">
                            {message}
                        </Text>
                        <Button
                            mt="md"
                            variant="outline"
                            onClick={() => window.close()}
                        >
                            Close
                        </Button>
                    </>
                )}
            </Card>
        </Container>
    );
}
