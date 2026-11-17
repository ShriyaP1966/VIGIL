import React, { useState } from 'react';
import { Settings as SettingsIcon, Trash2, AlertTriangle, CheckCircle, Shield } from 'lucide-react';
import { apiClient, ApiMode } from '../services/api/client';

export const Settings: React.FC<{ apiMode: ApiMode }> = ({ apiMode }) => {
  const live = apiMode === 'live';
  const [clearing, setClearing] = useState(false);
  const [cleared, setCleared] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleClearData = async () => {
    if (!window.confirm('Are you sure you want to permanently erase all local investigation and association records?')) {
      return;
    }
    setClearing(true);
    setError(null);
    try {
      await apiClient.clearAllData();
      setCleared(true);
    } catch (err: any) {
      setError(err.message || 'Failed to clear local data');
    } finally {
      setClearing(false);
    }
  };

  return (
    <div className="p-4 sm:p-8 max-w-4xl mx-auto space-y-6 sm:space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text-primary">System Settings</h1>
        <p className="text-sm text-text-secondary mt-1">
          Configure processing modes, inspect operational parameters, and manage local data retention.
        </p>
      </div>

      {/* Mode & Privacy Cards */}
      <div className="bg-bg-card border border-border-subtle rounded-lg p-6 space-y-4">
        <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
          <Shield className="w-4 h-4 text-accent-primary" />
          Processing Mode & Privacy Guarantees (§4.1, §10)
        </h3>
        <div className="space-y-3 text-xs text-text-secondary">
          <p>
            • <strong>Current mode:</strong>{' '}
            {apiMode === 'live'
              ? 'Live analysis backend (offline engine: regex and gazetteer rules, no external API calls).'
              : apiMode === 'waking'
                ? 'Waiting for the live backend; precomputed synthetic data is shown meanwhile.'
                : 'Hosted demo: precomputed synthetic data. Nothing you do here is stored or analysed.'}
          </p>
          <p>
            • <strong>Offline by default:</strong> the engine needs no API keys and makes no external calls.
          </p>
          <p>
            • <strong>Identifier handling:</strong> identifiers are stored in normalised form so exact matches can be found,
            and masked in this interface. Passwords and OTPs are not collected. Use synthetic data only.
          </p>
          <p>
            • <strong>Local data control:</strong> in live mode, records are kept in the backend's SQLite database
            and can be erased below.
          </p>
        </div>
      </div>

      {/* Danger Zone: Clear Local Data */}
      <div className="bg-bg-card border border-risk-critical/30 rounded-lg p-6 space-y-4">
        <div className="flex items-center gap-2 text-risk-critical font-bold text-sm">
          <AlertTriangle className="w-4 h-4" />
          <span>Danger Zone: Local Data Retention</span>
        </div>
        <p className="text-xs text-text-secondary">
          Erase all incidents, extracted entities, associations, and analyst review records from local storage.
        </p>

        {cleared && (
          <div className="p-3 bg-accent-secondary/10 border border-accent-secondary/30 rounded text-xs text-accent-secondary flex items-center gap-2">
            <CheckCircle className="w-4 h-4" />
            <span>All local investigation records have been cleared.</span>
          </div>
        )}

        {error && (
          <div className="p-3 bg-risk-critical/10 border border-risk-critical/30 rounded text-xs text-risk-critical">
            {error}
          </div>
        )}

        <button
          onClick={handleClearData}
          disabled={clearing || !live}
          className="flex items-center gap-2 bg-risk-critical/20 hover:bg-risk-critical/30 text-risk-critical border border-risk-critical/40 px-4 py-2 rounded-md text-xs font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Trash2 className="w-4 h-4" aria-hidden="true" />
          <span>{clearing ? 'Clearing…' : 'Clear all local data'}</span>
        </button>
        {!live && (
          <p className="text-[11px] text-text-muted">
            Available only when connected to the live backend. The hosted demo stores no data.
          </p>
        )}
      </div>
    </div>
  );
};
