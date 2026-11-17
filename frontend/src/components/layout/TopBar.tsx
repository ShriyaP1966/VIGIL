import React from 'react';
import { Search, Plus, Radio, Server } from 'lucide-react';
import { ApiMode } from '../../services/api/client';
import { ViewMode } from '../../types';

interface TopBarProps {
  apiMode: ApiMode;
  onNewInvestigation: () => void;
  onSearch?: (term: string) => void;
}

export const TopBar: React.FC<TopBarProps> = ({ apiMode, onNewInvestigation }) => {
  return (
    <header className="h-16 bg-bg-sidebar border-b border-border-subtle flex items-center justify-between px-6 gap-4">
      {/* Search Bar */}
      <div className="flex-1 max-w-md relative">
        <Search className="w-4 h-4 text-text-muted absolute left-3 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          disabled
          aria-label="Search (available in a later phase)"
          title="Search arrives in a later phase"
          placeholder="Search arrives in a later phase"
          className="w-full bg-bg-card border border-border-subtle rounded-md pl-9 pr-4 py-1.5 text-sm text-text-primary placeholder:text-text-muted cursor-not-allowed opacity-60"
        />
      </div>

      {/* Right Controls: Mode Badge & New Action */}
      <div className="flex items-center gap-4">
        {/* Operating Mode Badge */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-bg-card border border-border-subtle text-xs">
          {apiMode === 'live' ? (
            <>
              <span className="w-2 h-2 rounded-full bg-risk-low animate-pulse"></span>
              <span className="text-text-primary font-medium flex items-center gap-1.5">
                <Server className="w-3.5 h-3.5 text-risk-low" />
                Live analysis
              </span>
            </>
          ) : apiMode === 'waking' ? (
            <>
              <span className="w-2 h-2 rounded-full bg-risk-elevated animate-pulse"></span>
              <span className="text-text-secondary flex items-center gap-1.5">
                <Radio className="w-3.5 h-3.5 text-risk-elevated" />
                Waking analysis server… (precomputed data shown)
              </span>
            </>
          ) : (
            <>
              <span className="w-2 h-2 rounded-full bg-accent-secondary"></span>
              <span className="text-text-secondary flex items-center gap-1.5">
                <Radio className="w-3.5 h-3.5 text-accent-secondary" />
                Hosted demo: precomputed synthetic data
              </span>
            </>
          )}
        </div>

        {/* Quick New Investigation Button */}
        <button
          onClick={onNewInvestigation}
          className="flex items-center gap-2 bg-accent-primary hover:bg-sky-400 text-bg-main font-semibold px-3.5 py-1.5 rounded-md text-sm transition-colors shadow-sm"
        >
          <Plus className="w-4 h-4" />
          <span>New Investigation</span>
        </button>
      </div>
    </header>
  );
};
