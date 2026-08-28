import { useQuery } from '@tanstack/react-query';
import { getApiStatus, getQuotes } from '@/lib/api';
import clsx from 'clsx';
import { RefreshCw, TrendingUp, TrendingDown } from 'lucide-react';

export default function Markets() {
  const { data: quotes = [], isLoading, isError, isFetching, dataUpdatedAt, refetch } = useQuery({
    queryKey: ['quotes'],
    queryFn: () => getQuotes().then(r => r.data),
    refetchInterval: 10000,
  });
  const { data: apiStatus } = useQuery({
    queryKey: ['api-status'],
    queryFn: () => getApiStatus().then(r => r.data),
    refetchInterval: 30000,
  });
  const marketOpen = apiStatus?.market_open === true;
  const feedAvailable = quotes.length > 0;
  const statusLabel = isError ? 'Unavailable' : feedAvailable ? (marketOpen ? 'Live' : 'Recent') : 'Paused';

  return (
    <div className="space-y-4 animate-[fade-in_0.3s_ease]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2"><TrendingUp size={20} className="text-brand-blue" /> Live Market</h1>
          <p className="text-text-muted text-xs mt-0.5">
            NSE Nifty 50 Watchlist · Auto-refresh 10s
            {dataUpdatedAt > 0 && <span className="ml-2 text-brand-green">· Updated {new Date(dataUpdatedAt).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour12: false })}</span>}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => refetch()} disabled={isFetching} title="Refresh market data" className="p-2 rounded-lg border border-white/10 text-text-muted hover:text-brand-blue disabled:opacity-40"><RefreshCw size={14} className={isFetching ? 'animate-spin' : ''} /></button>
          <div className={clsx('w-2 h-2 rounded-full', feedAvailable ? 'bg-brand-green animate-pulse' : 'bg-text-muted')} />
          <span className={clsx('text-xs font-semibold', feedAvailable ? 'text-brand-green' : 'text-text-muted')}>{statusLabel}</span>
        </div>
      </div>

      <div className="glass-card overflow-hidden">
        {isLoading && <div className="p-8 text-center text-text-muted">Fetching live quotes from NSE...</div>}
        {isError && (
          <div className="p-8 text-center">
            <p className="text-brand-red text-sm">Could not fetch live quotes.</p>
            <p className="text-text-muted text-xs mt-1">Market may be closed or yfinance rate limit reached. Data refreshes every 10s.</p>
          </div>
        )}
        {!isLoading && quotes.length > 0 && (
          <table className="w-full text-[12px]">
            <thead>
              <tr className="text-text-muted text-[10px] uppercase tracking-wider">
                {['Symbol','LTP','Open','High','Low','Change %','Volume','AI Signal'].map(h => (
                  <th key={h} className="text-left px-5 py-3 border-b border-[var(--border)] font-semibold">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {quotes.map((q: any) => (
                <tr key={q.symbol} className="hover:bg-white/[0.02] transition-colors border-b border-white/[0.03] last:border-0">
                  <td className="px-5 py-3 font-mono font-bold text-text-primary">{q.symbol}</td>
                  <td className="px-5 py-3 font-mono font-bold text-brand-blue">₹{q.ltp?.toFixed(2)}</td>
                  <td className="px-5 py-3 font-mono text-text-secondary">₹{q.open?.toFixed(2) || '—'}</td>
                  <td className="px-5 py-3 font-mono text-brand-green">₹{q.high?.toFixed(2) || '—'}</td>
                  <td className="px-5 py-3 font-mono text-brand-red">₹{q.low?.toFixed(2) || '—'}</td>
                  <td className={clsx('px-5 py-3 font-mono font-bold flex items-center gap-1',
                    (q.change_pct || 0) >= 0 ? 'text-brand-green' : 'text-brand-red'
                  )}>
                    {(q.change_pct || 0) >= 0 ? <TrendingUp size={11}/> : <TrendingDown size={11}/>}
                    {(q.change_pct || 0) >= 0 ? '+' : ''}{(q.change_pct || 0).toFixed(2)}%
                  </td>
                  <td className="px-5 py-3 font-mono text-text-muted">{q.volume ? (q.volume / 100000).toFixed(1) + 'L' : '—'}</td>
                  <td className="px-5 py-3">
                    <span className="text-[10px] px-2 py-0.5 rounded border bg-white/5 text-text-muted border-white/10">—</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {!isLoading && !isError && quotes.length === 0 && (
          <div className="p-8 text-center text-text-muted text-sm">
            {isError ? 'Market feed unavailable. Check provider configuration and container logs.' : marketOpen ? 'No quotes received yet. The provider may be warming up.' : 'Market closed — quotes will refresh during NSE hours (9:15 AM – 3:30 PM IST)'}
          </div>
        )}
      </div>
    </div>
  );
}

