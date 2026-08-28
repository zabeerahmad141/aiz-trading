import { useQuery } from '@tanstack/react-query';
import { getAISignals, getBotStatus, getTradeHistory } from '@/lib/api';
import clsx from 'clsx';
import { Brain, RefreshCw, Zap, Target, TrendingUp } from 'lucide-react';

export default function AIEngine() {
  const { data: botStatus } = useQuery({
    queryKey: ['botStatus'],
    queryFn: () => getBotStatus().then(r => r.data),
    refetchInterval: 5000,
  });
  const { data: trades = [] } = useQuery({
    queryKey: ['trades'],
    queryFn: () => getTradeHistory().then(r => r.data),
  });
  const { data: signalResponse, isLoading: signalsLoading, isError: signalsError, isFetching: signalsFetching, refetch: refetchSignals } = useQuery({
    queryKey: ['ai-signals'],
    queryFn: () => getAISignals().then(r => r.data),
    refetchInterval: 15000,
  });

  const aiTrades    = trades.filter((t: any) => t.ai_confidence);
  const wins        = aiTrades.filter((t: any) => t.pnl > 0).length;
  const winRate     = aiTrades.length > 0 ? ((wins / aiTrades.length) * 100).toFixed(1) : null;
  const avgConf     = aiTrades.length > 0
    ? (aiTrades.reduce((s: number, t: any) => s + t.ai_confidence, 0) / aiTrades.length).toFixed(0)
    : null;
  const predictions = signalResponse?.signals || [];

  return (
    <div className="space-y-4 animate-[fade-in_0.3s_ease]">
      <div>
        <h1 className="text-xl font-bold flex items-center gap-2"><Brain size={20} className="text-brand-gold" /> AI Engine</h1>
        <p className="text-text-muted text-xs mt-0.5">Model performance, live predictions and signal analysis</p>
      </div>

      {/* Engine status */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: 'Engine Status',    value: botStatus?.market_open ? 'TRADING' : 'STANDBY', color: botStatus?.market_open ? 'text-brand-green' : 'text-brand-gold', icon: Zap },
          { label: 'Closed-trade win rate', value: winRate ? `${winRate}%` : 'N/A', color: 'text-brand-green', icon: Target },
          { label: 'Avg confidence',   value: avgConf ? `${avgConf}%` : 'N/A', color: 'text-brand-blue',  icon: Brain },
          { label: 'AI Trades Placed', value: aiTrades.length || 0, color: 'text-brand-blue', icon: TrendingUp },
        ].map(({ label, value, color, icon: Icon }) => (
          <div key={label} className="glass-card card-top-gold p-5 relative overflow-hidden">
            <div className="text-[10px] uppercase tracking-widest text-text-muted mb-2 flex items-center gap-1.5"><Icon size={10}/>{label}</div>
            <div className={clsx('text-2xl font-black font-mono', color)}>{value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-[1fr_300px] gap-4">
        {/* Live predictions */}
        <div className="glass-card overflow-hidden">
          <div className="px-5 py-3 border-b border-[var(--border)] flex items-center justify-between">
            <span className="text-sm font-semibold flex items-center gap-2"><Brain size={14} className="text-brand-gold"/>AI Predictions — Next Signal</span>
            <div className="flex items-center gap-2"><button onClick={() => refetchSignals()} disabled={signalsFetching} title="Refresh signals" className="p-1.5 rounded border border-white/10 text-text-muted hover:text-brand-blue disabled:opacity-40"><RefreshCw size={12} className={signalsFetching ? 'animate-spin' : ''} /></button><span className="text-[10px] text-text-muted">Latest ML engine signals</span></div>
          </div>
          <div className="divide-y divide-white/[0.04]">
            {signalsLoading && <div className="px-5 py-8 text-center text-xs text-text-muted">Checking for the latest ML signals...</div>}
            {signalsError && <div className="px-5 py-8 text-center text-xs text-brand-red">Signal feed unavailable. Check the backend and ML engine.</div>}
            {!signalsLoading && !signalsError && predictions.length === 0 && <div className="px-5 py-8 text-center text-xs text-text-muted">{botStatus?.market_open ? 'No signal has been published yet.' : 'Market is closed. The ML engine will generate signals during the next NSE session.'}</div>}
            {predictions.map((p: any) => (
              <div key={p.symbol} className="flex items-center gap-4 px-5 py-3 hover:bg-white/[0.02]">
                <span className="w-20 font-mono font-bold text-[12px]">{p.symbol}</span>
                <span className={clsx('text-[10px] font-bold px-2 py-0.5 rounded-full border w-12 text-center',
                  p.signal?.toLowerCase() === 'buy'  ? 'text-brand-green bg-brand-green/10 border-brand-green/30' :
                  p.signal?.toLowerCase() === 'sell' ? 'text-brand-red   bg-brand-red/10   border-brand-red/30' :
                                        'text-text-muted  bg-white/5         border-white/10'
                )}>{p.signal}</span>
                <div className="flex-1">
                  <div className="flex justify-between text-[9px] text-text-muted mb-1">
                    <span>{p.reason || 'No explanation provided'}</span><span>{p.confidence}%</span>
                  </div>
                  <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                    <div className={clsx('h-full rounded-full transition-all', p.signal?.toLowerCase() === 'buy' ? 'bg-brand-green' : p.signal?.toLowerCase() === 'sell' ? 'bg-brand-red' : 'bg-text-muted')}
                      style={{ width: `${p.confidence || 0}%` }} />
                  </div>
                </div>
                <span className="text-[11px] font-mono text-text-muted w-14 text-right">₹{p.ltp?.toFixed?.(2) || 'N/A'}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Model stats */}
        <div className="space-y-3">
          <div className="glass-card overflow-hidden">
            <div className="px-4 py-3 border-b border-[var(--border)]">
              <span className="text-sm font-semibold">Model Details</span>
            </div>
            <div className="divide-y divide-white/[0.04]">
              {[
                { l: 'Algorithm',     v: 'XGBoost',                     c: 'text-brand-blue' },
                { l: 'Training Data', v: '3 Years OHLCV + Indicators',  c: 'text-text-primary' },
                { l: 'Features',      v: '24 Technical Indicators',     c: 'text-text-primary' },
                { l: 'Sharpe Ratio',  v: 'N/A',                         c: 'text-text-muted' },
                { l: 'Max Drawdown',  v: 'N/A',                         c: 'text-text-muted' },
                { l: 'Last Retrain',  v: 'Reported by ML engine',       c: 'text-text-muted' },
                { l: 'Next Retrain',  v: 'Configured schedule',          c: 'text-text-muted' },
              ].map(({ l, v, c }) => (
                <div key={l} className="flex justify-between items-center px-4 py-2.5">
                  <span className="text-[11px] text-text-secondary">{l}</span>
                  <span className={clsx('text-[11px] font-mono font-semibold', c)}>{v}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="glass-card p-4">
            <div className="text-[10px] uppercase tracking-widest text-text-muted mb-3">Feature Importance</div>
            <div className="text-xs text-text-muted">Feature importance will appear after model metrics are persisted by the ML engine.</div>
          </div>
        </div>
      </div>
    </div>
  );
}

