import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/auth';
import {
  LayoutDashboard, TrendingUp, Clock, Brain,
  Settings, Users, LogOut, Zap, Shield,
} from 'lucide-react';
import clsx from 'clsx';
import TickerTape from '@/components/TickerTape';
import LiveClock from '@/components/LiveClock';

const navSections = [
  {
    label: 'Main',
    items: [
      { to: '/', label: 'Dashboard', icon: LayoutDashboard, exact: true },
      { to: '/markets', label: 'Markets', icon: TrendingUp, badge: '5' },
      { to: '/ai-engine', label: 'AI Engine', icon: Brain },
      { to: '/history', label: 'Trade History', icon: Clock },
    ],
  },
  {
    label: 'Analytics',
    items: [
      { to: '/backtest', label: 'Stock Screener', icon: Settings },
      { to: '/models',   label: 'ML Models',      icon: Brain, badge: '3', badgeGold: true },
      { to: '/reports',  label: 'Reports',        icon: TrendingUp },
    ],
  },
  {
    label: 'System',
    items: [
      { to: '/alerts', label: 'Alerts', icon: Users },
      { to: '/users', label: 'Users', icon: Users, adminOnly: true },
      { to: '/settings', label: 'Settings', icon: Settings },
    ],
  },
];

export default function Layout() {
  const { username, role, logout } = useAuthStore();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate('/login');
  }

  return (
    <div className="min-h-screen bg-bg-primary font-sans">
      {/* Ticker tape */}
      <TickerTape />

      {/* Sidebar */}
      <aside className="fixed top-[34px] left-0 w-[240px] h-[calc(100vh-34px)] bg-[rgba(6,11,20,0.97)] border-r border-[var(--border)] flex flex-col z-50 backdrop-blur-xl">
        {/* Logo */}
        <div className="p-5 border-b border-[var(--border)]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-blue to-blue-600 flex items-center justify-center shadow-[0_0_20px_rgba(0,212,255,0.4)]">
              <Zap size={18} className="text-white" />
            </div>
            <div>
              <div className="text-xl font-black gradient-text tracking-widest">AI Z</div>
              <div className="text-[9px] text-text-muted tracking-[2px] uppercase">Trading Engine</div>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
          {navSections.map((section) => (
            <div key={section.label}>
              <div className="text-[9px] tracking-[2px] uppercase text-text-muted px-2 py-3">{section.label}</div>
              {section.items
                .filter((item) => !(item as any).adminOnly || role === 'admin')
                .map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={(item as any).exact}
                    className={({ isActive }) =>
                      clsx(
                        'flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-[13px] font-medium transition-all',
                        isActive
                          ? 'bg-brand-blue/10 text-brand-blue border border-brand-blue/20'
                          : 'text-text-secondary hover:bg-brand-blue/5 hover:text-text-primary'
                      )
                    }
                  >
                    <item.icon size={15} />
                    <span className="flex-1">{item.label}</span>
                    {(item as any).badge && (
                      <span className={clsx('text-[9px] px-1.5 py-0.5 rounded-full font-bold',
                        (item as any).badgeGold ? 'bg-brand-gold/20 text-brand-gold' : 'bg-brand-blue text-black'
                      )}>{(item as any).badge}</span>
                    )}
                  </NavLink>
                ))}
            </div>
          ))}
        </nav>

        {/* Bot status */}
        <div className="m-3 p-3 rounded-xl bg-gradient-to-br from-brand-green/8 to-brand-blue/5 border border-brand-green/20">
          <div className="text-[9px] uppercase tracking-[1.5px] text-text-muted mb-2">Bot Status</div>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-brand-green font-semibold text-[13px]">
              <div className="pulse-dot" />
              LIVE
            </div>
            <Shield size={14} className="text-text-muted" />
          </div>
          <div className="text-[10px] text-text-muted mt-1.5">Mode: <span className="text-brand-gold font-semibold">Paper Trading</span></div>
        </div>

        {/* User */}
        <div className="p-3 border-t border-[var(--border)]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-brand-blue to-purple-600 flex items-center justify-center text-xs font-bold">
              {username?.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[12px] font-semibold truncate">{username}</div>
              <div className="text-[10px] text-brand-gold capitalize">{role}</div>
            </div>
            <button onClick={handleLogout} className="text-text-muted hover:text-brand-red transition-colors p-1">
              <LogOut size={14} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="ml-[240px] mt-[34px] min-h-[calc(100vh-34px)] p-5">
        <div className="flex items-center justify-end gap-3 mb-5">
          <LiveClock />
        </div>
        <Outlet />
      </main>
    </div>
  );
}
