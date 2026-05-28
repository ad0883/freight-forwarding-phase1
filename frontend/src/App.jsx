import { Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout.jsx';
import ProtectedRoute from './components/ProtectedRoute.jsx';
import AdminToolsPage from './pages/AdminToolsPage.jsx';
import AuditLogsPage from './pages/AuditLogsPage.jsx';
import CreateShipmentPage from './pages/CreateShipmentPage.jsx';
import DashboardPage from './pages/DashboardPage.jsx';
import EmailAutomationPage from './pages/EmailAutomationPage.jsx';
import EventsPage from './pages/EventsPage.jsx';
import FinancePage from './pages/FinancePage.jsx';
import LoginPage from './pages/LoginPage.jsx';
import MockAiPage from './pages/MockAiPage.jsx';
import NotificationsPage from './pages/NotificationsPage.jsx';
import PartiesPage from './pages/PartiesPage.jsx';
import ReportsPage from './pages/ReportsPage.jsx';
import RulesPage from './pages/RulesPage.jsx';
import SettingsPage from './pages/SettingsPage.jsx';
import ShipmentDetailPage from './pages/ShipmentDetailPage.jsx';
import ShipmentsPage from './pages/ShipmentsPage.jsx';
import StatusPage from './pages/StatusPage.jsx';
import TasksPage from './pages/TasksPage.jsx';
import UsersAdminPage from './pages/UsersAdminPage.jsx';
import ValidationIssuesPage from './pages/ValidationIssuesPage.jsx';
import ManualReviewPage from './pages/ManualReviewPage.jsx';
import ApprovalsPage from './pages/ApprovalsPage.jsx';
import BotGovernancePage from './pages/BotGovernancePage.jsx';
import PortalPage from './pages/PortalPage.jsx';
import CustomsPage from './pages/CustomsPage.jsx';
import TransportPage from './pages/TransportPage.jsx';
import TrackingPage from './pages/TrackingPage.jsx';

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
        <Route
          path="shipments/new"
          element={
            <ProtectedRoute allowedRoles={['ADMIN', 'STAFF']}>
              <CreateShipmentPage />
            </ProtectedRoute>
          }
        />
        <Route path="shipments/:id" element={<ShipmentDetailPage />} />
        <Route path="parties" element={<PartiesPage />} />
        <Route path="tasks" element={<TasksPage />} />
        <Route path="notifications" element={<NotificationsPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="finance" element={<FinancePage />} />
        <Route path="ai" element={<MockAiPage />} />
        <Route
          path="email"
          element={
            <ProtectedRoute allowedRoles={['ADMIN', 'STAFF']}>
              <EmailAutomationPage />
            </ProtectedRoute>
          }
        />
        <Route path="settings" element={<SettingsPage />} />
        <Route
          path="audit-logs"
          element={
            <ProtectedRoute allowedRoles={['ADMIN']}>
              <AuditLogsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="users"
          element={
            <ProtectedRoute allowedRoles={['ADMIN']}>
              <UsersAdminPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="status"
          element={
            <ProtectedRoute allowedRoles={['ADMIN']}>
              <StatusPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="admin/tools"
          element={
            <ProtectedRoute allowedRoles={['ADMIN']}>
              <AdminToolsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="events"
          element={
            <ProtectedRoute allowedRoles={['ADMIN', 'STAFF']}>
              <EventsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="validation-issues"
          element={
            <ProtectedRoute allowedRoles={['ADMIN', 'STAFF']}>
              <ValidationIssuesPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="rules"
          element={
            <ProtectedRoute allowedRoles={['ADMIN', 'STAFF']}>
              <RulesPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="manual-review"
          element={
            <ProtectedRoute allowedRoles={['ADMIN', 'STAFF', 'VIEW_ONLY']}>
              <ManualReviewPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="approvals"
          element={
            <ProtectedRoute allowedRoles={['ADMIN', 'STAFF', 'VIEW_ONLY']}>
              <ApprovalsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="bot-governance"
          element={
            <ProtectedRoute allowedRoles={['ADMIN', 'STAFF', 'VIEW_ONLY']}>
              <BotGovernancePage />
            </ProtectedRoute>
          }
        />
        <Route path="portal" element={<ProtectedRoute><PortalPage /></ProtectedRoute>} />
        <Route
          path="customs"
          element={
            <ProtectedRoute allowedRoles={['ADMIN', 'STAFF', 'VIEW_ONLY']}>
              <CustomsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="transport"
          element={
            <ProtectedRoute allowedRoles={['ADMIN', 'STAFF', 'VIEW_ONLY']}>
              <TransportPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="tracking"
          element={
            <ProtectedRoute allowedRoles={['ADMIN', 'STAFF', 'VIEW_ONLY']}>
              <TrackingPage />
            </ProtectedRoute>
          }
        />
        <Route path="admin/audit-logs" element={<Navigate to="/audit-logs" replace />} />
        <Route path="admin/users" element={<Navigate to="/users" replace />} />
        <Route path="admin/status" element={<Navigate to="/status" replace />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
