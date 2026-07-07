export interface ProposedFix {
  description: string;
  steps: string[];
  markdown?: string;
  destructiveActions?: string[];
  targetNode?: string;
}

export interface Incident {
  id: string;
  service: string;
  serviceType: string;
  status: 'online' | 'issue' | 'warning' | 'resolving' | 'resolved';
  logs: string[];
  confidence: number;
  proposedFix: ProposedFix | null;
  jobId?: string;
  detectedAt?: string;
}

export interface DeviceHealth {
  id: string;
  name: string;
  hostname: string;
  addresses: string[];
  os: string;
  lastSeen: string | null;
  status: 'online' | 'issue' | 'warning' | 'resolving' | 'resolved' | 'offline';
  incident: Incident | null;
}
