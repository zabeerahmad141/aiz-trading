import { useQuery } from '@tanstack/react-query';
import { Bell, CircleCheck, CircleAlert } from 'lucide-react';
import { getApiStatus, getBotStatus, getOpenPositions } from '@/lib/api';

export default function Alerts() {
  const { data: api } = useQuery({ queryKey: ['api-status'], queryFn: () => getApiStatus().then(r => r.data), refetchInterval: 30000 });
  const { data: bot } = useQuery({ queryKey: ['botStatus'], queryFn: () => getBotStatus().then(r => r.data), refetchInterval: 10000 });
  const { data: positions = [] } = useQuery({ queryKey: ['positions'], queryFn: () => getOpenPositions().then(r => r.data), refetchInterval: 10000 });
  const alerts = [
    { ok: api?.api === 'connected', title: 'Backend connection', detail: api?.api === 'connected' ? 'API is responding normally.' : 'Backend status is unavailable.' },
    { ok: !bot?.market_open, title: 'Market session', detail: bot?.market_open ? 'NSE session is open.' : 'NSE is closed. New orders are paused.' },
    { ok: positions.length === 0, title: 'Open positions', detail: positions.length ? `${positions.length} position(s) require monitoring.` : 'No open positions require monitoring.' },
  ];
  return <div className="space-y-4 animate-[fade-in_0.3s_ease]"><div><h1 className="text-xl font-bold">Alerts</h1><p className="text-xs text-text-muted mt-1">Live system and risk conditions</p></div><div className="glass-card divide-y divide-white/[0.04]">{alerts.map(alert => <div key={alert.title} className="p-4 flex items-start gap-3"><span className={alert.ok ? 'text-brand-green' : 'text-brand-gold'}>{alert.ok ? <CircleCheck size={18} /> : <CircleAlert size={18} />}</span><div><div className="font-semibold text-sm">{alert.title}</div><div className="text-xs text-text-muted mt-1">{alert.detail}</div></div></div>)}</div><div className="glass-card p-6 flex gap-3 border-brand-blue/20"><Bell size={18} className="text-brand-blue" /><p className="text-sm text-text-secondary">Trade alerts will be generated from real signals and risk events. This page does not invent notifications when no event has occurred.</p></div></div>;
}
