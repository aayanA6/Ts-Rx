import { DeviceHealth } from '../lib/types';
import { STATUS_INFO } from '../lib/statusInfo';

const DeviceHealthGrid = ({
  devices,
  onSelectIncident,
}: {
  devices: DeviceHealth[];
  onSelectIncident: (incidentId: string) => void;
}) => {
  if (devices.length === 0) return null;

  return (
    <div>
      <h3 style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.75rem' }}>
        All Tailnet Devices
      </h3>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
          gap: '0.75rem',
          marginBottom: '1.5rem',
        }}
      >
        {devices.map((device) => {
          const { label, color } = STATUS_INFO[device.status] ?? { label: device.status, color: 'var(--text-secondary)' };
          const clickable = !!device.incident;
          return (
            <div
              key={device.id}
              className="ts-panel"
              onClick={() => device.incident && onSelectIncident(device.incident.id)}
              style={{
                padding: '0.875rem 1rem',
                cursor: clickable ? 'pointer' : 'default',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.375rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span className={`status-dot ${device.status}`}></span>
                <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {device.name}
                </span>
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {device.addresses[0] || device.hostname || '—'}
              </span>
              <span style={{ fontSize: '0.75rem', color }}>{label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default DeviceHealthGrid;
