import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getScreener } from '@/lib/api';
import clsx from 'clsx';
import { Search, TrendingUp, TrendingDown, RefreshCw } from 'lucide-react';

interface ScreenerStock {
  symbol: string;
  ltp: number;
  change_pct: number;
  rsi: number;
  vol_ratio: number;
  ema9: number;
  ema21: number;
  score: number;
  reason: string;
}

interface ScreenerResponse {
  screened: ScreenerStock[];
  total_scanned: number;
}

export default function Screener() {
  const [minScore, setMinScore] = useState(50);

  const { data, isLoading, isFetching, refetch, dataUpdatedAt } = useQuery<ScreenerResponse>({
    queryKey: ['screener'],
    queryFn: () => getScreener().then(r => r.data),
    staleTime: 5 * 60 * 1000,   // 5 min cache
    retry: 1,
  });

  const stocks = ((data as any)?.screened || []).filter((s: any) => s.score >= minScore);

  return (
    <div className="space-y-4 animate-[fade-in_0.3s_ease]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Search size={20} className="text-brand-gold" /> Stock Screener
          </h1>
          <p className="text-text-muted text-xs mt-0.5">
            Auto-screens {(data as any)?.total_scanned || 40} Nifty stocks · Picks best candidates for today
            {dataUpdatedAt > 0 && (
              <span className="ml-2 text-brand-green">
                · Scanned at {new Date(dataUpdatedAt).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour12: false })}
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs text-text-muted">
            <span>Min Score:</span>
            <select value={minScore} onChange={e => setMinScore(Number(e.target.value))}
              className="bg-white/5 border border-white/10 rounded px-2 py-1 text-text-primary text-xs focus:outline-none">
              {[25,50,75,100].map(v => <option key={v} value={v}>{v}%</option>)}
            </select>
          </div>
          <button onClick={() => refetch()} disabled={isFetching}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand-blue/10 text-brand-blue border border-brand-blue/25 text-xs font-semibold hover:bg-brand-blue/20 disabled:opacity-50">
            <RefreshCw size={12} className={isFetching ? 'animate-spin' : ''} />
            {isFetching ? 'Scanning...' : 'Re-scan'}
          </button>
        </div>
      </div>

      {/* Criteria info */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: 'Uptrend (EMA)',   desc: 'Price above EMA 9 & 21',     points: '+50 pts', color: 'text-brand-green' },
          { label: 'RSI Zone',        desc: 'RSI between 40-65',           points: '+25 pts', color: 'text-brand-blue' },
          { label: 'Volume Surge',    desc: 'Volume > 1.3x 20-day avg',    points: '+25 pts', color: 'text-brand-gold' },
          { label: 'Auto-updates',    desc: 'Re-scans every 5 minutes',    points: 'Live',    color: 'text-brand-green' },
        ].map(c => (
          <div key={c.label} className="glass-card p-3">
            <div className={clsx('text-[10px] font-bold uppercase tracking-wider mb-1', c.color)}>{c.label}</div>
            <div className="text-[11px] text-text-muted">{c.desc}</div>
            <div className={clsx('text-[11px] font-mono font-bold mt-1', c.color)}>{c.points}</div>
          </div>
        ))}
      </div>

      {/* Results */}
      <div className="glass-card overflow-hidden">
        <div className="px-5 py-3 border-b border-[var(--border)] flex items-center justify-between">
          <span className="text-sm font-semibold">
            {isLoading ? 'Scanning market...' : `${stocks.length} stocks selected`}
          </span>
          {!isLoading && data && (
            <span className="text-xs text-text-muted">
              Scanned {(data as any).total_scanned} stocks from Nifty pool
            </span>
          )}
        </div>

        {isLoading && (
          <div className="p-10 text-center">
            <div className="text-brand-blue animate-pulse text-sm">Scanning {(data as any)?.total_scanned || 40} stocks...</div>
            <div className="text-text-muted text-xs mt-2">Fetching OHLCV, computing indicators. Takes ~30 seconds.</div>
          </div>
        )}

        {!isLoading && stocks.length === 0 && (
          <div className="p-10 text-center">
            <div className="text-4xl mb-3">🔍</div>
            <p className="text-text-muted text-sm">No stocks meet the criteria right now.</p>
            <p className="text-text-muted text-xs mt-1">Try lowering the Min Score or check during market hours (9:15 AM–3:30 PM IST).</p>
          </div>
        )}

        {!isLoading && stocks.length > 0 && (
          <table className="w-full text-[12px]">
            <thead>
              <tr className="text-text-muted text-[10px] uppercase tracking-wider">
                {['Rank','Symbol','LTP','Change','RSI','Vol Ratio','Score','Reason','Action'].map(h => (
                  <th key={h} className="text-left px-4 py-2.5 border-b border-[var(--border)] font-semibold">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {stocks.map((s: any, i: number) => (
                <tr key={s.symbol} className={clsx('hover:bg-white/[0.02] transition-colors border-b border-white/[0.03] last:border-0',
                  i === 0 && 'bg-brand-green/[0.03]'
                )}>
                  <td className="px-4 py-3">
                    <span className={clsx('text-[11px] font-bold w-6 h-6 rounded-full flex items-center justify-center',
                      i === 0 ? 'bg-brand-gold text-black' : i === 1 ? 'bg-white/20 text-text-primary' : 'text-text-muted'
                    )}>#{i+1}</span>
                  </td>
                  <td className="px-4 py-3 font-mono font-bold text-text-primary">{s.symbol}</td>
                  <td className="px-4 py-3 font-mono font-bold text-brand-blue">₹{s.ltp?.toFixed(2)}</td>
                  <td className={clsx('px-4 py-3 font-mono font-bold flex items-center gap-1',
                    s.change_pct >= 0 ? 'text-brand-green' : 'text-brand-red'
                  )}>
                    {s.change_pct >= 0 ? <TrendingUp size={10}/> : <TrendingDown size={10}/>}
                    {s.change_pct >= 0 ? '+' : ''}{s.change_pct?.toFixed(2)}%
                  </td>
                  <td className={clsx('px-4 py-3 font-mono', s.rsi >= 40 && s.rsi <= 65 ? 'text-brand-green' : 'text-text-muted')}>
                    {s.rsi?.toFixed(1)}
                  </td>
                  <td className={clsx('px-4 py-3 font-mono', s.vol_ratio >= 1.3 ? 'text-brand-gold' : 'text-text-muted')}>
                    {s.vol_ratio?.toFixed(2)}x
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-1.5 bg-white/10 rounded-full overflow-hidden">
                        <div className={clsx('h-full rounded-full', s.score >= 100 ? 'bg-brand-green' : s.score >= 75 ? 'bg-brand-gold' : 'bg-brand-blue')}
                          style={{ width: `${s.score}%` }} />
                      </div>
                      <span className={clsx('text-[11px] font-bold font-mono',
                        s.score >= 100 ? 'text-brand-green' : s.score >= 75 ? 'text-brand-gold' : 'text-brand-blue'
                      )}>{s.score}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-text-muted text-[11px]">{s.reason}</td>
                  <td className="px-4 py-3">
                    <span className="text-[10px] px-2 py-0.5 rounded border border-brand-green/30 text-brand-green bg-brand-green/10 font-bold">
                      Watch
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="glass-card p-4 text-[11px] text-text-muted">
        <strong className="text-text-secondary">How to use:</strong> Screener runs automatically. 
        Add top stocks to your watchlist in <code className="text-brand-blue">.env → WATCHLIST=STOCK1,STOCK2,...</code> 
        then restart backend. The AI bot will start analysing and trading those stocks automatically.
      </div>
    </div>
  );
}
