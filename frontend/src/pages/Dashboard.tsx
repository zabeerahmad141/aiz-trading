import { useQuery } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';
import { getPortfolioSummary, getBotStatus, getOpenPositions, getTradeHistory } from '@/lib/api';
import { Wallet, TrendingUp, Target, Bot, Shield, Brain, Zap, RefreshCw } from 'lucide-react';
import clsx from 'clsx';
// @ts-ignore
import { createChart, ColorType, CrosshairMode } from 'lightweight-charts';

// ── Candlestick chart component ─────────────────────────────────────────────
function CandleChart() {
  const ref = useRef<HTMLDivElement>(null);
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
    const ema = chart.addLineSeries({ color: 'rgba(0,212,255,0.7)', lineWidth: 1, priceLineVisible: false });
    // Generate realistic-looking candle data
    const now = Math.floor(Date.now() / 1000);
    let close = 2820; const data: any[] = []; const emaData: any[] = []; let emaVal = 2820;
    for (let i = 180; i >= 0; i--) {
      const t = now - i * 60;
      const o = close;
      close = Math.max(2780, Math.min(2880, o + (Math.random() - 0.46) * 8));
      const h = Math.max(o, close) + Math.random() * 4;
      const l = Math.min(o, close) - Math.random() * 4;
      data.push({ time: t, open: +o.toFixed(2), high: +h.toFixed(2), low: +l.toFixed(2), close: +close.toFixed(2) });
      emaVal = emaVal * 0.9 + close * 0.1;
      emaData.push({ time: t, value: +emaVal.toFixed(2) });
    }
    series.setData(data);
    ema.setData(emaData);
    // Live update every 1.5s
    let last = data[data.length - 1];
    const iv = setInterval(() => {
      const nc = Math.max(2780, Math.min(2880, last.close + (Math.random() - 0.46) * 3));
      last = { time: Math.floor(Date.now() / 1000), open: last.open, high: Math.max(last.high, nc), low: Math.min(last.low, nc), close: +nc.toFixed(2) };
      series.update(last);
    }, 1500);
    const ro = new ResizeObserver(() => chart.applyOptions({ width: ref.current!.clientWidth }));
    ro.observe(ref.current);
    return () => { clearInterval(iv); chart.remove(); ro.disconnect(); };
  }, []);
  return <div ref={ref} />;
}

