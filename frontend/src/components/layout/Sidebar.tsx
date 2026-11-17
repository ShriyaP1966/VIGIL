import React, { useEffect } from 'react';
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
import { Link } from '../../router';
import { pathFor } from '../../router/routes';

interface SidebarProps {
  /** The section the current URL belongs to (null on the not-found page). */
  currentView: ViewMode | null;
  /** Called after a navigation link is followed (the mobile drawer closes itself with it). */
  onNavigate?: () => void;
  /** Below md the sidebar is a drawer: closed by default, opened from the top bar. Ignored from md up. */
  open?: boolean;
  onClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentView, onNavigate, open = false, onClose }) => {
  // Escape closes the drawer.
  useEffect(() => {
    if (!open || !onClose) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

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
    <>
    {/* Tap outside the drawer to close it (phones only) */}
    {open && (
      <div className="md:hidden fixed inset-0 z-40 bg-black/50" onClick={onClose} aria-hidden="true" data-testid="drawer-backdrop" />
    )}
    <aside
      id="app-sidebar"
      aria-label="Main navigation"
      className={`fixed inset-y-0 left-0 z-50 w-64 max-w-[85vw] transition-transform duration-200 md:static md:z-auto md:max-w-none md:translate-x-0 md:visible md:h-screen shrink-0 bg-bg-sidebar border-r border-border-subtle flex flex-col select-none ${
        open ? 'translate-x-0 visible' : '-translate-x-full invisible'
      }`}
    >
      {/* Brand Header */}
      <div className="h-16 shrink-0 flex items-center px-6 gap-3 border-b border-border-subtle">
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
            <Link
              key={item.id}
              to={pathFor(item.id as ViewMode)}
              onNavigate={onNavigate}
              aria-current={isActive ? 'page' : undefined}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary ${
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
            </Link>
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
    </>
  );
};
