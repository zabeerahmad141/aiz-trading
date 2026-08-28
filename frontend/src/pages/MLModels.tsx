import { useQuery } from '@tanstack/react-query';
import { Brain, Activity, Database, ShieldCheck } from 'lucide-react';
import { getApiStatus, getBotStatus } from '@/lib/api';

export default function MLModels() {
  const { data: apiStatus } = useQuery({ queryKey: ['api-status'], queryFn: () => getApiStatus().then(r => r.data), refetchInterval: 30000 });
  const { data: bot } = useQuery({ queryKey: ['botStatus'], queryFn: () => getBotStatus().then(r => r.data), refetchInterval: 10000 });
  const marketOpen = Boolean(bot?.market_open);
  const rows = [
    ['Runtime', apiStatus?.api === 'connected' ? 'Connected' : 'Unavailable', Activity],
    ['Trading mode', bot?.mode || 'Unknown', ShieldCheck],
    ['Market feed', marketOpen ? 'Live session' : 'Paused after close', Database],
    ['Model type', 'XGBoost', Brain],
  ] as const;
  return <div className="space-y-4 animate-[fade-in_0.3s_ease]">
    <div><h1 className="text-xl font-bold">ML Models</h1><p className="text-xs text-text-muted mt-1">Operational model and data-pipeline status</p></div>
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {rows.map(([label, value, Icon]) => <div key={label} className="glass-card p-5 flex items-center gap-4"><span className="w-10 h-10 rounded-lg bg-brand-blue/10 flex items-center justify-center"><Icon size={18} className="text-brand-blue" /></span><div><div className="text-[10px] uppercase tracking-wider text-text-muted">{label}</div><div className="font-mono font-bold text-text-primary mt-1">{value}</div></div></div>)}
    </div>
    <div className="glass-card p-6 border-brand-gold/20"><div className="flex items-center gap-2 font-semibold"><Brain size={16} className="text-brand-gold" />Model metrics</div><p className="text-sm text-text-secondary mt-4">Validated accuracy, Sharpe ratio, and drawdown will appear after a model report is published. No performance numbers are being fabricated.</p></div>
  </div>;
}
