import React, { useState } from 'react';

export default function LoginModal({ onLoginSuccess, onCancel }) {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('password123');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Authentication failed.');
      }

      localStorage.setItem('voxsell_token', data.access_token);
      localStorage.setItem('voxsell_user', JSON.stringify(data.user));
      onLoginSuccess(data.user, data.access_token);
    } catch (err) {
      setError(err.message || 'Authentication error.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/90">
      <div className="w-full max-w-sm bg-zinc-950 border border-zinc-800 rounded p-6 relative shadow-2xl">
        <div className="mb-6">
          <h2 className="text-base font-bold text-white font-mono uppercase tracking-wider">Console Authentication</h2>
          <p className="text-xs text-zinc-400 mt-1">
            JWT credential verification for management and CRM access.
          </p>
        </div>

        {error && (
          <div className="mb-4 p-2.5 rounded bg-zinc-900 border border-red-800 text-red-400 text-xs font-mono">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-mono uppercase text-zinc-400 mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              className="w-full px-3 py-2 bg-zinc-900 border border-zinc-800 rounded text-xs text-white focus:outline-none focus:border-zinc-600 font-mono"
              placeholder="admin"
            />
          </div>

          <div>
            <label className="block text-xs font-mono uppercase text-zinc-400 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-3 py-2 bg-zinc-900 border border-zinc-800 rounded text-xs text-white focus:outline-none focus:border-zinc-600 font-mono"
              placeholder="••••••••••••"
            />
            <p className="text-[11px] font-mono text-zinc-500 mt-1">Default credentials: admin / password123</p>
          </div>

          <div className="pt-2 flex gap-2">
            {onCancel && (
              <button
                type="button"
                onClick={onCancel}
                className="flex-1 py-2 px-3 rounded bg-zinc-900 border border-zinc-800 text-zinc-300 text-xs font-mono hover:bg-zinc-800"
              >
                CANCEL
              </button>
            )}
            <button
              type="submit"
              disabled={loading}
              className="flex-1 py-2 px-3 rounded bg-white text-black font-semibold text-xs font-mono hover:bg-zinc-200 disabled:opacity-50"
            >
              {loading ? 'VERIFYING...' : 'SIGN IN'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
