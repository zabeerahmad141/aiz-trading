import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import {
  getPortfolioSummary, getBotStatus, getOpenPositions,
  getTradeHistory, getOHLCV, getQuotes, getPnLChart, getPortfolioSessions, placeOrder,
  getPortfolioRisk, getApiStatus,
} from '@/lib/api';
import { Wallet, TrendingUp, Target, Bot, Shield, Brain, Zap, RefreshCw, ShoppingCart } from 'lucide-react';
import clsx from 'clsx';
import { useAuthStore } from '@/store/auth';
// @ts-ignore
import { createChart, ColorType, CrosshairMode } from 'lightweight-charts';

// ── Candlestick chart component — fetches real data from backend ────────────
type ChartView = 'candles' | 'line' | 'area';

function CandleChart({ symbol = 'RELIANCE', interval, view }: { symbol?: string; interval: string; view: ChartView }) {
  const ref = useRef<HTMLDivElement>(null);
  const { data: ohlcvData } = useQuery({
    queryKey: ['ohlcv', symbol, interval],
    queryFn: () => getOHLCV(symbol, '1d', interval).then(r => r.data),
    refetchInterval: 60000,
    staleTime: 60000,
    gcTime: 24 * 60 * 60 * 1000,
    placeholderData: (previousData) => previousData,
    retry: 2,
  });

  useEffect(() => {
    if (!ref.current) return;
    const chart = createChart(ref.current, {
      width: ref.current.clientWidth,
      height: 320,
      layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: '#7a8fa6' },
      grid: { vertLines: { color: 'rgba(255,255,255,0.04)' }, horzLines: { color: 'rgba(255,255,255,0.04)' } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: 'rgba(0,212,255,0.12)', scaleMargins: { top: 0.08, bottom: 0.24 } },
      timeScale: { borderColor: 'rgba(0,212,255,0.12)', timeVisible: true, secondsVisible: false },
    });
    const series = view === 'candles' ? chart.addCandlestickSeries({
      upColor: '#00e676', downColor: '#ff3d71',
      borderUpColor: '#00e676', borderDownColor: '#ff3d71',
      wickUpColor: 'rgba(0,230,118,0.5)', wickDownColor: 'rgba(255,61,113,0.5)',
    }) : view === 'area' ? chart.addAreaSeries({
      lineColor: '#00d4ff', topColor: 'rgba(0,212,255,0.24)', bottomColor: 'rgba(0,212,255,0.02)',
      lineWidth: 2,
    }) : chart.addLineSeries({ color: '#00d4ff', lineWidth: 2, priceLineVisible: false });
    const emaLine = view === 'candles' ? chart.addLineSeries({ color: 'rgba(255,193,7,0.85)', lineWidth: 1, priceLineVisible: false }) : null;
    const volumeSeries = view === 'candles' ? chart.addHistogramSeries({
      color: 'rgba(0,212,255,0.35)', priceFormat: { type: 'volume' }, priceScaleId: '',
    }) : null;
    if (volumeSeries) chart.priceScale('').applyOptions({ scaleMargins: { top: 0.82, bottom: 0.02 } });

    // Render only provider candles; no generated incremental series is used.
    const candles = ohlcvData?.candles;
    const data: any[] = candles && candles.length > 5 ? candles : [];
    if (!data.length) return () => chart.remove();
    if (view === 'candles') series.setData(data);
    else series.setData(data.map(d => ({ time: d.time, value: Number(d.close) })));
    volumeSeries?.setData(data.map(d => ({
      time: d.time,
      value: Number(d.volume || 0),
      color: d.close >= d.open ? 'rgba(0,230,118,0.35)' : 'rgba(255,61,113,0.35)',
    })));

    // EMA overlay
    let emaVal = data[0]?.close || 2820;
    const emaData = data.map(d => { emaVal = emaVal * 0.9 + d.close * 0.1; return { time: d.time, value: +emaVal.toFixed(2) }; });
    emaLine?.setData(emaData);

    // Live tick update (for real last candle)
    const ro = new ResizeObserver(() => { if (ref.current) chart.applyOptions({ width: ref.current.clientWidth }); });
    ro.observe(ref.current);
    return () => { chart.remove(); ro.disconnect(); };
  }, [ohlcvData, view]);

  return <div ref={ref} className={!ohlcvData?.candles?.length ? 'h-[320px] flex items-center justify-center text-xs text-text-muted' : 'h-[320px]'}>{!ohlcvData?.candles?.length && <span>{'No verified candles available for this symbol.'}</span>}</div>;
}

