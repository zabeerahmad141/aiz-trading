import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listUsers, createUser, updateUser } from '@/lib/api';
import { useAuthStore } from '@/store/auth';
import clsx from 'clsx';
import toast from 'react-hot-toast';
import { UserPlus, Shield, Users as UsersIcon } from 'lucide-react';

const ROLES = ['admin', 'analyst', 'viewer', 'guest'];
const ROLE_COLORS: Record<string, string> = {
  admin:   'text-brand-gold   bg-brand-gold/10   border-brand-gold/30',
  analyst: 'text-brand-blue   bg-brand-blue/10   border-brand-blue/30',
  viewer:  'text-brand-green  bg-brand-green/10  border-brand-green/30',
  guest:   'text-text-muted   bg-white/5         border-white/10',
};

export default function Users() {
  const role = useAuthStore((s) => s.role);
  const qc   = useQueryClient();

  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ username: '', email: '', password: '', role: 'viewer' });
  const [creating, setCreating] = useState(false);

  const { data: users = [], isLoading, isError } = useQuery({
    queryKey: ['users'],
    queryFn: () => listUsers().then(r => r.data),
    retry: 1,
  });

  const toggleActive = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      updateUser(id, { is_active }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); toast.success('User updated'); },
    onError:   () => toast.error('Failed to update user'),
  });

  const changeRole = useMutation({
    mutationFn: ({ id, role }: { id: number; role: string }) =>
      updateUser(id, { role }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); toast.success('Role updated'); },
    onError:   () => toast.error('Failed to update role'),
  });

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      await createUser(form);
      toast.success(`User '${form.username}' created`);
      setForm({ username: '', email: '', password: '', role: 'viewer' });
      setShowCreate(false);
      qc.invalidateQueries({ queryKey: ['users'] });
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to create user');
    } finally {
      setCreating(false);
    }
  }

  if (role !== 'admin') {
    return (
      <div className="glass-card p-10 text-center">
        <Shield size={40} className="mx-auto mb-4 text-brand-red opacity-50" />
        <h2 className="text-xl font-bold mb-2">Admin Only</h2>
        <p className="text-sm text-text-muted">You need admin role to manage users.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4 animate-[fade-in_0.3s_ease]">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <UsersIcon size={20} className="text-brand-blue" /> User Management
          </h1>
          <p className="text-text-muted text-xs mt-0.5">Create and manage user accounts and roles</p>
        </div>
        <button onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-blue/15 text-brand-blue border border-brand-blue/30 text-sm font-semibold hover:bg-brand-blue/25 transition-all">
          <UserPlus size={14} /> Add User
        </button>
      </div>

      {/* Create user form */}
      {showCreate && (
        <div className="glass-card p-5">
          <h2 className="text-sm font-semibold mb-4">Create New User</h2>
          <form onSubmit={handleCreate} className="grid grid-cols-2 gap-3">
            <input required placeholder="Username" value={form.username}
              onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
              className="bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-brand-blue/50 col-span-1" />
            <input required placeholder="Email" type="email" value={form.email}
              onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
              className="bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-brand-blue/50" />
            <input required placeholder="Password (min 8 chars)" type="password" value={form.password}
              minLength={8}
              onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
              className="bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-brand-blue/50" />
            <select value={form.role} onChange={e => setForm(f => ({ ...f, role: e.target.value }))}
              className="bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-text-primary focus:outline-none focus:border-brand-blue/50">
              {ROLES.map(r => <option key={r} value={r}>{r.charAt(0).toUpperCase() + r.slice(1)}</option>)}
            </select>
            <div className="col-span-2 flex gap-2 justify-end">
              <button type="button" onClick={() => setShowCreate(false)}
                className="px-4 py-2 rounded-lg text-sm text-text-muted hover:text-text-primary border border-white/10 hover:border-white/20">
                Cancel
              </button>
              <button type="submit" disabled={creating}
                className="px-4 py-2 rounded-lg text-sm font-semibold bg-brand-blue/15 text-brand-blue border border-brand-blue/30 hover:bg-brand-blue/25 disabled:opacity-50">
                {creating ? 'Creating...' : 'Create User'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Users table */}
      <div className="glass-card overflow-hidden">
        <div className="px-5 py-3 border-b border-[var(--border)] flex items-center justify-between">
          <span className="text-sm font-semibold">All Users</span>
          <span className="text-xs text-text-muted bg-white/5 px-2 py-0.5 rounded-full">{users.length} accounts</span>
        </div>

        {isLoading && <div className="p-8 text-center text-text-muted text-sm">Loading users...</div>}
        {isError  && <div className="p-8 text-center text-brand-red text-sm">Could not load users — check backend connection</div>}

        {!isLoading && !isError && (
          <table className="w-full text-[12px]">
            <thead>
              <tr className="text-text-muted text-[10px] uppercase tracking-wider">
                {['Username','Email','Role','Status','Last Login','Actions'].map(h => (
                  <th key={h} className="text-left px-5 py-3 border-b border-[var(--border)] font-semibold">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {users.map((u: any) => (
                <tr key={u.id} className="hover:bg-white/[0.02] transition-colors">
                  <td className="px-5 py-3 font-semibold">{u.username}</td>
                  <td className="px-5 py-3 text-text-muted">{u.email}</td>
                  <td className="px-5 py-3">
                    <select
                      value={u.role}
                      onChange={e => changeRole.mutate({ id: u.id, role: e.target.value })}
                      className={clsx('text-[10px] font-bold px-2 py-1 rounded border bg-transparent cursor-pointer focus:outline-none', ROLE_COLORS[u.role] || ROLE_COLORS.guest)}
                    >
                      {ROLES.map(r => <option key={r} value={r} className="bg-bg-secondary text-text-primary">{r}</option>)}
                    </select>
                  </td>
                  <td className="px-5 py-3">
                    <span className={clsx('text-[10px] font-bold px-2 py-0.5 rounded-full border',
                      u.is_active ? 'text-brand-green bg-brand-green/10 border-brand-green/30' : 'text-brand-red bg-brand-red/10 border-brand-red/30'
                    )}>{u.is_active ? 'Active' : 'Inactive'}</span>
                  </td>
                  <td className="px-5 py-3 text-text-muted font-mono text-[11px]">
                    {u.last_login ? new Date(u.last_login).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : 'Never'}
                  </td>
                  <td className="px-5 py-3">
                    <button
                      onClick={() => toggleActive.mutate({ id: u.id, is_active: !u.is_active })}
                      className={clsx('text-[10px] px-2.5 py-1 rounded border font-semibold transition-all',
                        u.is_active
                          ? 'border-brand-red/30 text-brand-red hover:bg-brand-red/10'
                          : 'border-brand-green/30 text-brand-green hover:bg-brand-green/10'
                      )}>
                      {u.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Role guide */}
      <div className="glass-card p-4">
        <div className="text-xs font-semibold text-text-secondary mb-3">Role Permissions</div>
        <div className="grid grid-cols-4 gap-3 text-[11px]">
          {[
            { role: 'admin',   perms: 'Full access · Manage users · All settings' },
            { role: 'analyst', perms: 'Dashboard · Trade control · Backtest' },
            { role: 'viewer',  perms: 'View dashboard · Trade history · Read only' },
            { role: 'guest',   perms: 'Portfolio summary only · No trade data' },
          ].map(({ role, perms }) => (
            <div key={role} className="p-3 rounded-lg bg-white/[0.02] border border-white/5">
              <span className={clsx('text-[10px] font-bold px-2 py-0.5 rounded border', ROLE_COLORS[role])}>{role}</span>
              <p className="text-text-muted mt-2">{perms}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

