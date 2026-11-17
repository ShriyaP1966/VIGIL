import React from 'react';
import { Handle, Position, type NodeProps, type Node } from '@xyflow/react';
import { Building2, Globe, Link2, Mail, Phone, ShieldAlert, Wallet, CircleHelp } from 'lucide-react';
import { RISK_COLORS, type NodeKind, type VigilNodeData } from './graph_layout';

/** Blueprint §12.5: incident = square, phone = circle, email = hexagon, domain = diamond,
 * URL = rounded rectangle, payment handle = wallet, organisation = building. Border colour = risk band. */
const ICONS: Record<NodeKind, React.ComponentType<{ className?: string }>> = {
  incident: ShieldAlert,
  phone: Phone,
  upi_handle: Wallet,
  email: Mail,
  domain: Globe,
  url: Link2,
  organisation: Building2,
  other: CircleHelp,
};

const KIND_NAMES: Record<NodeKind, string> = {
  incident: 'Incident',
  phone: 'Phone',
  upi_handle: 'Payment handle',
  email: 'Email',
  domain: 'Domain',
  url: 'URL',
  organisation: 'Claimed organisation',
  other: 'Entity',
};

function shapeStyle(kind: NodeKind, borderColor: string): React.CSSProperties {
  const base: React.CSSProperties = { borderColor, borderWidth: 2, borderStyle: 'solid' };
  switch (kind) {
    case 'phone':
    case 'upi_handle':
      return { ...base, borderRadius: '9999px' };
    case 'email':
      return { ...base, clipPath: 'polygon(25% 5%, 75% 5%, 100% 50%, 75% 95%, 25% 95%, 0 50%)', borderWidth: 0, background: borderColor + '33' };
    case 'domain':
      return { ...base, clipPath: 'polygon(50% 0, 100% 50%, 50% 100%, 0 50%)', borderWidth: 0, background: borderColor + '33' };
    case 'url':
    case 'organisation':
      return { ...base, borderRadius: '10px' };
    default:
      return { ...base, borderRadius: '4px' };
  }
}

export const VigilNode: React.FC<NodeProps<Node<VigilNodeData>>> = ({ data, selected }) => {
  const { kind, label, riskBand, graphNode } = data;
  const Icon = ICONS[kind];
  const isIncident = kind === 'incident';
  const borderColor = isIncident
    ? RISK_COLORS[riskBand ?? 'LOW']
    : kind === 'other' ? '#64748B' : '#94A3B8';

  return (
    <div className="flex flex-col items-center gap-1.5" style={{ width: isIncident ? 220 : 150 }}>
      <Handle type="target" position={Position.Top} className="!bg-transparent !border-0" />
      <div
        className={`flex items-center justify-center bg-bg-card ${isIncident ? 'w-14 h-14' : 'w-11 h-11'} ${selected ? 'ring-2 ring-accent-primary' : ''}`}
        style={shapeStyle(kind, borderColor)}
        aria-hidden="true"
      >
        <Icon className={isIncident ? 'w-6 h-6 text-text-primary' : 'w-5 h-5 text-text-secondary'} />
      </div>
      <div className="text-center leading-tight">
        <div className="text-[10px] uppercase tracking-wider font-mono text-text-muted">{KIND_NAMES[kind]}</div>
        <div className={`text-[11px] ${isIncident ? 'font-semibold text-text-primary' : 'font-mono text-text-secondary'} break-words`}>
          {label}
        </div>
        {isIncident && graphNode.details?.risk_score !== undefined && (
          <div className="text-[10px] font-mono" style={{ color: borderColor }}>
            Risk {graphNode.details.risk_score} · {riskBand}
          </div>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-transparent !border-0" />
    </div>
  );
};
