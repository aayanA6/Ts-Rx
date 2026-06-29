import { useCallback, useEffect, useRef, useState } from 'react';
import { Search } from 'lucide-react';
import IncidentCard from './IncidentCard';
import ReviewModal from './ReviewModal';
import { Incident } from '../lib/types';
import { fetchIncidents, createIncidentWebSocket } from '../lib/api';

const Dashboard = () => {
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [showResolved, setShowResolved] = useState(false);
  const [search, setSearch] = useState('');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Ref so the WS callback always calls the latest version (avoids stale closure)
  const loadIncidentsRef = useRef<() => Promise<void>>(async () => {});

  const selectedIncident = selectedIncidentId
    ? incidents.find((i) => i.id === selectedIncidentId) ?? null
    : null;

  const filteredIncidents = search.trim()
    ? incidents.filter(
        (i) =>
          i.service.toLowerCase().includes(search.toLowerCase()) ||
          i.id.toLowerCase().includes(search.toLowerCase()),
      )
    : incidents;

  const loadIncidents = useCallback(async () => {
    try {
      const data = await fetchIncidents(showResolved);
      setIncidents(data);
      setLoadError(null);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load incidents');
    } finally {
      setLoading(false);
    }
  }, [showResolved]);

  // Keep ref in sync with latest callback so WS handler never stales
  useEffect(() => {
    loadIncidentsRef.current = loadIncidents;
  }, [loadIncidents]);

  const connectWs = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = createIncidentWebSocket((data: unknown) => {
      const msg = data as { type: string };
      if (msg.type === 'job_update' || msg.type === 'incident_resolved') {
        void loadIncidentsRef.current();
      }
    });

    ws.onclose = () => {
      wsRef.current = null;
      reconnectTimerRef.current = setTimeout(() => connectWs(), 3000);
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, []);

  // Initial load + WebSocket
  useEffect(() => {
    void loadIncidents();
    connectWs();

    return () => {
      wsRef.current?.close();
      wsRef.current = null;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
    };
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  // Re-fetch when showResolved changes
  useEffect(() => {
    setLoading(true);
    void loadIncidents();
  }, [loadIncidents]);

  useEffect(() => {
    if (!selectedIncidentId) return;
    const still = incidents.some((i) => i.id === selectedIncidentId);
    if (!still) setSelectedIncidentId(null);
  }, [incidents, selectedIncidentId]);

  return (
    <div className="flex-col" style={{ width: '100%', maxWidth: '1100px', margin: '0 auto', gap: '2rem', paddingBottom: '3rem' }}>

      {/* Page Header */}
      <div className="flex items-start justify-between">
        <div className="flex-col gap-1">
          <h1 style={{ fontSize: '1.5rem', fontWeight: 600, margin: 0 }}>Doctor</h1>
          <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            AI-powered incident triage for your Tailscale services.
          </span>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', fontSize: '0.8125rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
            <input type="checkbox" checked={showResolved} onChange={(e) => setShowResolved(e.target.checked)} />
            Show resolved
          </label>
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex items-center gap-3">
        <div style={{ position: 'relative', flex: 1, maxWidth: '600px' }}>
          <Search size={16} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input
            type="text"
            className="ts-input"
            placeholder="Search by service name or incident ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ paddingLeft: '2.25rem', paddingRight: '1rem', backgroundColor: 'var(--bg-base)' }}
          />
        </div>
      </div>

      <div style={{ display: 'inline-block', padding: '0.125rem 0.625rem', backgroundColor: 'rgba(255, 255, 255, 0.1)', borderRadius: 'var(--radius-full)', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', alignSelf: 'flex-start', marginBottom: '1rem' }}>
        {loading ? 'Loading...' : `${filteredIncidents.length} incident${filteredIncidents.length !== 1 ? 's' : ''}`}
      </div>

      {loadError && (
        <div style={{ marginBottom: '1rem', padding: '0.75rem 1rem', border: '1px solid rgba(239,68,68,0.45)', borderRadius: '0.5rem', color: '#FCA5A5', backgroundColor: 'rgba(127,29,29,0.3)', fontSize: '0.875rem' }}>
          {loadError}
        </div>
      )}

      {/* Table Headers */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(250px, 2fr) minmax(150px, 1fr) minmax(150px, 1fr) minmax(150px, 1fr) 40px', padding: '0 1rem 0.75rem 1rem', borderBottom: '1px solid var(--borderColor)', fontSize: '0.6875rem', fontWeight: 600, color: 'var(--text-muted)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
        <div>SERVICE</div>
        <div>STATUS</div>
        <div>CONFIDENCE</div>
        <div>LAST SEEN</div>
        <div></div>
      </div>

      {/* Incidents */}
      <div className="flex-col">
        {filteredIncidents.map((incident, index) => (
          <IncidentCard
            key={incident.id}
            incident={incident}
            onReview={() => setSelectedIncidentId(incident.id)}
            isLast={index === filteredIncidents.length - 1}
          />
        ))}
        {!loading && filteredIncidents.length === 0 && (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <p style={{ fontSize: '0.9375rem' }}>
              {search ? 'No incidents match your search.' : 'No active incidents — services are healthy.'}
            </p>
          </div>
        )}
      </div>

      {selectedIncident && (
        <ReviewModal
          incident={selectedIncident}
          onClose={() => setSelectedIncidentId(null)}
          onResolve={() => void loadIncidents()}
        />
      )}
    </div>
  );
};

export default Dashboard;
