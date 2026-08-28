import { useQuery } from '@tanstack/react-query';
import { getTradeHistory, getPortfolioSummary } from '@/lib/api';
import clsx from 'clsx';
import { Clock, TrendingUp, TrendingDown } from 'lucide-react';

export default function TradeHistory() {
  const { data: trades = [], isLoading } = useQuery({
    queryKey: ['trades-full'],
    queryFn: () => getTradeHistory(100).then(r => r.data),
    refetchInterval: 15000,
  });
  const { data: portfolio } = useQuery({
    queryKey: ['portfolio'],
    queryFn: () => getPortfolioSummary().then(r => r.data),
  });

  const completedTrades = trades.filter((t: any) => t.pnl != null);
  const totalPnl   = completedTrades.reduce((s: number, t: any) => s + Number(t.pnl || 0), 0);
  const wins       = completedTrades.filter((t: any) => t.pnl > 0).length;
  const losses     = completedTrades.filter((t: any) => t.pnl < 0).length;
  const winRate    = completedTrades.length > 0 ? ((wins / completedTrades.length) * 100).toFixed(1) : '0';

  return (
    <div className="space-y-4 animate-[fade-in_0.3s_ease]">
      <div>
        <h1 className="text-xl font-bold flex items-center gap-2"><Clock size={20} className="text-brand-blue" /> Trade History</h1>
        <p className="text-text-muted text-xs mt-0.5">All AI-executed and manual trades</p>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: 'Recorded executions', value: trades.length, color: 'text-brand-blue' },
          { label: 'Total P&L',    value: `${totalPnl >= 0 ? '+' : ''}₹${Math.abs(totalPnl).toFixed(0)}`, color: totalPnl >= 0 ? 'text-brand-green' : 'text-brand-red' },
          { label: 'Win Rate',     value: `${winRate}%`, color: 'text-brand-gold' },
          { label: 'Closed wins / losses', value: `${wins} / ${losses}`, color: 'text-text-primary' },
        ].map(s => (
          <div key={s.label} className="glass-card p-4">
            <div className="text-[10px] uppercase tracking-widest text-text-muted mb-2">{s.label}</div>
            <div className={clsx('text-2xl font-black font-mono', s.color)}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Trades table */}
      <div className="glass-card overflow-hidden">
        <div className="px-5 py-3 border-b border-[var(--border)]">
          <span className="text-sm font-semibold">All Trades</span>
        </div>
        {isLoading && <div className="p-8 text-center text-text-muted">Loading trade history...</div>}
        {!isLoading && trades.length === 0 && (
          <div className="p-12 text-center">
            <div className="text-4xl mb-3">📋</div>
            <p className="text-text-muted text-sm">No trades yet.</p>
            <p className="text-text-muted text-xs mt-1">The bot will start trading automatically during NSE market hours (9:15 AM – 3:30 PM IST).</p>
          </div>
        )}
        {!isLoading && trades.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-[11px]">
              <thead>
                <tr className="text-text-muted text-[9px] uppercase tracking-wider">
                  {['Date/Time','Symbol','Action','Qty','Entry','Exit','P&L','Confidence','Mode','Status'].map(h => (
                    <th key={h} className="text-left px-4 py-2.5 border-b border-[var(--border)] font-semibold">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {trades.map((t: any) => (
                  <tr key={t.id} className="hover:bg-white/[0.02] transition-colors border-b border-white/[0.03] last:border-0">
                    <td className="px-4 py-3 font-mono text-text-muted">
                      {new Date(t.entered_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false })}
                    </td>
                    <td className="px-4 py-3 font-mono font-bold">{t.symbol}</td>
                    <td className="px-4 py-3">
                      <span className={clsx('flex items-center gap-1 text-[10px] font-bold',
                        t.action === 'buy' ? 'text-brand-green' : 'text-brand-red'
                      )}>
                        {t.action === 'buy' ? <TrendingUp size={10}/> : <TrendingDown size={10}/>}
                        {t.action.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono">{t.quantity}</td>
                    <td className="px-4 py-3 font-mono">₹{t.entry_price}</td>
                    <td className="px-4 py-3 font-mono">{t.exit_price ? `₹${t.exit_price}` : <span className="text-brand-blue">Open</span>}</td>
                    <td className={clsx('px-4 py-3 font-mono font-bold', (t.pnl || 0) >= 0 ? 'text-brand-green' : 'text-brand-red')}>
                      {t.pnl != null ? `${t.pnl >= 0 ? '+' : ''}₹${Math.abs(t.pnl).toFixed(0)}` : '—'}
                    </td>
                    <td className="px-4 py-3">
                      {t.ai_confidence ? (
                        <div className="flex items-center gap-1.5">
                          <div className="w-12 h-1 bg-white/10 rounded-full overflow-hidden">
                            <div className="h-full bg-brand-blue rounded-full" style={{ width: `${t.ai_confidence}%` }} />
                          </div>
                          <span className="text-brand-blue font-mono">{t.ai_confidence}%</span>
                        </div>
                      ) : <span className="text-text-muted">Manual</span>}
                    </td>
                    <td className="px-4 py-3">
                      <span className={clsx('text-[9px] px-1.5 py-0.5 rounded font-bold uppercase',
                        t.is_paper ? 'bg-brand-gold/10 text-brand-gold' : 'bg-brand-red/10 text-brand-red'
                      )}>{t.is_paper ? 'Paper' : 'Live'}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={clsx('text-[9px] px-1.5 py-0.5 rounded font-bold uppercase',
                        t.status === 'executed' ? 'bg-brand-green/10 text-brand-green' : 'bg-text-muted/10 text-text-muted'
                      )}>{t.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

