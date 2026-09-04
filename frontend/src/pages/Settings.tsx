import { useQuery } from '@tanstack/react-query';
import { getBotStatus } from '@/lib/api';
import clsx from 'clsx';
import { Settings as SettingsIcon, CheckCircle, AlertCircle } from 'lucide-react';

export default function Settings() {
  const { data: status } = useQuery({
    queryKey: ['botStatus'],
    queryFn: () => getBotStatus().then(r => r.data),
    refetchInterval: 10000,
  });

  const config = [
    { section: 'Broker', items: [
      { label: 'Execution Broker', value: status?.broker || 'paper', highlight: true },
      { label: 'Configured Broker', value: status?.configured_broker || status?.broker || 'paper' },
      { label: 'Trading Mode', value: status?.mode || 'paper', good: status?.mode === 'paper' },
      { label: 'Market Status', value: status?.market_open ? 'OPEN' : 'CLOSED', good: !!status?.market_open },
      { label: 'Available Balance', value: status?.balance != null ? `₹${status.balance.toLocaleString('en-IN')}` : '—' },
    ]},
    { section: 'Risk Management', items: [
      { label: 'Max Risk Per Trade', value: '2%' },
      { label: 'Stop Loss', value: '1.5%' },
      { label: 'Target Profit', value: '3.0%' },
      { label: 'Max Open Positions', value: '5' },
      { label: 'Trailing Stop', value: 'Enabled', good: true },
    ]},
    { section: 'AI Engine', items: [
      { label: 'ML Model', value: 'XGBoost' },
      { label: 'Training Data', value: '3 Years historical' },
      { label: 'Min Confidence', value: '65%' },
      { label: 'Prediction Interval', value: '60 seconds' },
      { label: 'Daily Retrain', value: '8:00 AM IST', good: true },
    ]},
    { section: 'Market', items: [
      { label: 'Exchange', value: 'NSE (India)' },
      { label: 'Market Open', value: '9:15 AM IST' },
      { label: 'Market Close', value: '3:30 PM IST' },
      { label: 'Watchlist', value: 'Nifty 50 (10 stocks)' },
      { label: 'Market Data Provider', value: status?.data_provider === 'angelone' ? 'Angel One (live NSE)' : status?.data_provider || 'Unknown' },
    ]},
  ];

  return (
    <div className="space-y-4 animate-[fade-in_0.3s_ease]">
      <div>
        <h1 className="text-xl font-bold flex items-center gap-2"><SettingsIcon size={20} className="text-brand-blue" /> Settings</h1>
        <p className="text-text-muted text-xs mt-0.5">Current configuration — edit values in your <code className="text-brand-blue">.env</code> file and restart to apply</p>
      </div>

      {/* Connection status */}
      <div className={clsx('flex items-center gap-3 px-4 py-3 rounded-xl border text-sm',
        status ? 'bg-brand-green/5 border-brand-green/20' : 'bg-brand-red/5 border-brand-red/20'
      )}>
        {status
          ? <><CheckCircle size={16} className="text-brand-green flex-shrink-0"/><span>Backend API connected · Market data: {status.data_provider === 'angelone' ? 'Angel One' : status.data_provider || 'unknown'} · Execution: {status.broker === 'paper' ? 'Paper trading' : status.broker}</span></>
          : <><AlertCircle size={16} className="text-brand-red flex-shrink-0"/><span>Backend API not responding — check if backend container is running</span></>
        }
      </div>

      <div className="grid grid-cols-2 gap-4">
        {config.map(({ section, items }) => (
          <div key={section} className="glass-card overflow-hidden">
            <div className="px-5 py-3 border-b border-[var(--border)]">
              <span className="text-sm font-semibold">{section}</span>
            </div>
            <div className="divide-y divide-white/[0.04]">
              {items.map(({ label, value, highlight, good }) => (
                <div key={label} className="flex items-center justify-between px-5 py-3">
                  <span className="text-[12px] text-text-secondary">{label}</span>
                  <span className={clsx('text-[12px] font-mono font-semibold',
                    highlight ? 'text-brand-blue' :
                    good === true ? 'text-brand-green' :
                    good === false ? 'text-brand-red' : 'text-text-primary'
                  )}>{value}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="glass-card p-5">
        <div className="text-sm font-semibold mb-3">How to change settings</div>
        <div className="space-y-2 text-[12px] text-text-secondary">
          <p>1. Open <code className="text-brand-blue font-mono">.env</code> file in the project root</p>
          <p>2. Edit the desired values (see <code className="text-brand-blue font-mono">.env.example</code> for all options)</p>
          <p>3. Rebuild: <code className="text-brand-blue font-mono">docker compose -f docker-compose.dev.yml up -d --build backend</code></p>
          <p>4. To switch to live trading: change <code className="text-brand-blue font-mono">TRADING_MODE=live</code> and <code className="text-brand-blue font-mono">ACTIVE_BROKER=angelone</code></p>
        </div>
      </div>
    </div>
  );
}

