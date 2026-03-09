import { Route, Routes } from 'react-router-dom';
import { BaltoThemeWrapper } from './components/BaltoThemeWrapper';
import { InterruptsPage } from './pages/InterruptsPage';
import { RunDetailPage } from './pages/RunDetailPage';
import { WorkflowDetailPage } from './pages/WorkflowDetailPage';
import { WorkflowsPage } from './pages/WorkflowsPage';

export default function App() {
    return (
        <BaltoThemeWrapper>
            <Routes>
                <Route path="/" element={<WorkflowsPage />} />
                <Route
                    path="/workflow/:workflowId"
                    element={<WorkflowDetailPage />}
                />
                <Route
                    path="/workflow/:workflowId/run/:runId"
                    element={<RunDetailPage />}
                />
                <Route path="/interrupts" element={<InterruptsPage />} />
            </Routes>
        </BaltoThemeWrapper>
    );
}
