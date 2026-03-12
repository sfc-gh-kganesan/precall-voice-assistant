import { AppShell, Container, NavLink, Text, Title } from '@mantine/core';
import { useState } from 'react';
import { SlackLink } from './pages/SlackLink';

function App() {
    const path = window.location.pathname;
    const [activeSection, setActiveSection] = useState('studio');

    if (path === '/auth/slack-link') {
        return <SlackLink />;
    }

    return (
        <AppShell
            header={{ height: 60 }}
            navbar={{ width: 200, breakpoint: 'sm' }}
            padding="md"
        >
            <AppShell.Header>
                <Container
                    h="100%"
                    px="md"
                    style={{ display: 'flex', alignItems: 'center' }}
                    strategy="grid"
                >
                    <Title order={1} fw={700}>
                        p67
                    </Title>
                </Container>
            </AppShell.Header>

            <AppShell.Navbar p="md">
                <NavLink
                    label="Studio"
                    active={activeSection === 'studio'}
                    onClick={() => setActiveSection('studio')}
                />
                <NavLink
                    label="Test"
                    active={activeSection === 'test'}
                    onClick={() => setActiveSection('test')}
                />
                <NavLink
                    label="Deploy"
                    active={activeSection === 'deploy'}
                    onClick={() => setActiveSection('deploy')}
                />
            </AppShell.Navbar>

            <AppShell.Main>
                <Container>
                    <Text size="lg" mb="md">
                        Agent Builder -{' '}
                        {activeSection.charAt(0).toUpperCase() +
                            activeSection.slice(1)}
                    </Text>
                </Container>
            </AppShell.Main>
        </AppShell>
    );
}

export default App;
