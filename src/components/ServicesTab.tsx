import { useEffect, useState } from 'react';
import { Server, AlertTriangle, CheckCircle, Clock, RefreshCw } from 'lucide-react';
import { fetchServices } from '../lib/api';

interface ServiceSummary {
  service: string;
  serviceType: string;
  last_seen: string;
  incident_count: number;
  last_status: string;
}

const statusIcon = (status: string) => {
  if (status === 'issue') return <AlertTriangle size={14} color="var(--status-issue)" />;
  if (status === 'warning') return <AlertTriangle size={14} color="var(--status-warning)" />;
  if (status === 'resolving') return <RefreshCw size={14} color="var(--status-resolving)" />;
  if (status === 'resolved') return <CheckCircle size={14} color="var(--status-online)" />;
  return <CheckCircle size={14} color="var(--status-online)" />;
};

const statusLabel = (status: string) => {
  if (status === 'issue') return { label: 'Incident', color: 'var(--status-issue)' };
  if (status === 'warning') return { label: 'Degraded', color: 'var(--status-warning)' };
  if (status === 'resolving') return { label: 'Analyzing', color: 'var(--status-resolving)' };
  if (status === 'resolved') return { label: 'Resolved', color: 'var(--status-online)' };
  return { label: 'Online', color: 'var(--status-online)' };
};

const ServicesTab = () => {
  const [services, setServices] = useState<ServiceSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchServices()
      .then(setServices)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const colHeader: React.CSSProperties = {
    fontSize: '0.6875rem', fontWeight: 600, color: 'var(--text-muted)',
    letterSpacing: '0.05em', textTransform: 'uppercase',
  };

  return (
    <div style={{ width: '100%', maxWidth: '1100px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '1.5rem', paddingBottom: '3rem' }}>
      <div>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 600, margin: 0 }}>Services</h1>
        <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>All monitored services across your Tailscale nodes.</span>
      </div>

      {loading ? (
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Loading services...</p>
      ) : services.length === 0 ? (
        <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
          <Server size={32} style={{ margin: '0 auto 1rem', opacity: 0.4 }} />
          <p style={{ fontSize: '0.9375rem', fontWeight: 500 }}>No services yet</p>
          <p style={{ fontSize: '0.8125rem', marginTop: '0.375rem', color: 'var(--text-muted)' }}>Services appear here once the first webhook is received.</p>
        </div>
      ) : (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(200px, 2fr) 1fr 1fr 1fr', padding: '0 1rem 0.75rem', borderBottom: '1px solid var(--borderColor)', gap: '1rem' }}>
            <span style={colHeader}>SERVICE</span>
            <span style={colHeader}>STATUS</span>
            <span style={colHeader}>INCIDENTS</span>
            <span style={colHeader}>LAST SEEN</span>
          </div>
          {services.map((svc) => {
            const { label, color } = statusLabel(svc.last_status);
            return (
              <div key={svc.service} className="ts-row-hover" style={{ display: 'grid', gridTemplateColumns: 'minmax(200px, 2fr) 1fr 1fr 1fr', padding: '0.875rem 1rem', borderBottom: '1px solid var(--borderColor)', gap: '1rem', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
                  <Server size={16} color="var(--text-muted)" />
                  <div>
                    <p style={{ fontSize: '0.875rem', fontWeight: 500, color: 'var(--text-primary)' }}>{svc.service}</p>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{svc.serviceType}</p>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                  {statusIcon(svc.last_status)}
                  <span style={{ fontSize: '0.8125rem', color }}>{label}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                  <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>{svc.incident_count}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                  <Clock size={12} color="var(--text-muted)" />
                  <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                    {new Date(svc.last_seen).toLocaleDateString()}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default ServicesTab;
