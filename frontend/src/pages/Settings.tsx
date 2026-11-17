import React, { useState } from 'react';
import { Settings as SettingsIcon, Trash2, AlertTriangle, CheckCircle, Shield } from 'lucide-react';
import { apiClient } from '../services/api/client';

export const Settings: React.FC = () => {
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
    <div className="p-8 max-w-4xl mx-auto space-y-8">
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
            • <strong>Offline Mode (Default):</strong> Pure deterministic extraction using local regex, gazetteers, and scikit-learn models. No external API calls are made.
          </p>
          <p>
            • <strong>Zero PII Retention:</strong> Phone numbers, UPI handles, and emails are hashed for cross-incident matching and masked in UI displays. Passwords and OTP tokens are never stored.
          </p>
          <p>
            • <strong>Local Data Control:</strong> All SQLite database records exist exclusively on this device.
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
          disabled={clearing}
          className="flex items-center gap-2 bg-risk-critical/20 hover:bg-risk-critical/30 text-risk-critical border border-risk-critical/40 px-4 py-2 rounded-md text-xs font-semibold transition-colors disabled:opacity-50"
        >
          <Trash2 className="w-4 h-4" />
          <span>{clearing ? 'Clearing Data...' : 'Clear All Local Data'}</span>
        </button>
      </div>
    </div>
  );
};
