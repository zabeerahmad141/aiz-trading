import { useQuery } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';
import {
  getPortfolioSummary, getBotStatus, getOpenPositions,
  getTradeHistory, getOHLCV, getQuotes, getPnLChart,
} from '@/lib/api';
import { Wallet, TrendingUp, Target, Bot, Shield, Brain, Zap, RefreshCw } from 'lucide-react';
import clsx from 'clsx';
// @ts-ignore
import { createChart, ColorType, CrosshairMode } from 'lightweight-charts';

// ── Candlestick chart component — fetches real data from backend ────────────
function CandleChart({ symbol = 'RELIANCE' }: { symbol?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const { data: ohlcvData } = useQuery({
    queryKey: ['ohlcv', symbol],
    queryFn: () => getOHLCV(symbol, '1d', '5m').then(r => r.data),
    refetchInterval: 60000,
    retry: 1,
  });

  useEffect(() => {
    if (!ref.current) return;
    const chart = createChart(ref.current, {
      width: ref.current.clientWidth,
      height: 300,
      layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: '#7a8fa6' },
      grid: { vertLines: { color: 'rgba(255,255,255,0.04)' }, horzLines: { color: 'rgba(255,255,255,0.04)' } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: 'rgba(0,212,255,0.12)' },
      timeScale: { borderColor: 'rgba(0,212,255,0.12)', timeVisible: true },
    });
    const series = chart.addCandlestickSeries({
      upColor: '#00e676', downColor: '#ff3d71',
      borderUpColor: '#00e676', borderDownColor: '#ff3d71',
      wickUpColor: 'rgba(0,230,118,0.5)', wickDownColor: 'rgba(255,61,113,0.5)',
    });
    const emaLine = chart.addLineSeries({ color: 'rgba(0,212,255,0.7)', lineWidth: 1, priceLineVisible: false });

    // Keep the chart empty when the provider has no data, such as after market close.
    const candles = ohlcvData?.candles;
    const data: any[] = candles && candles.length > 5 ? candles : [];
    if (!data.length) return () => chart.remove();
    series.setData(data);

    // EMA overlay
    let emaVal = data[0]?.close || 2820;
    const emaData = data.map(d => { emaVal = emaVal * 0.9 + d.close * 0.1; return { time: d.time, value: +emaVal.toFixed(2) }; });
    emaLine.setData(emaData);

    // Live tick update (for real last candle)
    const ro = new ResizeObserver(() => { if (ref.current) chart.applyOptions({ width: ref.current.clientWidth }); });
    ro.observe(ref.current);
    return () => { chart.remove(); ro.disconnect(); };
  }, [ohlcvData]);

  return <div ref={ref} className={!ohlcvData?.candles?.length ? 'h-[300px] flex items-center justify-center text-xs text-text-muted' : undefined}>{!ohlcvData?.candles?.length && 'No market data available while the market is closed.'}</div>;
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
        <div className="relative mx-auto mb-3 w-14 h-14 rounded-full border border-brand-blue/30 flex items-center justify-center">
          <span className="absolute inset-0 rounded-full border border-brand-blue/20 animate-ping" />
          <Brain size={18} className="text-brand-blue" />
        </div>
        <div className="text-text-secondary">{marketOpen ? 'Waiting for the next model signal.' : 'The model is resting between sessions.'}</div>
        <div className="mt-1 text-[10px]">Live predictions will appear automatically when signals are published.</div>
      </div>
    </div>
  );
}

