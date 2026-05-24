import { Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout.jsx';
import ProtectedRoute from './components/ProtectedRoute.jsx';
import AdminToolsPage from './pages/AdminToolsPage.jsx';
import AuditLogsPage from './pages/AuditLogsPage.jsx';
import CreateShipmentPage from './pages/CreateShipmentPage.jsx';
import DashboardPage from './pages/DashboardPage.jsx';
import EmailAutomationPage from './pages/EmailAutomationPage.jsx';
import LoginPage from './pages/LoginPage.jsx';
import MockAiPage from './pages/MockAiPage.jsx';
import PartiesPage from './pages/PartiesPage.jsx';
import ReportsPage from './pages/ReportsPage.jsx';
import SettingsPage from './pages/SettingsPage.jsx';
import ShipmentDetailPage from './pages/ShipmentDetailPage.jsx';
import ShipmentsPage from './pages/ShipmentsPage.jsx';
import StatusPage from './pages/StatusPage.jsx';
import TasksPage from './pages/TasksPage.jsx';
import UsersAdminPage from './pages/UsersAdminPage.jsx';

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="shipments" element={<ShipmentsPage />} />
        <Route path="shipments/new" element={<CreateShipmentPage />} />
        <Route path="shipments/:id" element={<ShipmentDetailPage />} />
        <Route path="parties" element={<PartiesPage />} />
        <Route path="tasks" element={<TasksPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="ai" element={<MockAiPage />} />
        <Route path="email" element={<EmailAutomationPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="admin/audit-logs" element={<AuditLogsPage />} />
        <Route path="admin/users" element={<UsersAdminPage />} />
        <Route path="admin/status" element={<StatusPage />} />
        <Route path="admin/tools" element={<AdminToolsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
