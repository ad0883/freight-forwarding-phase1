import { Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout.jsx';
import ProtectedRoute from './components/ProtectedRoute.jsx';
import CreateShipmentPage from './pages/CreateShipmentPage.jsx';
import DashboardPage from './pages/DashboardPage.jsx';
import LoginPage from './pages/LoginPage.jsx';
import MockAiPage from './pages/MockAiPage.jsx';
import PartiesPage from './pages/PartiesPage.jsx';
import ShipmentDetailPage from './pages/ShipmentDetailPage.jsx';
import ShipmentsPage from './pages/ShipmentsPage.jsx';
import TasksPage from './pages/TasksPage.jsx';

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
        <Route path="ai" element={<MockAiPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
