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

// Stub pages for nav items (expand these later)
const Stub = ({ title, icon }: { title: string; icon: string }) => (
  <div className="glass-card p-10 text-center text-text-secondary">
    <div className="text-5xl mb-4">{icon}</div>
    <h2 className="text-xl font-bold mb-2">{title}</h2>
    <p className="text-sm text-text-muted">This section is coming soon. Build it out using the patterns in Dashboard.tsx and the docs/MASTER.md guide.</p>
  </div>
);
const Backtest = () => <Stub title="Backtest Engine" icon="🔬" />;
const MLModels = () => <Stub title="ML Models" icon="🧠" />;
const Reports  = () => <Stub title="Reports" icon="📊" />;
const Alerts   = () => <Stub title="Alerts" icon="🔔" />;

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
