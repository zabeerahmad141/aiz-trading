import { useQuery } from '@tanstack/react-query';
import { getQuotes } from '@/lib/api';

function Item({ symbol, ltp, change_pct }: { symbol: string; ltp: number; change_pct: number }) {
  const up = change_pct >= 0;
  return (
    <span className="inline-flex items-center gap-2 px-2 text-[11px] font-mono whitespace-nowrap">
      <span className="w-1.5 h-1.5 rounded-full bg-brand-blue/50 flex-shrink-0" />
      <span className="text-text-secondary font-semibold">{symbol}</span>
      <span className="text-text-primary">₹{Number(ltp).toLocaleString('en-IN')}</span>
      <span className={up ? 'text-brand-green' : 'text-brand-red'}>
        {up ? '+' : ''}{Number(change_pct).toFixed(2)}%
      </span>
    </span>
  );
}

export default function TickerTape() {
  const { data: quotes } = useQuery({
    queryKey: ['quotes'],
    queryFn: () => getQuotes().then(r => Array.isArray(r.data) ? r.data : []).catch(() => []),
    refetchInterval: 10000,
    staleTime: 10000,
    retry: 2,
    retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 4000),
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
  });

  const items: any[] = ((quotes || []) as any[]).filter((quote) => Number(quote.ltp || 0) > 0);
  const doubled = [...items, ...items];
  const tickerStatus = items.length ? 'Live market feed' : 'Checking market feed';

  return (
    <div className="fixed top-0 left-0 right-0 h-[34px] bg-[rgba(6,11,20,0.97)] border-b border-[var(--border)] z-[200] overflow-hidden flex items-center">
      <div className={items.length ? 'flex gap-10 animate-[ticker_50s_linear_infinite]' : 'flex items-center justify-center w-full'}>
        {items.length ? doubled.map((t: any, i: number) => (
          <Item key={i} symbol={t.symbol || t.n} ltp={t.ltp || t.close || 0} change_pct={t.change_pct || 0} />
        )) : <span className="text-[10px] uppercase tracking-[2px] text-text-muted animate-pulse">{tickerStatus}</span>}
      </div>
    </div>
  );
}

