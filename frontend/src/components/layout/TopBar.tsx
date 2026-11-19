import React from 'react';
import { Search, Plus, Radio, Server, Menu } from 'lucide-react';
import { ApiMode } from '../../services/api/client';

interface TopBarProps {
  apiMode: ApiMode;
  onNewInvestigation: () => void;
  /** Opens the navigation drawer (only shown below md, where the sidebar is a drawer). */
  onOpenMenu?: () => void;
  menuOpen?: boolean;
  onSearch?: (term: string) => void;
}

const MODE_LABEL: Record<ApiMode, { short: string; long: string }> = {
  live: { short: 'Live', long: 'Live analysis' },
  waking: { short: 'Waking', long: 'Waking analysis server… (precomputed data shown)' },
  static: { short: 'Synthetic demo', long: 'Hosted demo: precomputed synthetic data' },
};

export const TopBar: React.FC<TopBarProps> = ({ apiMode, onNewInvestigation, onOpenMenu, menuOpen = false }) => {
  const label = MODE_LABEL[apiMode] ?? MODE_LABEL.static;
  return (
    <header className="h-16 shrink-0 bg-bg-sidebar border-b border-border-subtle flex items-center justify-between px-3 sm:px-6 gap-2 sm:gap-4">
      {/* Hamburger: only where the sidebar is a drawer */}
      <button
        type="button"
        onClick={onOpenMenu}
        aria-label="Open navigation menu"
        aria-expanded={menuOpen}
        aria-controls="app-sidebar"
        className="md:hidden shrink-0 p-2 -ml-1 rounded-md text-text-secondary hover:text-text-primary hover:bg-bg-card focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary"
      >
        <Menu className="w-5 h-5" aria-hidden="true" />
      </button>

      {/* Search Bar: hidden on phones (search lives on the Investigations page) */}
      <div className="hidden sm:block flex-1 max-w-md min-w-0 relative">
        <Search className="w-4 h-4 text-text-muted absolute left-3 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          disabled
          aria-label="Search: use the Investigations page"
          title="Search and filters are on the Investigations page"
          placeholder="Search: see Investigations"
          className="w-full bg-bg-card border border-border-subtle rounded-md pl-9 pr-4 py-1.5 text-sm text-text-primary placeholder:text-text-muted cursor-not-allowed opacity-60"
        />
      </div>

      {/* Right Controls: Mode Badge & New Action */}
      <div className="flex items-center gap-2 sm:gap-4 min-w-0 ml-auto">
        {/* Operating Mode Badge: short label on phones, full text from lg */}
        <div
          className="flex items-center gap-2 px-2.5 sm:px-3 py-1.5 rounded-full bg-bg-card border border-border-subtle text-xs min-w-0"
          title={label.long}
        >
          {apiMode === 'live' ? (
            <>
              <span className="w-2 h-2 shrink-0 rounded-full bg-risk-low animate-pulse"></span>
              <span className="text-text-primary font-medium flex items-center gap-1.5 min-w-0">
                <Server className="hidden sm:block w-3.5 h-3.5 shrink-0 text-risk-low" />
                <span className="lg:hidden">{label.short}</span>
                <span className="hidden lg:inline">{label.long}</span>
              </span>
            </>
          ) : apiMode === 'waking' ? (
            <>
              <span className="w-2 h-2 shrink-0 rounded-full bg-risk-elevated animate-pulse"></span>
              <span className="text-text-secondary flex items-center gap-1.5 min-w-0">
                <Radio className="hidden sm:block w-3.5 h-3.5 shrink-0 text-risk-elevated" />
                <span className="lg:hidden">{label.short}</span>
                <span className="hidden lg:inline">{label.long}</span>
              </span>
            </>
          ) : (
            <>
              <span className="w-2 h-2 shrink-0 rounded-full bg-accent-secondary"></span>
              <span className="text-text-secondary flex items-center gap-1.5 min-w-0">
                <Radio className="hidden sm:block w-3.5 h-3.5 shrink-0 text-accent-secondary" />
                <span className="lg:hidden">{label.short}</span>
                <span className="hidden lg:inline">{label.long}</span>
              </span>
            </>
          )}
        </div>

        {/* Quick New Investigation Button: icon-only on phones */}
        <button
          type="button"
          onClick={onNewInvestigation}
          aria-label="New Investigation"
          title="New Investigation"
          className="shrink-0 flex items-center gap-2 bg-accent-primary hover:bg-sky-400 text-bg-main font-semibold p-2 sm:px-3.5 sm:py-1.5 rounded-md text-sm transition-colors shadow-sm"
        >
          <Plus className="w-4 h-4" aria-hidden="true" />
          <span className="hidden sm:inline">New Investigation</span>
        </button>
      </div>
    </header>
  );
};
