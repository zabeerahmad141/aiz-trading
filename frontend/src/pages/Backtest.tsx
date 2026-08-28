import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { BarChart3, Play } from 'lucide-react';
import { runBacktest } from '@/lib/api';

const sample = `close,high,low,signal
100,101,99,BUY
101,102,100,HOLD
104,105,103,SELL`;

function parseCandles(text: string) {
  const rows = text.trim().split(/\r?\n/).slice(1);
  if (!rows.length || rows.some(row => row.split(',').slice(0, 3).some(value => !Number.isFinite(Number(value))))) {
    throw new Error('Use a CSV header followed by numeric close, high, and low values.');
  }
  return rows.map(row => { const [close, high, low, signal = 'HOLD'] = row.split(','); return { close: Number(close), high: Number(high), low: Number(low), signal: signal.trim().toUpperCase() }; });
}

export default function Backtest() {
  const [csv, setCsv] = useState(sample);
  const [settings, setSettings] = useState({ initial_capital: 100000, risk_per_trade_pct: 1, stop_loss_pct: 1.5, target_pct: 3, commission_pct: 0.1 });
  const mutation = useMutation({ mutationFn: (data: object) => runBacktest(data).then(response => response.data) });
  const [inputError, setInputError] = useState<string | null>(null);
  const run = () => {
    try {
      setInputError(null);
      mutation.mutate({ candles: parseCandles(csv), ...settings });
    } catch (error) {
      setInputError(error instanceof Error ? error.message : 'Invalid candle data.');
    }
  };
  const result = mutation.data;
  return <div className="space-y-4 animate-[fade-in_0.3s_ease]">
    <div><h1 className="text-xl font-bold flex items-center gap-2"><BarChart3 size={20} className="text-brand-gold" /> Backtest</h1><p className="text-xs text-text-muted mt-1">Historical simulation with explicit risk, target, and commission assumptions.</p></div>
    <div className="glass-card p-4"><label className="text-xs text-text-secondary">Candle data: close, high, low, signal</label><textarea value={csv} onChange={event => setCsv(event.target.value)} className="mt-2 w-full h-36 bg-black/20 border border-white/10 rounded-lg p-3 text-xs font-mono text-text-primary" /><div className="grid grid-cols-2 md:grid-cols-5 gap-2 mt-3">{Object.entries(settings).map(([key, value]) => <label key={key} className="text-[10px] text-text-muted capitalize">{key.replace(/_/g, ' ')}<input type="number" value={value} min="0" step="0.1" onChange={event => setSettings({ ...settings, [key]: Number(event.target.value) })} className="mt-1 w-full bg-black/20 border border-white/10 rounded px-2 py-1.5 text-xs text-text-primary" /></label>)}</div><button onClick={run} disabled={mutation.isPending} className="mt-3 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-blue/15 border border-brand-blue/30 text-brand-blue text-xs font-semibold"><Play size={13} />{mutation.isPending ? 'Running...' : 'Run simulation'}</button>{inputError && <p className="text-xs text-brand-red mt-2">{inputError}</p>}{mutation.isError && <p className="text-xs text-brand-red mt-2">Backtest request failed. Check authentication, service health, and candle values.</p>}</div>
    {result && <div className="grid grid-cols-2 md:grid-cols-5 gap-3">{[['Return', `${result.total_return_pct}%`], ['Trades', result.total_trades], ['Win rate', `${result.win_rate_pct}%`], ['Drawdown', `${result.max_drawdown_pct}%`], ['Expectancy', `₹${result.expectancy}`]].map(([label, value]) => <div key={label} className="glass-card p-4"><div className="text-[10px] uppercase tracking-wider text-text-muted">{label}</div><div className="text-xl font-mono font-bold text-brand-blue mt-2">{value}</div></div>)}</div>}
    {result && <div className="glass-card overflow-hidden"><div className="px-4 py-3 border-b border-[var(--border)] text-sm font-semibold">Simulated trades</div>{result.trades.map((trade: any, index: number) => <div key={index} className="px-4 py-3 flex justify-between text-xs border-b border-white/[0.04]"><span>{trade.entry_index} · {trade.quantity} units @ ₹{trade.entry_price}</span><span className={trade.pnl >= 0 ? 'text-brand-green' : 'text-brand-red'}>{trade.reason} · {trade.pnl >= 0 ? '+' : ''}₹{trade.pnl}</span></div>)}</div>}
  </div>;
}
