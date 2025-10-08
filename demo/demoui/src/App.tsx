import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './components/Dashboard';
import RealDataDashboard from './components/RealDataDashboard';
import InvoiceProcessor from './components/InvoiceProcessor';
import ExceptionQueue from './components/ExceptionQueue';
import Tasks from './components/Tasks';
import Reports from './components/Reports';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<RealDataDashboard />} />
          <Route path="mock-dashboard" element={<Dashboard />} />
          <Route path="invoice-processor" element={<InvoiceProcessor />} />
          <Route path="exception-queue" element={<ExceptionQueue />} />
          <Route path="tasks" element={<Tasks />} />
          <Route path="reports" element={<Reports />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;