// ── AI Predictions panel ─────────────────────────────────────────────────────
function AIPredictions({ marketOpen }: { marketOpen: boolean }) {
  return (
    <div className="glass-card">
      <div className="px-4 py-3 border-b border-[var(--border)] flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <span className="w-6 h-6 rounded bg-brand-gold/10 flex items-center justify-center"><Brain size={12} className="text-brand-gold" /></span>
          AI Predictions
        </div>
        <span className="text-[10px] text-text-muted">Next 30 min</span>
      </div>
      <div className="px-4 py-6 text-center text-xs text-text-muted">
        <div className="relative mx-auto mb-3 w-10 h-10 rounded border border-white/15 bg-white/[0.04] flex items-center justify-center">
          <Brain size={16} className="text-text-secondary" />
        </div>
        <div className="text-text-secondary">{marketOpen ? 'Waiting for the next model signal.' : 'The model is resting between sessions.'}</div>
        <div className="mt-1 text-[10px]">Live predictions will appear automatically when signals are published.</div>
      </div>
    </div>
  );
}

function MarketContext({ status, quotes }: { status?: any; quotes: any[] }) {
  const validQuotes = quotes.filter(quote => Number(quote.ltp) > 0);
  const averageChange = validQuotes.length
    ? validQuotes.reduce((sum, quote) => sum + Number(quote.change_pct || 0), 0) / validQuotes.length
    : 0;
  const advancing = validQuotes.filter(quote => Number(quote.change_pct || 0) > 0).length;
  const mood = !validQuotes.length ? 'Waiting' : averageChange >= 1 ? 'Greedy' : averageChange >= 0.2 ? 'Constructive' : averageChange <= -1 ? 'Fearful' : averageChange <= -0.2 ? 'Cautious' : 'Neutral';
  const moodColor = mood === 'Greedy' || mood === 'Constructive' ? 'text-brand-green' : mood === 'Fearful' || mood === 'Cautious' ? 'text-brand-red' : 'text-brand-gold';
  return (
    <div className="glass-card px-4 py-3 border-brand-blue/20">
      <div className="flex items-center justify-between gap-3 mb-2">
        <div className="text-sm font-semibold">Market context</div>
        <span className={clsx('text-xs font-bold uppercase tracking-wide', moodColor)}>Mood: {mood}</span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-[11px]">
        <div><div className="text-text-muted">Current session</div><div className="font-semibold mt-1">{status?.session_state === 'open' ? 'Open' : status?.session_state === 'pre_open' ? 'Pre-open' : 'Closed'}</div><div className="text-text-muted mt-1">{status?.session_comment || 'Checking session status.'}</div></div>
        <div><div className="text-text-muted">Session timeline</div><div className="mt-1">{status?.previous_session || 'Previous session unavailable.'}</div><div className="text-text-muted mt-1">{status?.next_session || 'Next session unavailable.'}</div></div>
        <div><div className="text-text-muted">Watchlist breadth</div><div className="font-mono font-bold mt-1">{advancing}/{validQuotes.length} advancing</div><div className="text-text-muted mt-1">Average change {averageChange >= 0 ? '+' : ''}{averageChange.toFixed(2)}%</div></div>
      </div>
    </div>
  );
}

