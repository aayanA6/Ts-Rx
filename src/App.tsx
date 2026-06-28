import { useEffect, useState } from 'react';
import Header from './components/Header';
import Dashboard from './components/Dashboard';
import ServicesTab from './components/ServicesTab';
import SettingsTab from './components/SettingsTab';
import LoginPage from './components/LoginPage';
import { isAuthenticated, getMe } from './lib/api';

const params = new URLSearchParams(window.location.search);
const embedded = params.get('embedded') === 'true';
const pageBg = params.get('bg') || 'var(--bg-base)';

// App URL for webhook links in Settings — falls back to current origin
const APP_URL = import.meta.env.VITE_APP_URL || window.location.origin;

function App() {
  const [authed, setAuthed] = useState(isAuthenticated());
  const [userEmail, setUserEmail] = useState('');
  const [activeTab, setActiveTab] = useState('Doctor');

  useEffect(() => {
    if (authed) {
      getMe()
        .then((u) => setUserEmail(u.email))
        .catch(() => { setAuthed(false); });
    }
  }, [authed]);

  if (!authed) {
    return <LoginPage onAuth={() => setAuthed(true)} />;
  }

  const renderTab = () => {
    switch (activeTab) {
      case 'Doctor': return <Dashboard />;
      case 'Services': return <ServicesTab />;
      case 'Settings': return <SettingsTab userEmail={userEmail} appUrl={APP_URL} />;
      default:
        return (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '60vh', color: 'var(--text-secondary)' }}>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.5rem' }}>{activeTab}</h2>
            <p>Coming soon.</p>
          </div>
        );
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%', minHeight: '100vh', backgroundColor: pageBg }}>
      {!embedded && (
        <Header
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          userEmail={userEmail}
          onLogout={() => { setAuthed(false); setUserEmail(''); }}
        />
      )}
      <main style={{ flex: 1, padding: '2rem 1.5rem', margin: '0 auto', width: '100%', maxWidth: '1200px' }}>
        {renderTab()}
      </main>
    </div>
  );
}

export default App;
