const TICKERS = [
  { n: 'NIFTY 50', p: '24,153', c: '+0.82%', up: true },
  { n: 'RELIANCE', p: '₹2,847', c: '+1.32%', up: true },
  { n: 'TCS', p: '₹3,421', c: '+0.78%', up: true },
  { n: 'HDFCBANK', p: '₹1,672', c: '-0.24%', up: false },
  { n: 'INFY', p: '₹1,814', c: '+0.55%', up: true },
  { n: 'WIPRO', p: '₹452', c: '+1.10%', up: true },
  { n: 'SENSEX', p: '79,814', c: '+0.75%', up: true },
  { n: 'ICICIBANK', p: '₹1,221', c: '+0.94%', up: true },
  { n: 'BAJFINANCE', p: '₹6,980', c: '+1.87%', up: true },
  { n: 'SBIN', p: '₹813', c: '-0.15%', up: false },
];

const Item = ({ n, p, c, up }: typeof TICKERS[0]) => (
  <span className="inline-flex items-center gap-2 px-2 text-[11px] font-mono whitespace-nowrap">
    <span className="w-1.5 h-1.5 rounded-full bg-brand-blue/50" />
    <span className="text-text-secondary font-semibold">{n}</span>
    <span className="text-text-primary">{p}</span>
    <span className={up ? 'text-brand-green' : 'text-brand-red'}>{c}</span>
  </span>
);

export default function TickerTape() {
  return (
    <div className="fixed top-0 left-0 right-0 h-[34px] bg-[rgba(6,11,20,0.97)] border-b border-[var(--border)] z-[200] overflow-hidden flex items-center">
      <div className="flex animate-[ticker_40s_linear_infinite] gap-12">
        {[...TICKERS, ...TICKERS].map((t, i) => <Item key={i} {...t} />)}
      </div>
    </div>
  );
}