// ── AI Predictions panel ─────────────────────────────────────────────────────
const AI_PREDS = [
  { stock: 'RELIANCE', signal: 'buy',  conf: 82, target: '₹2,870' },
  { stock: 'HDFCBANK', signal: 'buy',  conf: 76, target: '₹1,695' },
  { stock: 'INFY',     signal: 'sell', conf: 68, target: '₹1,790' },
  { stock: 'WIPRO',    signal: 'hold', conf: 55, target: '₹452'   },
  { stock: 'TCS',      signal: 'buy',  conf: 71, target: '₹3,460' },
];
function AIPredictions() {
  return (
    <div className="glass-card">
      <div className="px-4 py-3 border-b border-[var(--border)] flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <span className="w-6 h-6 rounded bg-brand-gold/10 flex items-center justify-center"><Brain size={12} className="text-brand-gold" /></span>
          AI Predictions
        </div>
        <span className="text-[10px] text-text-muted">Next 30 min</span>
      </div>
      <div className="px-4 py-2 divide-y divide-white/[0.04]">
        {AI_PREDS.map(p => (
          <div key={p.stock} className="flex items-center gap-3 py-2.5">
            <span className="w-[68px] font-mono text-[12px] font-bold text-text-primary">{p.stock}</span>
            <span className={clsx('text-[10px] font-bold px-2 py-0.5 rounded-full border',
              p.signal === 'buy'  ? 'bg-brand-green/10 text-brand-green border-brand-green/30' :
              p.signal === 'sell' ? 'bg-brand-red/10 text-brand-red border-brand-red/30' :
                                    'bg-white/5 text-text-secondary border-white/10'
            )}>{p.signal.toUpperCase()}</span>
            <div className="flex-1">
              <div className="flex justify-between text-[9px] text-text-muted mb-1">
                <span>Confidence</span><span>{p.conf}%</span>
              </div>
              <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                <div className={clsx('h-full rounded-full', p.signal === 'buy' ? 'bg-brand-green' : p.signal === 'sell' ? 'bg-brand-red' : 'bg-text-muted')}
                  style={{ width: `${p.conf}%` }} />
              </div>
            </div>
            <span className="text-[11px] font-mono text-text-muted w-14 text-right">{p.target}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Model metrics ────────────────────────────────────────────────────────────
function ModelMetrics() {
  const rows = [
    { label: 'Accuracy',     value: '74.3%',          color: 'text-brand-green' },
    { label: 'Sharpe Ratio', value: '2.41',            color: 'text-brand-gold'  },
    { label: 'Max Drawdown', value: '-3.2%',           color: 'text-brand-red'   },
    { label: 'Trained On',   value: '3Y data',         color: 'text-brand-blue'  },
    { label: 'Model',        value: 'XGBoost v2+LSTM', color: 'text-text-secondary text-[11px]' },
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
const FEED = [
  { type: 'buy',  title: 'BUY RELIANCE × 5', sub: 'AI Signal: RSI Breakout · Conf 82%', pnl: '+₹185', time: '09:42' },
  { type: 'ai',   title: 'Model retrained',   sub: 'XGBoost v2 · Accuracy: 74.3%',       pnl: '',      time: '09:35' },
  { type: 'sell', title: 'SELL INFY × 3',     sub: 'Target hit · Stop loss avoided',      pnl: '+₹210', time: '09:28' },
  { type: 'buy',  title: 'BUY TCS × 2',       sub: 'AI Signal: MACD Cross · Conf 71%',   pnl: '+₹62',  time: '09:19' },
  { type: 'sell', title: 'SELL WIPRO × 6',    sub: 'Trailing stop triggered',             pnl: '-₹48',  time: '09:15' },
];
function LiveFeed({ trades }: { trades?: any[] }) {
  const items = trades && trades.length > 0 ? trades.slice(0, 5).map(t => ({
    type: t.action,
    title: `${t.action.toUpperCase()} ${t.symbol} × ${t.quantity}`,
    sub: t.ai_reason || (t.ai_signal ? `AI Signal · Conf ${t.ai_confidence}%` : 'Manual trade'),
    pnl: t.pnl != null ? `${t.pnl >= 0 ? '+' : ''}₹${Math.abs(t.pnl).toFixed(0)}` : '',
    time: new Date(t.entered_at).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', hour12: false }),
  })) : FEED;

  return (
    <div className="glass-card flex flex-col">
      <div className="px-4 py-3 border-b border-[var(--border)] flex items-center gap-2 text-sm font-semibold">
        <span className="w-6 h-6 rounded bg-brand-blue/10 flex items-center justify-center"><Zap size={12} className="text-brand-blue" /></span>
        Live Activity
        <div className="ml-auto w-1.5 h-1.5 rounded-full bg-brand-green animate-pulse" />
      </div>
      <div className="px-3 py-2 space-y-2 overflow-y-auto max-h-64">
        {items.map((f, i) => (
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
        ))}
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

  const portVal   = portfolio?.portfolio_value || 124350;
  const pnl       = portfolio?.total_pnl ?? 2980;
  const winRate   = portfolio?.win_rate ?? 74.3;
  const tradesCnt = portfolio?.total_trades ?? 12;

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
      <div className="flex items-center gap-3 px-4 py-2.5 rounded-xl bg-brand-green/5 border border-brand-green/20 text-xs">
        <span className="text-brand-green text-base">✓</span>
        <span>AI Engine executed <strong>3 BUY signals</strong> in last 15 minutes — RELIANCE, TCS, HDFCBANK ·
          Total deployed: <strong className="text-brand-gold">₹47,250</strong></span>
        <span className="ml-auto text-text-muted">09:39 IST</span>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-5 gap-3">
        <StatCard label="Portfolio Value" icon={Wallet} color="green"
          value={`₹${portVal.toLocaleString('en-IN')}`}
          sub={`Capital: ₹${(portfolio?.capital || 100000).toLocaleString('en-IN')}`} />
        <StatCard label="Today's P&L" icon={TrendingUp} color="gold"
          value={`${pnl >= 0 ? '+' : ''}₹${Math.abs(pnl).toLocaleString('en-IN')}`}
          sub={`${portfolio?.wins ?? 9} wins · ${portfolio?.losses ?? 3} losses`} />
        <StatCard label="Win Rate" icon={Target} color="blue"
          value={`${winRate}%`} sub={`${tradesCnt} total trades`} />
        <StatCard label="AI Trades Today" icon={Bot} color="blue"
          value={tradesCnt} sub="Auto-executed by AI" />
        <StatCard label="Sharpe Ratio" icon={Shield} color="gold"
          value="2.41" sub="Max drawdown: 3.2%" />
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
              { l: 'Open', v: '₹2,810.50' },
              { l: 'High', v: '₹2,861.25', c: 'text-brand-green' },
              { l: 'Low',  v: '₹2,798.30', c: 'text-brand-red' },
              { l: 'LTP',  v: '₹2,847.60', c: 'text-brand-blue' },
              { l: 'Volume', v: '18.4L' },
              { l: 'AI Signal', v: '▲ BUY', c: 'text-brand-green' },
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
              { l: 'EMA 9: 2,839', c: 'text-brand-blue bg-brand-blue/10 border-brand-blue/20' },
              { l: 'EMA 21: 2,821', c: 'text-brand-gold bg-brand-gold/10 border-brand-gold/20' },
              { l: 'RSI: 62.4', c: 'text-brand-green bg-brand-green/10 border-brand-green/20' },
              { l: 'MACD: +4.2', c: 'text-brand-blue bg-brand-blue/10 border-brand-blue/20' },
              { l: 'BB Upper: 2,870', c: 'text-brand-gold bg-brand-gold/10 border-brand-gold/20' },
              { l: 'Stoch: 74.1', c: 'text-brand-red bg-brand-red/10 border-brand-red/20' },
            ].map(t => (
              <span key={t.l} className={clsx('text-[10px] font-mono font-semibold px-2 py-0.5 rounded border', t.c)}>{t.l}</span>
            ))}
          </div>
          <div className="p-2"><CandleChart /></div>
        </div>

        {/* Right column */}
        <div className="flex flex-col gap-4">
          <AIPredictions />
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
              {positions?.length ?? 3} Active
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
              {(positions?.length ? positions : [
                { symbol:'RELIANCE', quantity:5, avg_price:2810, current_price:2847, pnl:185,  is_paper:true },
                { symbol:'TCS',      quantity:2, avg_price:3390, current_price:3421, pnl:62,   is_paper:true },
                { symbol:'HDFCBANK', quantity:8, avg_price:1690, current_price:1672, pnl:-144, is_paper:true },
              ]).map((p: any, i: number) => (
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
            <PortfolioSparkline />
          </div>
        </div>

        {/* Live feed */}
        <LiveFeed trades={trades} />
      </div>
    </div>
  );
}

// ── Portfolio sparkline (CSS-drawn gradient chart) ────────────────────────────
function PortfolioSparkline() {
  const pts = [121370,121800,122100,121900,122400,122900,123100,122800,123400,123900,124100,123800,124350];
  const min = Math.min(...pts); const max = Math.max(...pts);
  const h = 160; const w = 100;
  const poly = pts.map((v,i) => `${(i/(pts.length-1))*w},${h - ((v-min)/(max-min))*h}`).join(' ');
  return (
    <div>
      <div className="text-2xl font-black font-mono text-brand-green mb-1">₹1,24,350</div>
      <div className="text-xs text-brand-green mb-3">▲ +₹2,980 today (+2.45%)</div>
      <svg viewBox={`0 0 100 ${h}`} className="w-full" style={{height:160}} preserveAspectRatio="none">
        <defs>
          <linearGradient id="pg" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#00d4ff" stopOpacity="0.3"/>
            <stop offset="100%" stopColor="#00d4ff" stopOpacity="0"/>
          </linearGradient>
        </defs>
        <polygon points={`0,${h} ${poly} ${w},${h}`} fill="url(#pg)"/>
        <polyline points={poly} fill="none" stroke="#00d4ff" strokeWidth="1.5"/>
      </svg>
      <div className="flex justify-between text-[9px] text-text-muted mt-1">
        <span>9:15</span><span>11:00</span><span>13:00</span><span>15:30</span>
      </div>
    </div>
  );
}
