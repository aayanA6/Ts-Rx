function resolveApiBase(): string {
  const override = new URLSearchParams(window.location.search).get('apiBase');
  if (override) return override.replace(/\/$/, '');
  return import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ?? '';
}

const BASE = resolveApiBase();

let _accessToken: string | null = localStorage.getItem('access_token');
let _refreshToken: string | null = localStorage.getItem('refresh_token');

export function getAccessToken() { return _accessToken; }
export function isAuthenticated() { return !!_accessToken; }

export function setTokens(access: string, refresh: string) {
  _accessToken = access;
  _refreshToken = refresh;
  localStorage.setItem('access_token', access);
  localStorage.setItem('refresh_token', refresh);
}

export function clearTokens() {
  _accessToken = null;
  _refreshToken = null;
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}

async function refreshAccessToken(): Promise<boolean> {
  if (!_refreshToken) return false;
  try {
    const res = await fetch(`${BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: _refreshToken }),
    });
    if (!res.ok) { clearTokens(); return false; }
    const data = await res.json();
    setTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    clearTokens();
    return false;
  }
}

async function apiFetch(path: string, init: RequestInit = {}, retry = true): Promise<Response> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...(init.headers as Record<string, string> ?? {}) };
  if (_accessToken) headers['Authorization'] = `Bearer ${_accessToken}`;

  const res = await fetch(`${BASE}${path}`, { ...init, headers });

  if (res.status === 401 && retry) {
    const ok = await refreshAccessToken();
    if (ok) return apiFetch(path, init, false);
    clearTokens();
    window.location.reload();
  }

  return res;
}

// Auth
export async function login(email: string, password: string) {
  const res = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error((await res.json()).detail ?? 'Login failed');
  const data = await res.json();
  setTokens(data.access_token, data.refresh_token);
  return data;
}

export async function register(email: string, password: string) {
  const res = await fetch(`${BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error((await res.json()).detail ?? 'Registration failed');
  const data = await res.json();
  setTokens(data.access_token, data.refresh_token);
  return data;
}

export async function getMe() {
  const res = await apiFetch('/auth/me');
  if (!res.ok) throw new Error('Failed to fetch user');
  return res.json();
}

// Incidents
export async function resolveIncident(incidentId: string) {
  const res = await apiFetch(`/api/v1/analysis/incidents/${incidentId}/resolve`, { method: 'POST' });
  if (!res.ok && res.status !== 404) throw new Error('Failed to resolve incident');
}

export async function fetchIncidents(includeResolved = false) {
  const res = await apiFetch(`/api/v1/analysis/incidents?include_resolved=${includeResolved}`);
  if (!res.ok) throw new Error(`Failed: ${res.status}`);
  return res.json();
}

// Services
export async function fetchServices() {
  const res = await apiFetch('/api/v1/analysis/services');
  if (!res.ok) throw new Error(`Failed: ${res.status}`);
  return res.json();
}

// Tailscale tailnet device health
export async function fetchDeviceHealth() {
  const res = await apiFetch('/api/v1/tailscale/devices');
  if (!res.ok) throw new Error(`Failed: ${res.status}`);
  return res.json();
}

// API Keys
export async function fetchApiKeys() {
  const res = await apiFetch('/api/v1/keys');
  if (!res.ok) throw new Error('Failed to fetch API keys');
  return res.json();
}

export async function createApiKey(label: string) {
  const res = await apiFetch('/api/v1/keys', { method: 'POST', body: JSON.stringify({ label }) });
  if (!res.ok) throw new Error('Failed to create API key');
  return res.json();
}

export async function deleteApiKey(id: string) {
  const res = await apiFetch(`/api/v1/keys/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete API key');
}

// Notifications
export async function fetchNotificationSettings() {
  const res = await apiFetch('/api/v1/notifications');
  if (!res.ok) throw new Error('Failed to fetch notification settings');
  return res.json();
}

export async function updateNotificationSettings(settings: {
  email_enabled: boolean;
  discord_enabled: boolean;
  discord_webhook_url: string | null;
  slack_enabled: boolean;
  slack_webhook_url: string | null;
}) {
  const res = await apiFetch('/api/v1/notifications', { method: 'PUT', body: JSON.stringify(settings) });
  if (!res.ok) throw new Error('Failed to update notification settings');
  return res.json();
}

// WebSocket
export function createIncidentWebSocket(onMessage: (data: unknown) => void): WebSocket {
  const wsBase = BASE.replace(/^http/, 'ws') || `ws://${window.location.host}`;
  const ws = new WebSocket(`${wsBase}/ws/incidents?token=${_accessToken ?? ''}`);
  ws.onmessage = (e) => {
    try { onMessage(JSON.parse(e.data)); } catch { /* ignore */ }
  };
  return ws;
}
