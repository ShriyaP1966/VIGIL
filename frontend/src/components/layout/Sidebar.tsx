import React from 'react';
import { 
  ShieldAlert, 
  LayoutDashboard, 
  PlusCircle, 
  Network, 
  Layers, 
  FlaskConical, 
  PhoneCall, 
  FileText, 
  Settings as SettingsIcon
} from 'lucide-react';
import { ViewMode } from '../../types';

interface SidebarProps {
  currentView: ViewMode;
  onNavigate: (view: ViewMode) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentView, onNavigate }) => {
  const navItems = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'new_investigation', label: 'New Investigation', icon: PlusCircle },
    { id: 'graph', label: 'Intelligence Graph', icon: Network },
    { id: 'campaigns', label: 'Campaigns', icon: Layers },
    { id: 'scenario_lab', label: 'Scenario Lab', icon: FlaskConical },
    { id: 'simulated_live_call', label: 'Simulated Call Analysis', icon: PhoneCall, badge: 'P1' },
    { id: 'reports', label: 'Reports', icon: FileText },
    { id: 'settings', label: 'Settings', icon: SettingsIcon },
  ];

  return (
    <aside className="w-64 bg-bg-sidebar border-r border-border-subtle flex flex-col h-screen select-none">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-6 gap-3 border-b border-border-subtle">
        <div className="w-9 h-9 rounded-lg bg-accent-primary/10 border border-accent-primary/30 flex items-center justify-center text-accent-primary font-bold shadow-sm">
          <ShieldAlert className="w-5 h-5 text-accent-primary" />
        </div>
        <div>
          <div className="flex items-center gap-1.5">
            <span className="font-bold text-base tracking-wider text-text-primary">VIGIL</span>
            <span className="text-[10px] bg-accent-primary/20 text-accent-primary px-1.5 py-0.5 rounded font-mono">v3.1</span>
          </div>
          <p className="text-[11px] text-text-muted leading-tight">Scam Intelligence</p>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentView === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id as ViewMode)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                isActive 
                  ? 'bg-bg-elevated text-accent-primary border-l-2 border-accent-primary font-semibold' 
                  : 'text-text-secondary hover:text-text-primary hover:bg-bg-card'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-accent-primary' : 'text-text-muted'}`} />
              <span className="flex-1 text-left">{item.label}</span>
              {item.badge && (
                <span className="text-[10px] font-mono uppercase bg-bg-elevated text-text-muted px-1.5 py-0.5 rounded border border-border-subtle">
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Bottom Footer Info */}
      <div className="p-4 border-t border-border-subtle bg-bg-main/50 text-[11px] text-text-muted flex flex-col gap-1 font-mono">
        <div className="flex items-center justify-between">
          <span>Branch:</span>
          <span className="text-risk-low">main only</span>
        </div>
        <div className="flex items-center justify-between">
          <span>Budget:</span>
          <span>$0 Free Stack</span>
        </div>
        <div className="flex items-center justify-between">
          <span>Mode:</span>
          <span className="text-accent-secondary">Offline-First</span>
        </div>
      </div>
    </aside>
  );
};