// ── Model metrics ────────────────────────────────────────────────────────────
function ModelMetrics() {
  const rows = [
    { label: 'Accuracy', value: 'Unavailable', color: 'text-text-muted' },
    { label: 'Sharpe Ratio', value: 'Unavailable', color: 'text-text-muted' },
    { label: 'Max Drawdown', value: 'Unavailable', color: 'text-text-muted' },
    { label: 'Training data', value: 'Not published', color: 'text-text-muted' },
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
  const { data: portfolio } = useQuery({ queryKey: ['portfolio'], queryFn: () => getPortfolioSummary().then(r => r.data), refetchInterval: 10000 });
  const { data: botStatus } = useQuery({ queryKey: ['botStatus'], queryFn: () => getBotStatus().then(r => r.data), refetchInterval: 5000 });
  const { data: positions } = useQuery({ queryKey: ['positions'], queryFn: () => getOpenPositions().then(r => r.data), refetchInterval: 5000 });
  const { data: trades } = useQuery({ queryKey: ['trades'], queryFn: () => getTradeHistory().then(r => r.data) });
  const { data: quotes = [] } = useQuery({ queryKey: ['quotes'], queryFn: () => getQuotes().then(r => r.data), refetchInterval: 30000 });
  const { data: pnlChart } = useQuery({ queryKey: ['pnl-chart', 'today'], queryFn: () => getPnLChart('today').then(r => r.data), refetchInterval: 30000 });

  const portVal   = portfolio?.portfolio_value ?? 0;
  const pnl       = portfolio?.total_pnl ?? 0;
  const winRate   = portfolio?.win_rate ?? 0;
  const tradesCnt = portfolio?.total_trades ?? 0;
  const hasActivity = tradesCnt > 0;
  const reliance = quotes.find((quote: any) => quote.symbol === 'RELIANCE');
  const formatPrice = (value?: number) => value ? `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 2 })}` : 'N/A';

  return (
    <div className="space-y-4 animate-[fade-in_0.3s_ease]">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold">Dashboard
          <span className="text-text-muted font-normal text-sm ml-2">— Good morning, Admin</span>
        </h1>
        <p className="text-text-muted text-xs mt-0.5">
          NSE · Nifty 50 ·&nbsp;
          {botStatus?.mode === 'paper' ? '📄 Paper Trading Mode' : '🔴 Live Trading'}
          {botStatus?.market_open
            ? <span className="text-brand-green ml-1">· Market Open</span>
            : <span className="text-brand-red ml-1">· Market Closed</span>}
        </p>
      </div>

      {/* Alert banner */}
      <div className="flex items-center gap-3 px-4 py-2.5 rounded-xl bg-brand-blue/5 border border-brand-blue/20 text-xs">
        <span className="text-brand-blue text-base">●</span>
        <span>{hasActivity ? `${tradesCnt} recorded trades in the current portfolio.` : 'No trades recorded for the current portfolio.'}</span>
        <span className="ml-auto text-text-muted">{botStatus?.market_open ? 'Live session' : 'Market closed'}</span>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-5 gap-3">
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
          value="N/A" sub="No published metrics" />
      </div>

      {/* Main 2-column grid */}
      <div className="grid grid-cols-[1fr_320px] gap-4">
        {/* Candlestick chart card */}
        <div className="glass-card overflow-hidden">
          <div className="px-4 py-3 border-b border-[var(--border)] flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <span className="w-6 h-6 rounded bg-brand-blue/10 flex items-center justify-center"><TrendingUp size={12} className="text-brand-blue" /></span>
              RELIANCE · NSE
            </div>
            <div className="flex gap-1">
              {['1m','5m','15m','1H','1D'].map((t,i) => (
                <button key={t} className={clsx('px-2.5 py-1 rounded text-[11px] font-semibold',
                  i === 0 ? 'bg-brand-blue/15 text-brand-blue border border-brand-blue/25' : 'text-text-muted hover:text-text-primary'
                )}>{t}</button>
              ))}
            </div>
          </div>
          {/* Chart stats bar */}
          <div className="flex gap-6 px-4 py-2.5 border-b border-[var(--border)] flex-wrap">
            {[
              { l: 'Open', v: formatPrice(reliance?.open) },
              { l: 'High', v: formatPrice(reliance?.high), c: 'text-brand-green' },
              { l: 'Low',  v: formatPrice(reliance?.low), c: 'text-brand-red' },
              { l: 'LTP',  v: formatPrice(reliance?.ltp), c: 'text-brand-blue' },
              { l: 'Volume', v: reliance?.volume ? reliance.volume.toLocaleString('en-IN') : 'N/A' },
              { l: 'Change', v: reliance ? `${reliance.change_pct >= 0 ? '+' : ''}${reliance.change_pct}%` : 'N/A', c: reliance?.change_pct >= 0 ? 'text-brand-green' : 'text-brand-red' },
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
              { l: `Change: ${reliance ? `${reliance.change_pct}%` : 'N/A'}`, c: 'text-brand-blue bg-brand-blue/10 border-brand-blue/20' },
              { l: `Close: ${formatPrice(reliance?.close)}`, c: 'text-brand-gold bg-brand-gold/10 border-brand-gold/20' },
              { l: `Updated: ${reliance ? new Date(reliance.timestamp).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) : 'N/A'}`, c: 'text-brand-green bg-brand-green/10 border-brand-green/20' },
            ].map(t => (
              <span key={t.l} className={clsx('text-[10px] font-mono font-semibold px-2 py-0.5 rounded border', t.c)}>{t.l}</span>
            ))}
          </div>
          <div className="p-2"><CandleChart /></div>
        </div>

        {/* Right column */}
        <div className="flex flex-col gap-4">
          <AIPredictions marketOpen={Boolean(botStatus?.market_open)} />
          <ModelMetrics />
        </div>
      </div>

      {/* Bottom 3-column grid */}
      <div className="grid grid-cols-[1fr_1fr_320px] gap-4">
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
                    <button className="text-[9px] px-2 py-0.5 rounded border border-brand-red/30 text-brand-red bg-brand-red/10 font-bold hover:bg-brand-red/20">Exit</button>
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
              {['Today','1W','1M'].map((t,i) => (
                <button key={t} className={clsx('px-2 py-0.5 rounded text-[10px] font-semibold',
                  i === 0 ? 'bg-brand-blue/15 text-brand-blue border border-brand-blue/25' : 'text-text-muted'
                )}>{t}</button>
              ))}
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
