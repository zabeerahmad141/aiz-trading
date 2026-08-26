import { useState, useEffect } from 'react';

export default function LiveClock() {
  const [time, setTime] = useState('');

  useEffect(() => {
    const tick = () => {
      const now = new Date().toLocaleTimeString('en-IN', {
        hour12: false,
        timeZone: 'Asia/Kolkata',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
      setTime(now + ' IST');
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <span className="font-mono text-xs text-text-secondary bg-brand-blue/10 border border-[var(--border)] rounded-lg px-3 py-1.5">
      {time}
    </span>
  );
}
