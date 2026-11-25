import React from 'react';
import { PhoneCall, Users, History, BarChart3, Database, Shield, LogOut } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, user, onLogout }) {
  const navItems = [
    { id: 'live-call', label: 'Live Call' },
    { id: 'leads', label: 'Leads' },
    { id: 'calls', label: 'Call Logs' },
    { id: 'analytics', label: 'Analytics' },
    { id: 'knowledge-base', label: 'Knowledge Base' },
  ];

  return (
    <header className="border-b border-zinc-800 bg-black sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="h-7 w-7 rounded bg-white text-black flex items-center justify-center font-mono font-black text-sm">
              V
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold tracking-wider text-white uppercase font-mono">
                VOXSELL
              </span>
              <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest border border-zinc-800 px-1.5 py-0.5 rounded">
                v2.4
              </span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="flex items-center space-x-1">
            {navItems.map((item) => {
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`px-3 py-1.5 rounded text-xs font-medium font-mono uppercase tracking-wider ${
                    isActive
                      ? 'bg-zinc-800 text-white border border-zinc-700'
                      : 'text-zinc-400 hover:text-white hover:bg-zinc-900 border border-transparent'
                  }`}
                >
                  {item.label}
                </button>
              );
            })}
          </nav>

          {/* User Profile & Logout */}
          <div className="flex items-center gap-3">
            {user ? (
              <div className="flex items-center gap-3 font-mono">
                <div className="hidden sm:flex flex-col text-right">
                  <span className="text-xs font-semibold text-white">{user.username || 'admin'}</span>
                  <span className="text-[10px] text-zinc-400">AUTHENTICATED</span>
                </div>
                <button
                  onClick={onLogout}
                  title="Logout"
                  className="px-2.5 py-1 rounded text-xs font-mono text-zinc-400 hover:text-white hover:bg-zinc-900 border border-zinc-800 hover:border-zinc-700"
                >
                  LOGOUT
                </button>
              </div>
            ) : (
              <button
                onClick={() => setActiveTab('login')}
                className="px-3 py-1.5 rounded text-xs font-mono font-semibold bg-white text-black hover:bg-zinc-200"
              >
                ADMIN LOGIN
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
