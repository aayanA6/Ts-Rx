import { HelpCircle, Grip, Server, Settings, MapPin, Activity, LogOut } from 'lucide-react';
import { clearTokens } from '../lib/api';

interface HeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  userEmail: string;
  onLogout: () => void;
}

const Header = ({ activeTab, setActiveTab, userEmail, onLogout }: HeaderProps) => {
  const tabs = [
    { id: 'Services', icon: Server, label: 'Services' },
    { id: 'Doctor', icon: Activity, label: 'Doctor' },
    { id: 'Settings', icon: Settings, label: 'Settings' },
  ];

  const avatarLetter = userEmail ? userEmail[0].toUpperCase() : 'U';
  const avatarColor = stringToColor(userEmail);

  const handleLogout = () => {
    clearTokens();
    onLogout();
  };

  return (
    <div style={{ backgroundColor: 'var(--bg-header)', borderBottom: '1px solid var(--borderColor)', display: 'flex', flexDirection: 'column' }}>

      {/* Top Utility Nav */}
      <div style={{ padding: '0.75rem 1.5rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', color: 'var(--text-primary)' }}>
            <Grip size={20} color="var(--text-secondary)" />
            <span style={{ fontWeight: 600, fontSize: '0.9375rem' }}>{userEmail}</span>
          </div>
          <span style={{ backgroundColor: 'rgba(59,130,246,0.15)', color: 'var(--accent-text)', padding: '0.125rem 0.375rem', borderRadius: '4px', fontSize: '0.6875rem', fontWeight: 600 }}>TS-RX</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <HelpCircle size={18} color="var(--text-secondary)" />
          </button>
          <button
            title="Sign out"
            onClick={handleLogout}
            style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          >
            <LogOut size={16} color="var(--text-secondary)" />
          </button>
          <div style={{ width: '28px', height: '28px', borderRadius: '50%', backgroundColor: avatarColor, color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.875rem', fontWeight: 600, cursor: 'pointer' }}>
            {avatarLetter}
          </div>
        </div>
      </div>

      {/* Primary Navigation Tabs */}
      <div style={{ padding: '0 1.5rem', display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginTop: '0.5rem' }}>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  background: 'none', border: 'none', padding: '0.5rem 0.75rem',
                  display: 'flex', alignItems: 'center', gap: '0.5rem',
                  color: isActive ? 'var(--accent-text)' : 'var(--text-secondary)',
                  cursor: 'pointer', fontSize: '0.8125rem', fontWeight: 500,
                  position: 'relative', paddingBottom: '0.875rem',
                }}
              >
                <Icon size={16} />
                {tab.label}
                {isActive && (
                  <div style={{ position: 'absolute', bottom: '-1px', left: 0, right: 0, height: '2px', backgroundColor: 'var(--accent-primary)', borderTopLeftRadius: '2px', borderTopRightRadius: '2px' }} />
                )}
              </button>
            );
          })}
        </div>

        <button style={{ background: 'none', border: 'none', padding: '0.5rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '0.8125rem', fontWeight: 500, paddingBottom: '0.875rem' }}>
          <MapPin size={16} />
          Resource hub
        </button>
      </div>
    </div>
  );
};

function stringToColor(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash);
  const colors = ['#BE185D', '#7C3AED', '#1D4ED8', '#0F766E', '#B45309', '#B91C1C', '#6D28D9'];
  return colors[Math.abs(hash) % colors.length];
}

export default Header;
