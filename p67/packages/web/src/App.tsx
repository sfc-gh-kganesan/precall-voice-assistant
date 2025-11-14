import { SingleLine, Heading, Paragraph, Layout } from '@snowflake/stellar-components';
import { AgentIcon } from '@snowflake/stellar-icons';

function App() {
    return (
        <Layout.Root style={{ margin: 100 }}>
            <Layout.Header>
                <SingleLine bold>
                    <Heading size='pageHeader'><AgentIcon /> p67</Heading>
                </SingleLine>
            </Layout.Header>
            <Layout.Content>
                <Paragraph>Agent Builder</Paragraph>
            </Layout.Content>
        </Layout.Root>
    );
}

export default App;
