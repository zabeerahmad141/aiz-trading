import { useQuery } from '@tanstack/react-query';
import { BarChart3, CalendarDays } from 'lucide-react';
import { getPortfolioSessions, getTradeHistory } from '@/lib/api';

export default function Reports() {
  const { data: sessionData, isLoading } = useQuery({ queryKey: ['portfolio-sessions'], queryFn: () => getPortfolioSessions(30).then(r => r.data) });
  const { data: trades = [] } = useQuery({ queryKey: ['reports-trades'], queryFn: () => getTradeHistory(200).then(r => r.data) });
  const totalPnl = trades.reduce((sum: number, trade: any) => sum + Number(trade.pnl || 0), 0);
  return <div className="space-y-4 animate-[fade-in_0.3s_ease]">
    <div><h1 className="text-xl font-bold">Reports</h1><p className="text-xs text-text-muted mt-1">Historical performance from recorded trades</p></div>
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4"><div className="glass-card p-5"><div className="text-[10px] uppercase tracking-wider text-text-muted">Recorded trades</div><div className="text-2xl font-mono font-bold text-brand-blue mt-2">{trades.length}</div></div><div className="glass-card p-5"><div className="text-[10px] uppercase tracking-wider text-text-muted">Realized P&amp;L</div><div className={`text-2xl font-mono font-bold mt-2 ${totalPnl >= 0 ? 'text-brand-green' : 'text-brand-red'}`}>{totalPnl >= 0 ? '+' : '-'}₹{Math.abs(totalPnl).toLocaleString('en-IN')}</div></div><div className="glass-card p-5"><div className="text-[10px] uppercase tracking-wider text-text-muted">Data status</div><div className="text-sm font-semibold text-text-secondary mt-3">{isLoading ? 'Loading history' : trades.length ? 'History available' : 'Awaiting first trade'}</div></div></div>
    <div className="glass-card overflow-hidden"><div className="px-4 py-3 border-b border-[var(--border)] flex items-center gap-2 font-semibold"><CalendarDays size={15} className="text-brand-gold" />Session performance</div>{sessionData?.sessions?.length ? <div className="divide-y divide-white/[0.04]">{sessionData.sessions.map((session: any) => <div key={session.date} className="px-4 py-3 flex items-center justify-between"><span className="font-mono text-sm">{session.date}</span><span className="text-xs text-text-muted">{session.trades} trades · {session.win_rate}% wins</span><span className={session.pnl >= 0 ? 'text-brand-green font-mono' : 'text-brand-red font-mono'}>{session.pnl >= 0 ? '+' : '-'}₹{Math.abs(session.pnl).toLocaleString('en-IN')}</span></div>)}</div> : <div className="p-8 text-center text-sm text-text-muted"><BarChart3 size={24} className="mx-auto mb-2 text-brand-blue animate-pulse" />Completed sessions will appear after trades are recorded.</div>}</div>
  </div>;
}
