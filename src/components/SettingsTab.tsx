import { useEffect, useState } from 'react';
import { Copy, Plus, Trash2, Check } from 'lucide-react';
import {
  fetchApiKeys,
  createApiKey,
  deleteApiKey,
  fetchNotificationSettings,
  updateNotificationSettings,
  testNotifications,
} from '../lib/api';

interface ApiKey {
  id: string;
  label: string;
  created_at: string;
  last_used_at: string | null;
}

interface NotifSettings {
  email_enabled: boolean;
  discord_enabled: boolean;
  discord_webhook_url: string | null;
  slack_enabled: boolean;
  slack_webhook_url: string | null;
  ntfy_enabled: boolean;
  ntfy_topic: string | null;
}

interface SettingsTabProps {
  userEmail: string;
  appUrl: string;
}

const SettingsTab = ({ userEmail, appUrl }: SettingsTabProps) => {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [newKeyLabel, setNewKeyLabel] = useState('');
  const [newKeyPlaintext, setNewKeyPlaintext] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState(false);
  const [copiedWebhook, setCopiedWebhook] = useState<string | null>(null);
  const [keyLoading, setKeyLoading] = useState(false);
  const [notif, setNotif] = useState<NotifSettings>({
    email_enabled: false,
    discord_enabled: false,
    discord_webhook_url: null,
    slack_enabled: false,
    slack_webhook_url: null,
    ntfy_enabled: false,
    ntfy_topic: null,
  });
  const [notifSaving, setNotifSaving] = useState(false);
  const [notifSaved, setNotifSaved] = useState(false);
  const [testSending, setTestSending] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);

  useEffect(() => {
    fetchApiKeys().then(setKeys).catch(console.error);
    fetchNotificationSettings().then(setNotif).catch(console.error);
  }, []);

  const handleCreateKey = async () => {
    if (!newKeyLabel.trim()) return;
    setKeyLoading(true);
    try {
      const data = await createApiKey(newKeyLabel.trim());
      setNewKeyPlaintext(data.key);
      setKeys((prev) => [...prev, { id: data.id, label: data.label, created_at: data.created_at, last_used_at: null }]);
      setNewKeyLabel('');
    } catch (e) {
      console.error(e);
    } finally {
      setKeyLoading(false);
    }
  };

  const handleDeleteKey = async (id: string) => {
    if (!confirm('Revoke this API key? Connected services will stop working.')) return;
    try {
      await deleteApiKey(id);
      setKeys((prev) => prev.filter((k) => k.id !== id));
    } catch (e) {
      console.error(e);
    }
  };

  const copyToClipboard = (text: string, type: 'key' | string) => {
    navigator.clipboard.writeText(text);
    if (type === 'key') {
      setCopiedKey(true);
      setTimeout(() => setCopiedKey(false), 2000);
    } else {
      setCopiedWebhook(type);
      setTimeout(() => setCopiedWebhook(null), 2000);
    }
  };

  const handleSaveNotifications = async () => {
    setNotifSaving(true);
    try {
      await updateNotificationSettings(notif);
      setNotifSaved(true);
      setTimeout(() => setNotifSaved(false), 2000);
    } catch (e) {
      console.error(e);
    } finally {
      setNotifSaving(false);
    }
  };

  const handleTestNotification = async () => {
    setTestSending(true);
    setTestResult(null);
    try {
      const data = await testNotifications();
      setTestResult({ ok: true, message: data.message });
    } catch (e) {
      setTestResult({ ok: false, message: e instanceof Error ? e.message : 'Failed to send test notification' });
    } finally {
      setTestSending(false);
      setTimeout(() => setTestResult(null), 5000);
    }
  };

  const labelStyle: React.CSSProperties = { display: 'block', fontSize: '0.8125rem', fontWeight: 500, color: 'var(--text-secondary)', marginBottom: '0.375rem' };
  const sectionTitle: React.CSSProperties = { fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.25rem' };
  const sectionDesc: React.CSSProperties = { fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: '1rem' };

  return (
    <div style={{ maxWidth: '720px', display: 'flex', flexDirection: 'column', gap: '2rem', paddingBottom: '3rem' }}>
      <div>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 600, margin: 0 }}>Settings</h1>
        <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Manage your account, API keys, and notifications.</span>
      </div>

      {/* Account */}
      <div className="ts-panel" style={{ padding: '1.5rem' }}>
        <p style={sectionTitle}>Account</p>
        <p style={sectionDesc}>Signed in as <strong style={{ color: 'var(--text-primary)' }}>{userEmail}</strong></p>
      </div>

      {/* API Keys */}
      <div className="ts-panel" style={{ padding: '1.5rem' }}>
        <p style={sectionTitle}>API Keys</p>
        <p style={sectionDesc}>Use an API key as the webhook path to connect Uptime Kuma or your TS-RX agent. The key is shown only once on creation.</p>

        {newKeyPlaintext && (
          <div style={{ marginBottom: '1.25rem', padding: '1rem', backgroundColor: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.25)', borderRadius: 'var(--radius-md)' }}>
            <p style={{ fontSize: '0.8125rem', color: '#6EE7B7', fontWeight: 500, marginBottom: '0.5rem' }}>Key created — copy it now, it won't be shown again.</p>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <code style={{ flex: 1, fontFamily: 'monospace', fontSize: '0.8125rem', color: 'var(--text-primary)', wordBreak: 'break-all', backgroundColor: 'var(--bg-base)', padding: '0.5rem 0.75rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--borderColor)' }}>
                {newKeyPlaintext}
              </code>
              <button className="btn btn-secondary" style={{ flexShrink: 0 }} onClick={() => copyToClipboard(newKeyPlaintext, 'key')}>
                {copiedKey ? <Check size={14} color="var(--status-online)" /> : <Copy size={14} />}
              </button>
            </div>
          </div>
        )}

        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
          <input
            className="ts-input"
            placeholder="Key label (e.g. homelab)"
            value={newKeyLabel}
            onChange={(e) => setNewKeyLabel(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCreateKey()}
            style={{ flex: 1 }}
          />
          <button className="btn btn-primary" onClick={handleCreateKey} disabled={keyLoading || !newKeyLabel.trim()} style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
            <Plus size={14} /> Create
          </button>
        </div>

        {keys.length === 0 ? (
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', padding: '0.75rem 0' }}>No API keys yet.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {keys.map((key) => {
              const webhookUrl = `${appUrl}/api/v1/ingest/${key.id}`;
              return (
                <div key={key.id} style={{ padding: '0.875rem 1rem', backgroundColor: 'var(--bg-surface)', border: '1px solid var(--borderColor)', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <p style={{ fontSize: '0.875rem', fontWeight: 500, color: 'var(--text-primary)', marginBottom: '0.25rem' }}>{key.label}</p>
                      <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        Created {new Date(key.created_at).toLocaleDateString()}
                        {key.last_used_at && ` · Last used ${new Date(key.last_used_at).toLocaleDateString()}`}
                      </p>
                    </div>
                    <button className="btn btn-danger" style={{ padding: '0.25rem 0.5rem' }} onClick={() => handleDeleteKey(key.id)}>
                      <Trash2 size={14} />
                    </button>
                  </div>
                  <div style={{ marginTop: '0.625rem' }}>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Uptime Kuma webhook URL:</p>
                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                      <code style={{ flex: 1, fontFamily: 'monospace', fontSize: '0.75rem', color: 'var(--text-secondary)', wordBreak: 'break-all', backgroundColor: 'var(--bg-base)', padding: '0.375rem 0.625rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--borderColor)' }}>
                        {webhookUrl}
                      </code>
                      <button className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', flexShrink: 0 }} onClick={() => copyToClipboard(webhookUrl, key.id)}>
                        {copiedWebhook === key.id ? <Check size={12} color="var(--status-online)" /> : <Copy size={12} />}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Notifications */}
      <div className="ts-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        <div>
          <p style={sectionTitle}>Notifications</p>
          <p style={sectionDesc}>Get alerted when an incident is analyzed. Configure at least one channel.</p>
        </div>

        {/* Email */}
        <div>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', cursor: 'pointer', marginBottom: '0.375rem' }}>
            <input type="checkbox" checked={notif.email_enabled} onChange={(e) => setNotif((p) => ({ ...p, email_enabled: e.target.checked }))} />
            <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>Email to {userEmail}</span>
          </label>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: '1.375rem' }}>Requires SMTP configured on the server.</p>
        </div>

        {/* Discord */}
        <div>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', cursor: 'pointer', marginBottom: '0.5rem' }}>
            <input type="checkbox" checked={notif.discord_enabled} onChange={(e) => setNotif((p) => ({ ...p, discord_enabled: e.target.checked }))} />
            <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>Discord</span>
          </label>
          {notif.discord_enabled && (
            <div style={{ marginLeft: '1.375rem' }}>
              <label style={labelStyle}>Webhook URL</label>
              <input
                className="ts-input"
                placeholder="https://discord.com/api/webhooks/..."
                value={notif.discord_webhook_url ?? ''}
                onChange={(e) => setNotif((p) => ({ ...p, discord_webhook_url: e.target.value || null }))}
              />
            </div>
          )}
        </div>

        {/* Slack */}
        <div>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', cursor: 'pointer', marginBottom: '0.5rem' }}>
            <input type="checkbox" checked={notif.slack_enabled} onChange={(e) => setNotif((p) => ({ ...p, slack_enabled: e.target.checked }))} />
            <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>Slack</span>
          </label>
          {notif.slack_enabled && (
            <div style={{ marginLeft: '1.375rem' }}>
              <label style={labelStyle}>Incoming Webhook URL</label>
              <input
                className="ts-input"
                placeholder="https://hooks.slack.com/services/..."
                value={notif.slack_webhook_url ?? ''}
                onChange={(e) => setNotif((p) => ({ ...p, slack_webhook_url: e.target.value || null }))}
              />
            </div>
          )}
        </div>

        {/* ntfy */}
        <div>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', cursor: 'pointer', marginBottom: '0.5rem' }}>
            <input type="checkbox" checked={notif.ntfy_enabled} onChange={(e) => setNotif((p) => ({ ...p, ntfy_enabled: e.target.checked }))} />
            <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>ntfy.sh</span>
          </label>
          {notif.ntfy_enabled && (
            <div style={{ marginLeft: '1.375rem' }}>
              <label style={labelStyle}>Topic</label>
              <input
                className="ts-input"
                placeholder="my-secret-tsrx-topic"
                value={notif.ntfy_topic ?? ''}
                onChange={(e) => setNotif((p) => ({ ...p, ntfy_topic: e.target.value || null }))}
              />
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.375rem' }}>
                Subscribe at ntfy.sh/{notif.ntfy_topic || '<topic>'} or in the ntfy app. Anyone who knows the topic name can read it, so pick something hard to guess.
              </p>
            </div>
          )}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem', paddingTop: '0.5rem', borderTop: '1px solid var(--borderColor)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <button className="btn btn-primary" onClick={handleSaveNotifications} disabled={notifSaving}>
              {notifSaving ? 'Saving...' : 'Save'}
            </button>
            <button className="btn btn-secondary" onClick={handleTestNotification} disabled={testSending}>
              {testSending ? 'Sending...' : 'Send test notification'}
            </button>
            {notifSaved && <span style={{ fontSize: '0.8125rem', color: 'var(--status-online)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}><Check size={14} /> Saved</span>}
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Save your settings before sending a test — the test uses whatever is currently saved, not unsaved edits above.</p>
          {testResult && (
            <span style={{ fontSize: '0.8125rem', color: testResult.ok ? 'var(--status-online)' : 'var(--status-issue)' }}>
              {testResult.message}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

export default SettingsTab;