// ── Model metrics ────────────────────────────────────────────────────────────
function ModelMetrics() {
  const rows = [
    { label: 'Accuracy', value: 'Waiting for metrics', color: 'text-text-muted' },
    { label: 'Sharpe Ratio', value: 'Waiting for metrics', color: 'text-text-muted' },
    { label: 'Max Drawdown', value: 'Waiting for metrics', color: 'text-text-muted' },
    { label: 'Training data', value: 'Awaiting report', color: 'text-text-muted' },
    { label: 'Model', value: 'XGBoost', color: 'text-text-secondary text-[11px]' },
  ];
  return (
    <div className="glass-card">
      <div className="px-4 py-3 border-b border-[var(--border)] flex items-center gap-2 text-sm font-semibold">
        <span className="w-6 h-6 rounded bg-brand-green/10 flex items-center justify-center"><Target size={12} className="text-brand-green" /></span>
        Model Performance
      </div>
      <div className="px-4 py-2 divide-y divide-white/[0.04]">
        {rows.map(r => (
          <div key={r.label} className="flex items-center justify-between py-2.5">
            <span className="text-[12px] text-text-secondary">{r.label}</span>
            <span className={clsx('font-mono font-bold text-[13px]', r.color)}>{r.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Live feed items ──────────────────────────────────────────────────────────
function LiveFeed({ trades }: { trades?: any[] }) {
  const items = trades?.length ? trades.slice(0, 5).map(t => ({
    type: t.action,
    title: `${t.action.toUpperCase()} ${t.symbol} × ${t.quantity}`,
    sub: t.ai_reason || (t.ai_signal ? `AI Signal · Conf ${t.ai_confidence}%` : 'Manual trade'),
    pnl: t.pnl != null ? `${t.pnl >= 0 ? '+' : ''}₹${Math.abs(t.pnl).toFixed(0)}` : '',
    time: new Date(t.entered_at).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', hour12: false }),
  })) : [];

  return (
    <div className="glass-card flex flex-col">
      <div className="px-4 py-3 border-b border-[var(--border)] flex items-center gap-2 text-sm font-semibold">
        <span className="w-6 h-6 rounded bg-brand-blue/10 flex items-center justify-center"><Zap size={12} className="text-brand-blue" /></span>
        Live Activity
        <div className="ml-auto w-1.5 h-1.5 rounded-full bg-brand-green animate-pulse" />
      </div>
      <div className="px-3 py-2 space-y-2 overflow-y-auto max-h-64">
        {items.length ? items.map((f, i) => (
          <div key={i} className={clsx('flex items-center gap-2.5 p-2.5 rounded-lg border transition-colors',
            i === 0 ? 'border-brand-blue/25 bg-brand-blue/4' : 'border-white/4 bg-white/[0.015]'
          )}>
            <div className={clsx('w-7 h-7 rounded-full flex items-center justify-center text-[11px] flex-shrink-0',
              f.type === 'buy' ? 'bg-brand-green/15 text-brand-green' :
              f.type === 'sell' ? 'bg-brand-red/15 text-brand-red' :
              'bg-brand-blue/15 text-brand-blue'
            )}>
              {f.type === 'buy' ? '↑' : f.type === 'sell' ? '↓' : '⚡'}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[12px] font-semibold truncate">{f.title}</div>
              <div className="text-[10px] text-text-muted truncate">{f.sub}</div>
            </div>
            {f.pnl && <span className={clsx('text-[12px] font-bold font-mono flex-shrink-0', f.pnl.startsWith('-') ? 'text-brand-red' : 'text-brand-green')}>{f.pnl}</span>}
            <span className="text-[10px] text-text-muted font-mono flex-shrink-0">{f.time}</span>
          </div>
        )) : <div className="py-8 text-center text-xs text-text-muted">No trading activity recorded.</div>}
      </div>
    </div>
  );
}

// ── Stat card ────────────────────────────────────────────────────────────────
function StatCard({ label, value, sub, color, icon: Icon }: any) {
  return (
    <div className={clsx('glass-card relative p-5 overflow-hidden transition-all hover:-translate-y-0.5 hover:shadow-[0_0_20px_rgba(0,212,255,0.1)] cursor-default',
      color === 'blue' && 'card-top-blue', color === 'gold' && 'card-top-gold', color === 'green' && 'card-top-green',
    )}>
      <div className="text-[10px] uppercase tracking-[1.5px] text-text-muted mb-2.5 flex items-center gap-1.5">
        <Icon size={11} /> {label}
      </div>
      <div className={clsx('text-2xl font-black font-mono tracking-tight',
        color === 'green' ? 'text-brand-green' : color === 'gold' ? 'text-brand-gold' : 'text-brand-blue'
      )}>{value}</div>
      <div className="text-[11px] text-text-muted mt-1.5">{sub}</div>
    </div>
  );
}

// ── Main Dashboard ────────────────────────────────────────────────────────────
export default function Dashboard() {
  const [interval, setInterval] = useState('5m');
  const [chartView, setChartView] = useState<ChartView>('candles');
  const [pnlPeriod, setPnlPeriod] = useState('today');
  const symbols = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'WIPRO', 'ICICIBANK', 'BAJFINANCE', 'SBIN', 'ITC', 'KOTAKBANK'];
  const [order, setOrder] = useState({ symbol: symbols[0], quantity: 1, stop_loss: '', target_price: '' });
  const [chartSymbol, setChartSymbol] = useState('RELIANCE');
  const { username, role } = useAuthStore();
  const canTrade = role === 'admin' || role === 'analyst';
  const { data: portfolio } = useQuery({ queryKey: ['portfolio'], queryFn: () => getPortfolioSummary().then(r => r.data), refetchInterval: 10000 });
  const { data: botStatus } = useQuery({ queryKey: ['botStatus'], queryFn: () => getBotStatus().then(r => r.data), refetchInterval: 5000 });
  const { data: positions } = useQuery({ queryKey: ['positions'], queryFn: () => getOpenPositions().then(r => r.data), refetchInterval: 5000 });
  const { data: trades } = useQuery({ queryKey: ['trades'], queryFn: () => getTradeHistory().then(r => r.data) });
  const { data: quotes = [], isError: quotesError } = useQuery({
    queryKey: ['quotes'],
    queryFn: () => getQuotes().then(r => r.data),
    refetchInterval: 30000,
    staleTime: 30000,
    gcTime: 24 * 60 * 60 * 1000,
    placeholderData: (previousData) => previousData,
    retry: 2,
  });
  const { data: apiStatus } = useQuery({ queryKey: ['api-status'], queryFn: () => getApiStatus().then(r => r.data), refetchInterval: 30000 });
  const { data: pnlChart } = useQuery({ queryKey: ['pnl-chart', pnlPeriod], queryFn: () => getPnLChart(pnlPeriod).then(r => r.data), refetchInterval: 30000 });
  const { data: sessionData } = useQuery({ queryKey: ['portfolio-sessions'], queryFn: () => getPortfolioSessions().then(r => r.data), refetchInterval: 60000 });
  const queryClient = useQueryClient();
  const exitMutation = useMutation({
    mutationFn: (position: any) => placeOrder({ symbol: position.symbol, action: 'sell', quantity: position.quantity }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['positions'] });
      queryClient.invalidateQueries({ queryKey: ['portfolio'] });
      queryClient.invalidateQueries({ queryKey: ['trades'] });
    },
  });
  const orderMutation = useMutation({
    mutationFn: (action: 'buy' | 'sell') => placeOrder({
      symbol: order.symbol,
      quantity: order.quantity,
      action,
      stop_loss: order.stop_loss ? Number(order.stop_loss) : undefined,
      target_price: order.target_price ? Number(order.target_price) : undefined,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['positions'] });
      queryClient.invalidateQueries({ queryKey: ['portfolio'] });
      queryClient.invalidateQueries({ queryKey: ['trades'] });
    },
  });
  const { data: risk } = useQuery({ queryKey: ['portfolio-risk'], queryFn: () => getPortfolioRisk().then(r => r.data), refetchInterval: 10000 });

  const portVal   = portfolio?.portfolio_value ?? 0;
  const pnl       = portfolio?.total_pnl ?? 0;
  const winRate   = portfolio?.win_rate ?? 0;
  const tradesCnt = portfolio?.total_trades ?? 0;
  const hasActivity = tradesCnt > 0;
  const selectedQuote = quotes.find((quote: any) => quote.symbol === chartSymbol);
  const formatPrice = (value?: number) => value ? `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 2 })}` : 'Waiting';
  const exitPosition = async (position: any) => {
    if (!botStatus?.market_open) return;
    if (window.confirm(`Exit ${position.quantity} ${position.symbol} at the current market price?`)) {
      exitMutation.mutate(position);
    }
  };

  return (
    <div className="space-y-4 animate-[fade-in_0.3s_ease]">
      {/* Header */}
      <div>
        <div className="flex items-center justify-between"><h1 className="text-xl font-bold">Dashboard
          <span className="text-text-muted font-normal text-sm ml-2">— Good morning, {username || 'Trader'}</span>
        </h1><button onClick={() => queryClient.invalidateQueries()} title="Refresh dashboard data" className="p-2 rounded-lg border border-white/10 text-text-muted hover:text-brand-blue"><RefreshCw size={15} /></button></div>
        <p className="text-text-muted text-xs mt-0.5">
          NSE · Nifty 50 ·&nbsp;
          {botStatus?.mode === 'paper' ? '📄 Paper Trading Mode' : botStatus?.mode === 'live' ? '🔴 Live Trading' : 'Checking trading mode'}
          {botStatus?.market_open
            ? <span className="text-brand-green ml-1">· Market Open</span>
            : botStatus ? <span className="text-brand-red ml-1">· Market Closed</span> : <span className="text-text-muted ml-1">· Checking market status</span>}
        </p>
      </div>

      <MarketContext status={apiStatus} quotes={quotes} />

      {/* Alert banner */}
      <div className="flex items-center gap-3 px-4 py-2.5 rounded-xl bg-brand-blue/5 border border-brand-blue/20 text-xs">
        <span className="text-brand-blue text-base">●</span>
        <span>{hasActivity ? `${tradesCnt} recorded trades in the current portfolio.` : 'No trades recorded for the current portfolio.'}</span>
        <span className="ml-auto text-text-muted">{botStatus?.market_open ? 'Live session' : 'Market closed'}</span>
      </div>

      <div className="glass-card px-4 py-3 border-brand-gold/20">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 text-sm font-semibold"><span className="text-brand-gold">◷</span> Recent sessions</div>
          <span className="text-[10px] text-text-muted">Stored trading history</span>
        </div>
        {sessionData?.sessions?.length ? <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          {sessionData.sessions.slice(0, 3).map((session: any) => <div key={session.date} className="rounded-lg border border-white/10 bg-white/[0.02] px-3 py-2">
            <div className="flex justify-between text-[11px] font-semibold"><span>{session.date}</span><span className={session.pnl >= 0 ? 'text-brand-green' : 'text-brand-red'}>{session.pnl >= 0 ? '+' : ''}₹{Math.abs(session.pnl).toLocaleString('en-IN')}</span></div>
            <div className="text-[10px] text-text-muted mt-1">{session.trades} trades · {session.win_rate}% win rate</div>
          </div>)}
        </div> : <div className="text-xs text-text-muted animate-pulse">Session history will appear here after the first completed trade.</div>}
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3">
        <StatCard label="Portfolio Value" icon={Wallet} color="green"
          value={`₹${portVal.toLocaleString('en-IN')}`}
          sub={`Capital: ₹${(portfolio?.capital ?? 0).toLocaleString('en-IN')}`} />
        <StatCard label="Today's P&L" icon={TrendingUp} color="gold"
          value={`${pnl >= 0 ? '+' : ''}₹${Math.abs(pnl).toLocaleString('en-IN')}`}
          sub={`${portfolio?.wins ?? 0} wins · ${portfolio?.losses ?? 0} losses`} />
        <StatCard label="Win Rate" icon={Target} color="blue"
          value={`${winRate}%`} sub={`${tradesCnt} total trades`} />
        <StatCard label="AI Trades Today" icon={Bot} color="blue"
          value={tradesCnt} sub="Recorded trades" />
        <StatCard label="Sharpe Ratio" icon={Shield} color="gold"
          value="Waiting" sub="No published metrics" />
      </div>

      <div className="glass-card px-4 py-3 border-brand-blue/20">
        <div className="flex items-center justify-between mb-2"><span className="text-sm font-semibold">Risk overview</span><span className="text-[10px] text-text-muted">Transparent exposure</span></div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-[11px]">
          <div><div className="text-text-muted">Open positions</div><div className="font-mono font-bold mt-1">{risk?.open_positions ?? '—'} / {risk?.max_positions ?? '—'}</div></div>
          <div><div className="text-text-muted">Gross exposure</div><div className="font-mono font-bold mt-1">{risk ? `₹${risk.gross_exposure.toLocaleString('en-IN')}` : 'Waiting'}</div></div>
          <div><div className="text-text-muted">Capital at risk</div><div className="font-mono font-bold text-brand-gold mt-1">{risk ? `₹${risk.capital_at_risk.toLocaleString('en-IN')}` : 'Waiting'}</div></div>
          <div><div className="text-text-muted">Daily loss limit</div><div className="font-mono font-bold mt-1">{risk ? `₹${risk.daily_loss_limit.toLocaleString('en-IN')}` : 'Waiting'}</div></div>
        </div>
      </div>

      <div className="glass-card p-4 border-brand-green/20">
        <div className="flex items-center justify-between gap-3 mb-3">
          <div><div className="flex items-center gap-2 text-sm font-semibold"><ShoppingCart size={15} className="text-brand-green" /> Paper order ticket</div><div className="text-[10px] text-text-muted mt-1">Choose a stock, define protection, and review before submitting.</div></div>
          <span className="text-[10px] text-text-muted text-right">Orders require an open NSE session</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <label className="text-[10px] text-text-muted">Symbol<select value={order.symbol} onChange={event => setOrder({ ...order, symbol: event.target.value })} className="mt-1 w-full bg-black/20 border border-white/10 rounded px-2 py-2 text-xs font-mono text-text-primary">{symbols.map(symbol => <option key={symbol} value={symbol}>{symbol} · NSE</option>)}</select></label>
          <label className="text-[10px] text-text-muted">Quantity<input type="number" min="1" value={order.quantity} onChange={event => setOrder({ ...order, quantity: Math.max(1, Number(event.target.value)) })} className="mt-1 w-full bg-black/20 border border-white/10 rounded px-2 py-2 text-xs font-mono text-text-primary" /></label>
          <label className="text-[10px] text-text-muted">Stop loss (optional)<input type="number" min="0" value={order.stop_loss} onChange={event => setOrder({ ...order, stop_loss: event.target.value })} className="mt-1 w-full bg-black/20 border border-white/10 rounded px-2 py-2 text-xs font-mono text-text-primary" /></label>
          <label className="text-[10px] text-text-muted">Target (optional)<input type="number" min="0" value={order.target_price} onChange={event => setOrder({ ...order, target_price: event.target.value })} className="mt-1 w-full bg-black/20 border border-white/10 rounded px-2 py-2 text-xs font-mono text-text-primary" /></label>
        </div>
        <div className="flex items-center gap-2 mt-3">
          <button disabled={!canTrade || !botStatus?.market_open || orderMutation.isPending || !order.symbol.trim()} onClick={() => window.confirm(`Place paper BUY for ${order.quantity} ${order.symbol}?`) && orderMutation.mutate('buy')} className="px-4 py-2 rounded-lg bg-brand-green/15 border border-brand-green/30 text-brand-green text-xs font-bold disabled:opacity-40">BUY</button>
          <button disabled={!canTrade || !botStatus?.market_open || orderMutation.isPending || !order.symbol.trim()} onClick={() => window.confirm(`Place paper SELL for ${order.quantity} ${order.symbol}?`) && orderMutation.mutate('sell')} className="px-4 py-2 rounded-lg bg-brand-red/15 border border-brand-red/30 text-brand-red text-xs font-bold disabled:opacity-40">SELL</button>
          {!canTrade ? <span className="text-[10px] text-text-muted">Viewer access: trading controls are disabled.</span> : !botStatus?.market_open && <span className="text-[10px] text-text-muted">Market closed: orders will be enabled at 09:15 IST.</span>}
          {orderMutation.isError && <span className="text-[10px] text-brand-red">Order failed. Check position, quantity, and market status.</span>}
          {orderMutation.isSuccess && <span className="text-[10px] text-brand-green">Paper order accepted.</span>}
        </div>
      </div>

      {/* Main 2-column grid */}
      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_320px] gap-4">
        {/* Candlestick chart card */}
        <div className="glass-card overflow-hidden">
          <div className="px-4 py-3 border-b border-[var(--border)] flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <span className="w-6 h-6 rounded bg-brand-blue/10 flex items-center justify-center"><TrendingUp size={12} className="text-brand-blue" /></span>
              <select value={chartSymbol} onChange={event => setChartSymbol(event.target.value)} className="bg-transparent text-sm font-semibold text-text-primary outline-none"><option value="RELIANCE">Reliance Industries (RELIANCE) · NSE</option>{symbols.filter(symbol => symbol !== 'RELIANCE').map(symbol => <option key={symbol} value={symbol}>{({ TCS: 'Tata Consultancy Services', HDFCBANK: 'HDFC Bank', INFY: 'Infosys', WIPRO: 'Wipro', ICICIBANK: 'ICICI Bank', BAJFINANCE: 'Bajaj Finance', SBIN: 'State Bank of India', ITC: 'ITC', KOTAKBANK: 'Kotak Mahindra Bank' } as Record<string, string>)[symbol] || symbol} ({symbol}) · NSE</option>)}</select>
            </div>
            <div className="flex gap-1">
              {(['candles', 'line', 'area'] as ChartView[]).map((type) => (
                <button key={type} onClick={() => setChartView(type)} className={clsx('px-2.5 py-1 rounded text-[11px] font-semibold capitalize', chartView === type ? 'bg-brand-blue/15 text-brand-blue border border-brand-blue/25' : 'text-text-muted hover:text-text-primary')}>
                  {type}
                </button>
              ))}
            </div>
            <div className="flex gap-1">
              {['1m','5m','15m','1H','1D'].map((t) => (
                <button key={t} onClick={() => setInterval(t === '1H' ? '1h' : t === '1D' ? '1d' : t)} className={clsx('px-2.5 py-1 rounded text-[11px] font-semibold',
                  interval === (t === '1H' ? '1h' : t === '1D' ? '1d' : t) ? 'bg-brand-blue/15 text-brand-blue border border-brand-blue/25' : 'text-text-muted hover:text-text-primary'
                )}>{t}</button>
              ))}
            </div>
          </div>
          {/* Chart stats bar */}
          <div className="flex gap-6 px-4 py-2.5 border-b border-[var(--border)] flex-wrap">
            {[
              { l: 'Open', v: quotesError ? 'Unavailable' : formatPrice(selectedQuote?.open) },
              { l: 'High', v: quotesError ? 'Unavailable' : formatPrice(selectedQuote?.high), c: 'text-brand-green' },
              { l: 'Low',  v: quotesError ? 'Unavailable' : formatPrice(selectedQuote?.low), c: 'text-brand-red' },
              { l: 'LTP',  v: quotesError ? 'Unavailable' : formatPrice(selectedQuote?.ltp), c: 'text-brand-blue' },
              { l: 'Volume', v: quotesError ? 'Unavailable' : selectedQuote?.volume ? selectedQuote.volume.toLocaleString('en-IN') : 'Waiting' },
              { l: 'Change', v: quotesError ? 'Unavailable' : selectedQuote ? `${selectedQuote.change_pct >= 0 ? '+' : ''}${selectedQuote.change_pct}%` : 'Waiting', c: selectedQuote?.change_pct >= 0 ? 'text-brand-green' : 'text-brand-red' },
            ].map(s => (
              <div key={s.l}>
                <div className="text-[9px] uppercase tracking-wider text-text-muted">{s.l}</div>
                <div className={clsx('text-[13px] font-bold font-mono', s.c || 'text-text-primary')}>{s.v}</div>
              </div>
            ))}
          </div>
          {/* Indicator tags */}
          <div className="flex gap-2 px-4 py-2 flex-wrap border-b border-[var(--border)]">
            {[
              { l: `Change: ${selectedQuote ? `${selectedQuote.change_pct}%` : 'Waiting'}`, c: 'text-brand-blue bg-brand-blue/10 border-brand-blue/20' },
              { l: `Close: ${formatPrice(selectedQuote?.close)}`, c: 'text-brand-gold bg-brand-gold/10 border-brand-gold/20' },
              { l: `${selectedQuote?.data_status === 'live' ? 'Live' : 'Last available'}: ${selectedQuote ? new Date(selectedQuote.timestamp).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) : 'Waiting'}`, c: selectedQuote?.data_status === 'live' ? 'text-brand-green bg-brand-green/10 border-brand-green/20' : 'text-brand-gold bg-brand-gold/10 border-brand-gold/20' },
            ].map(t => (
              <span key={t.l} className={clsx('text-[10px] font-mono font-semibold px-2 py-0.5 rounded border', t.c)}>{t.l}</span>
            ))}
          </div>
          <div className="px-4 py-2 border-b border-[var(--border)] flex items-center gap-3 text-[10px] text-text-muted">
            <span className="font-semibold text-text-secondary">{chartView === 'candles' ? 'Price + volume' : chartView === 'line' ? 'Closing price' : 'Closing price area'}</span>
            {chartView === 'candles' && <><span className="text-brand-gold">EMA trend</span><span className="text-text-muted">Drag to pan · scroll to zoom</span></>}
          </div>
          <div className="p-2"><CandleChart symbol={chartSymbol} interval={interval} view={chartView} /></div>
        </div>

        {/* Right column */}
        <div className="flex flex-col gap-4">
          <AIPredictions marketOpen={Boolean(botStatus?.market_open)} />
          <ModelMetrics />
        </div>
      </div>

      {/* Bottom 3-column grid */}
      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_320px] gap-4">
        {/* Open Positions */}
        <div className="glass-card overflow-hidden">
          <div className="px-4 py-3 border-b border-[var(--border)] flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <span className="w-6 h-6 rounded bg-brand-green/10 flex items-center justify-center"><TrendingUp size={12} className="text-brand-green" /></span>
              Open Positions
            </div>
            <span className="text-xs bg-brand-green/10 text-brand-green px-2 py-0.5 rounded-full border border-brand-green/20">
              {positions?.length ?? 0} Active
            </span>
          </div>
          <table className="w-full text-[11px]">
            <thead>
              <tr className="text-text-muted text-[9px] uppercase tracking-wider">
                {['Stock','Qty','Entry','LTP','P&L','Action'].map(h => (
                  <th key={h} className="text-left px-4 py-2 border-b border-[var(--border)] font-semibold">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(positions?.length ? positions : []).map((p: any, i: number) => (
                <tr key={i} className="hover:bg-brand-blue/3 transition-colors">
                  <td className="px-4 py-3 font-mono font-bold">{p.symbol}</td>
                  <td className="px-4 py-3 font-mono">{p.quantity}</td>
                  <td className="px-4 py-3 font-mono">₹{p.avg_price}</td>
                  <td className="px-4 py-3 font-mono text-brand-blue">₹{p.current_price}</td>
                  <td className={clsx('px-4 py-3 font-mono font-bold', p.pnl >= 0 ? 'text-brand-green' : 'text-brand-red')}>
                    {p.pnl >= 0 ? '+' : ''}₹{Math.abs(p.pnl)}
                  </td>
                  <td className="px-4 py-3">
                    <button disabled={!botStatus?.market_open || exitMutation.isPending} onClick={() => exitPosition(p)} title={botStatus?.market_open ? 'Close paper position' : 'Market closed'} className="text-[9px] px-2 py-0.5 rounded border border-brand-red/30 text-brand-red bg-brand-red/10 font-bold hover:bg-brand-red/20 disabled:opacity-40">{exitMutation.isPending ? '...' : 'Exit'}</button>
                  </td>
                </tr>
              ))}
              {!positions?.length && <tr><td colSpan={6} className="px-4 py-8 text-center text-xs text-text-muted">No open positions.</td></tr>}
            </tbody>
          </table>
        </div>

        {/* Portfolio chart */}
        <div className="glass-card overflow-hidden">
          <div className="px-4 py-3 border-b border-[var(--border)] flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <span className="w-6 h-6 rounded bg-brand-blue/10 flex items-center justify-center"><RefreshCw size={12} className="text-brand-blue" /></span>
              Portfolio Today
            </div>
            <div className="flex gap-1">
              {['Today','1W','1M'].map((t) => {
                const period = t === 'Today' ? 'today' : t === '1W' ? 'week' : 'month';
                return <button key={t} onClick={() => setPnlPeriod(period)} className={clsx('px-2 py-0.5 rounded text-[10px] font-semibold',
                  pnlPeriod === period ? 'bg-brand-blue/15 text-brand-blue border border-brand-blue/25' : 'text-text-muted'
                )}>{t}</button>
              })}
            </div>
          </div>
          <div className="p-4">
            <PortfolioSparkline points={pnlChart?.data ?? []} portfolioValue={portVal} pnl={pnl} />
          </div>
        </div>

        {/* Live feed */}
        <LiveFeed trades={trades} />
      </div>
    </div>
  );
}

// ── Portfolio sparkline (CSS-drawn gradient chart) ────────────────────────────
function PortfolioSparkline({ points, portfolioValue, pnl }: { points: any[]; portfolioValue: number; pnl: number }) {
  const pts = points.length ? points.map(point => point.value) : [0];
  const min = Math.min(...pts); const max = Math.max(...pts); const range = max - min || 1;
  const h = 160; const w = 100;
  const poly = pts.map((v,i) => `${pts.length === 1 ? w / 2 : (i/(pts.length-1))*w},${h - ((v-min)/range)*h}`).join(' ');
  return (
    <div>
      <div className="text-2xl font-black font-mono text-brand-green mb-1">₹{portfolioValue.toLocaleString('en-IN')}</div>
      <div className={clsx('text-xs mb-3', pnl >= 0 ? 'text-brand-green' : 'text-brand-red')}>{pnl >= 0 ? '+' : '-'}₹{Math.abs(pnl).toLocaleString('en-IN')} today</div>
      {points.length ? <svg viewBox={`0 0 100 ${h}`} className="w-full" style={{height:160}} preserveAspectRatio="none">
        <defs>
          <linearGradient id="pg" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#00d4ff" stopOpacity="0.3"/>
            <stop offset="100%" stopColor="#00d4ff" stopOpacity="0"/>
          </linearGradient>
        </defs>
        <polygon points={`0,${h} ${poly} ${w},${h}`} fill="url(#pg)"/>
        <polyline points={poly} fill="none" stroke="#00d4ff" strokeWidth="1.5"/>
      </svg> : <div className="h-[160px] flex items-center justify-center text-xs text-text-muted animate-pulse">Portfolio history will animate here after the first recorded trade.</div>}
      <div className="flex justify-between text-[9px] text-text-muted mt-1">
        <span>9:15</span><span>11:00</span><span>13:00</span><span>15:30</span>
      </div>
    </div>
  );
}
