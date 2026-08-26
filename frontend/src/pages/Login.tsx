import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/auth';
import { login } from '@/lib/api';
import toast from 'react-hot-toast';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const setAuth = useAuthStore((s) => s.setAuth);
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await login(username, password);
      setAuth(data.access_token, data.refresh_token, data.username, data.role);
      toast.success(`Welcome back, ${data.username}!`);
      navigate('/');
    } catch {
      toast.error('Invalid username or password');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-bg-primary flex items-center justify-center relative overflow-hidden">
      {/* Neural background */}
      <canvas id="neural" className="absolute inset-0 pointer-events-none" />

      {/* Glows */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full bg-brand-blue/5 blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 rounded-full bg-brand-gold/5 blur-3xl pointer-events-none" />

      <div className="relative z-10 w-full max-w-sm mx-4">
        {/* Logo */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-brand-blue to-blue-600 shadow-[0_0_30px_rgba(0,212,255,0.4)] mb-4">
            <span className="text-3xl">⚡</span>
          </div>
          <h1 className="text-4xl font-black gradient-text tracking-wider">AI Z</h1>
          <p className="text-text-muted text-xs tracking-[3px] uppercase mt-1">Trading Engine</p>
        </div>

        {/* Card */}
        <form onSubmit={handleSubmit} className="glass-card p-8 space-y-5">
          <h2 className="text-text-secondary text-sm font-semibold text-center tracking-wider uppercase">
            Sign In to Continue
          </h2>

          <div className="space-y-3">
            <input
              type="text"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-brand-blue/50 focus:bg-brand-blue/5 transition-all"
            />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-brand-blue/50 focus:bg-brand-blue/5 transition-all"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-lg font-bold text-sm tracking-wide text-black transition-all bg-gradient-to-r from-brand-blue to-blue-500 hover:shadow-[0_0_20px_rgba(0,212,255,0.4)] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Authenticating...' : 'Sign In'}
          </button>

          <p className="text-center text-text-muted text-xs">
            Protected by AES-256 encryption
          </p>
        </form>

        <p className="text-center text-text-muted text-xs mt-6">
          AI Z v1.0 · All rights reserved
        </p>
      </div>
    </div>
  );
}
