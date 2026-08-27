import { useQuery } from '@tanstack/react-query';
import { getQuotes } from '@/lib/api';

const FALLBACK = [
  { symbol: 'NIFTY 50',   ltp: 24153, change_pct: 0.82 },
  { symbol: 'SENSEX',     ltp: 79814, change_pct: 0.75 },
  { symbol: 'RELIANCE',   ltp: 2847,  change_pct: 1.32 },
  { symbol: 'TCS',        ltp: 3421,  change_pct: 0.78 },
  { symbol: 'HDFCBANK',   ltp: 1672,  change_pct: -0.24 },
  { symbol: 'INFY',       ltp: 1814,  change_pct: 0.55 },
  { symbol: 'WIPRO',      ltp: 452,   change_pct: 1.10 },
  { symbol: 'ICICIBANK',  ltp: 1221,  change_pct: 0.94 },
  { symbol: 'BAJFINANCE', ltp: 6980,  change_pct: 1.87 },
  { symbol: 'SBIN',       ltp: 813,   change_pct: -0.15 },
];

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
    queryKey: ['ticker-quotes'],
    queryFn: () => getQuotes().then(r => r.data).catch(() => []),
    refetchInterval: 30000,
    staleTime: 20000,
    retry: 0,
  });

  const items: any[] = (quotes && (quotes as any[]).length > 0 ? quotes : FALLBACK) as any[];
  const doubled = [...items, ...items];

  return (
    <div className="fixed top-0 left-0 right-0 h-[34px] bg-[rgba(6,11,20,0.97)] border-b border-[var(--border)] z-[200] overflow-hidden flex items-center">
      <div className="flex gap-10 animate-[ticker_50s_linear_infinite]">
        {doubled.map((t: any, i: number) => (
          <Item key={i} symbol={t.symbol || t.n} ltp={t.ltp || t.close || 0} change_pct={t.change_pct || 0} />
        ))}
      </div>
    </div>
  );
}

