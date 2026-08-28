import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from '@/store/auth';
import Layout from '@/components/Layout';
import Login from '@/pages/Login';
import Dashboard from '@/pages/Dashboard';
import Markets from '@/pages/Markets';
import TradeHistory from '@/pages/TradeHistory';
import AIEngine from '@/pages/AIEngine';
import Settings from '@/pages/Settings';
import Users from '@/pages/Users';
import Screener from '@/pages/Screener';
import MLModels from '@/pages/MLModels';
import Reports from '@/pages/Reports';
import Alerts from '@/pages/Alerts';
import Backtest from '@/pages/Backtest';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);
  return token ? <>{children}</> : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="markets"   element={<Markets />} />
        <Route path="history"   element={<TradeHistory />} />
        <Route path="ai-engine" element={<AIEngine />} />
        <Route path="backtest"  element={<Backtest />} />
        <Route path="screener"  element={<Screener />} />
        <Route path="models"    element={<MLModels />} />
        <Route path="reports"   element={<Reports />} />
        <Route path="alerts"    element={<Alerts />} />
        <Route path="settings"  element={<Settings />} />
        <Route path="users"     element={<Users />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
