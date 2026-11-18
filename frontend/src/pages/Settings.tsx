import React, { useState } from 'react';
import { AlertTriangle, Eye, Shield, Trash2 } from 'lucide-react';
import { apiClient, ApiMode } from '../services/api/client';
import { useToast } from '../components/ui/Toast';

const focusRing = 'focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary';

const MODE_TEXT: Record<ApiMode, string> = {
  live: 'Live analysis backend. The engine is rule-based and offline: no external API calls.',
  waking: 'Waiting for the live backend; precomputed synthetic data is shown meanwhile.',
  static: 'Hosted demo: precomputed synthetic data. Nothing you do here is stored or analysed.',
};

export const Settings: React.FC<{ apiMode: ApiMode }> = ({ apiMode }) => {
  const toast = useToast();
  const live = apiMode === 'live';
  const [confirming, setConfirming] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clearAll = async () => {
    setClearing(true);
    setError(null);
    try {
      await apiClient.clearAllData();
      setConfirming(false);
      toast.success('All local investigation records were erased.');
    } catch (e: any) {
      const message = e?.message || 'Failed to clear local data.';
      setError(message);
      toast.error(message);
    } finally {
      setClearing(false);
    }
  };

  return (
    <div className="p-4 sm:p-8 max-w-4xl mx-auto space-y-6 sm:space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text-primary">Settings</h1>
        <p className="text-sm text-text-secondary mt-1">
          How VIGIL processes evidence, what it keeps, and how to erase it.
        </p>
      </div>

      <section aria-labelledby="set-mode" className="bg-bg-card border border-border-subtle rounded-lg p-6 space-y-4">
        <h2 id="set-mode" className="text-sm font-semibold text-text-primary flex items-center gap-2">
          <Shield className="w-4 h-4 text-accent-primary" aria-hidden="true" />Processing mode
        </h2>
        <fieldset className="space-y-2">
          <legend className="sr-only">Processing mode</legend>
          <label className="flex items-start gap-3 rounded-md border border-accent-primary/60 bg-accent-primary/10 p-3 text-xs">
            <input type="radio" name="mode" checked readOnly className={`mt-0.5 ${focusRing}`} />
            <span>
              <strong className="text-text-primary">Offline rules (active)</strong>
              <span className="block text-text-secondary">Regex, gazetteer and a hand-written lexicon. Needs no API key and makes no network call. This is the only mode in this build.</span>
            </span>
          </label>
          <label className="flex items-start gap-3 rounded-md border border-border-subtle p-3 text-xs">
            <input type="radio" name="mode" disabled className="mt-0.5" />
            <span>
              <strong className="text-text-primary">Optional cloud extractor (not available)</strong>
              <span className="block text-text-secondary">Cut from this release. If it is ever added it will be off by default and fall back to the offline rules.</span>
            </span>
          </label>
        </fieldset>
        <p className="text-xs text-text-secondary"><strong>Right now:</strong> {MODE_TEXT[apiMode]}</p>
      </section>

      <section aria-labelledby="set-trans" className="bg-bg-card border border-border-subtle rounded-lg p-6 space-y-3">
        <h2 id="set-trans" className="text-sm font-semibold text-text-primary flex items-center gap-2">
          <Eye className="w-4 h-4 text-accent-primary" aria-hidden="true" />Transparency
        </h2>
        <ul className="space-y-2 text-xs text-text-secondary list-disc pl-5">
          <li><strong>All data is synthetic.</strong> Use synthetic text only. Nothing here is evidence about a real person or organisation.</li>
          <li><strong>Hypotheses, not findings.</strong> A campaign hypothesis groups incidents that may be related. An exact identifier match is an observation; a similar script is only a lead. An analyst decides.</li>
          <li><strong>The risk indicator is a heuristic,</strong> with a-priori weights and no calibration. It is not a probability.</li>
          <li><strong>Secrets are removed on a best-effort basis</strong> before anything is stored: OTPs, PINs, CVVs, passwords, card and Aadhaar numbers. Only counts of removals are kept.</li>
          <li><strong>Identifiers are masked</strong> on screen. Normalised values are stored in the local database so exact matches can be found.</li>
          <li><strong>Untrusted text is never rendered as HTML</strong>, and links in evidence are never fetched.</li>
          <li><strong>Simulated call analysis is a simulation:</strong> scripted text only. VIGIL does not listen to or intercept calls.</li>
        </ul>
      </section>

      <section aria-labelledby="set-danger" className="bg-bg-card border border-risk-critical/30 rounded-lg p-6 space-y-4">
        <h2 id="set-danger" className="flex items-center gap-2 text-risk-critical font-bold text-sm">
          <AlertTriangle className="w-4 h-4" aria-hidden="true" />Clear all local data
        </h2>
        <p className="text-xs text-text-secondary">
          Permanently erases every incident, evidence record, extracted identifier, association, campaign hypothesis and analyst review from the local database. This cannot be undone.
        </p>

        {error && <div role="alert" className="p-3 bg-risk-critical/10 border border-risk-critical/30 rounded text-xs text-text-primary">{error}</div>}

        {!confirming ? (
          <button
            type="button" onClick={() => setConfirming(true)} disabled={!live}
            className={`flex items-center gap-2 bg-risk-critical/20 hover:bg-risk-critical/30 text-risk-critical border border-risk-critical/40 px-4 py-2 rounded-md text-xs font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${focusRing}`}
          >
            <Trash2 className="w-4 h-4" aria-hidden="true" /><span>Clear all local data</span>
          </button>
        ) : (
          <div role="alertdialog" aria-labelledby="confirm-title" className="rounded-md border border-risk-critical/50 p-4 space-y-3">
            <p id="confirm-title" className="text-xs text-text-primary font-semibold">Erase everything now?</p>
            <div className="flex gap-2">
              <button type="button" onClick={clearAll} disabled={clearing} autoFocus
                className={`bg-risk-critical text-bg-main px-4 py-2 rounded-md text-xs font-semibold disabled:opacity-50 ${focusRing}`}>
                {clearing ? 'Erasing…' : 'Yes, erase all data'}
              </button>
              <button type="button" onClick={() => setConfirming(false)} disabled={clearing}
                className={`border border-border-subtle text-text-primary px-4 py-2 rounded-md text-xs ${focusRing}`}>
                Cancel
              </button>
            </div>
          </div>
        )}
        {!live && (
          <p className="text-[11px] text-text-muted">
            Available only when connected to the live backend. The hosted demo stores no data, so there is nothing to clear.
          </p>
        )}
      </section>
    </div>
  );
};
