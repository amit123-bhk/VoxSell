import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import LoginModal from './components/LoginModal';
import LiveCallPage from './pages/LiveCallPage';
import LeadsPage from './pages/LeadsPage';
import CallsPage from './pages/CallsPage';
import AnalyticsPage from './pages/AnalyticsPage';
import KnowledgeBasePage from './pages/KnowledgeBasePage';

export default function App() {
  const [activeTab, setActiveTab] = useState('live-call');
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [showLoginModal, setShowLoginModal] = useState(false);

  useEffect(() => {
    // Restore session from localStorage
    const savedToken = localStorage.getItem('voxsell_token');
    const savedUser = localStorage.getItem('voxsell_user');

    if (savedToken && savedUser) {
      try {
        setToken(savedToken);
        setUser(JSON.parse(savedUser));
      } catch (e) {
        localStorage.removeItem('voxsell_token');
        localStorage.removeItem('voxsell_user');
      }
    }
  }, []);

  const handleLoginSuccess = (userData, accessToken) => {
    setUser(userData);
    setToken(accessToken);
    setShowLoginModal(false);
  };

  const handleLogout = () => {
    localStorage.removeItem('voxsell_token');
    localStorage.removeItem('voxsell_user');
    setUser(null);
    setToken(null);
  };

  const handleTabChange = (tabId) => {
    if (tabId === 'login') {
      setShowLoginModal(true);
    } else {
      setActiveTab(tabId);
    }
  };

  return (
    <div className="min-h-screen bg-black text-white flex flex-col font-sans selection:bg-zinc-800 selection:text-white">
      {/* Top Navigation */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={handleTabChange}
        user={user}
        onLogout={handleLogout}
      />

      {/* Main Content Area */}
      <main className="flex-1">
        {activeTab === 'live-call' && <LiveCallPage />}
        {activeTab === 'leads' && <LeadsPage token={token} />}
        {activeTab === 'calls' && <CallsPage />}
        {activeTab === 'analytics' && <AnalyticsPage />}
        {activeTab === 'knowledge-base' && <KnowledgeBasePage />}
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-800 bg-black py-3 px-6 text-center text-xs font-mono text-zinc-500 flex flex-col sm:flex-row items-center justify-between">
        <span>VOXSELL TELEPHONY CONSOLE</span>
        <span>ENGINE: DEEPGRAM / GEMINI / ELEVENLABS / CHROMADB</span>
        <span>LATENCY TARGET: &lt;1500ms</span>
      </footer>

      {/* Admin Login Modal */}
      {showLoginModal && (
        <LoginModal
          onLoginSuccess={handleLoginSuccess}
          onCancel={() => setShowLoginModal(false)}
        />
      )}
    </div>
  );
}
