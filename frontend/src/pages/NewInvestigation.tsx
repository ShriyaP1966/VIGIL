import React, { useState } from 'react';
import { Send, FileText, Phone, MessageSquare, Globe, Sparkles, AlertCircle } from 'lucide-react';
import { apiClient, ApiMode } from '../services/api/client';

interface NewInvestigationProps {
  apiMode: ApiMode;
  onSuccess: (id: number) => void;
}

const MAX_EVIDENCE_CHARS = 20_000; // keep in sync with backend MAX_EVIDENCE_CHARS

export const NewInvestigation: React.FC<NewInvestigationProps> = ({ apiMode, onSuccess }) => {
  const live = apiMode === 'live';
  const [title, setTitle] = useState('');
  const [sourceChannel, setSourceChannel] = useState('call');
  const [language, setLanguage] = useState('hi-Latn');
  const [evidenceType, setEvidenceType] = useState('transcript');
  const [text, setText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const samples = [
    {
      label: 'Digital Arrest Call (CBI Impersonation)',
      channel: 'call',
      lang: 'hi-Latn',
      type: 'transcript',
      title: 'Digital Arrest Threat — CBI Officer Impersonation',
      text: 'Main CBI officer Rajesh Sharma bol raha hoon. Aapke Aadhaar card par illegal parcel Mumbai customs ne pakda hai. Is parcel mein drugs aur money laundering ke documents hain. Agar aap turant arrest warrant se bachna chahte hain to apni verification deposit 50000 rupees verify-cbi@okhdfcbank par transfer kijiye. Kisi ko mat batana, aap video call surveillance par hain.'
    },
    {
      label: 'Customs Parcel Scam (Same UPI)',
      channel: 'call',
      lang: 'en',
      type: 'transcript',
      title: 'Customs Contraband Parcel Demand',
      text: 'This is Mumbai Customs Department. A package registered in your name contains counterfeit currency and passport copies. An FIR has been registered. You are directed to transfer clearance charges immediately to verify-cbi@okhdfcbank within 30 minutes.'
    },
    {
      label: 'Legitimate Branch Notification (Negative Control)',
      channel: 'sms',
      lang: 'en',
      type: 'message',
      title: 'HDFC Official Branch Alert',
      text: 'Dear Customer, your monthly bank statement has been dispatched to your registered email address. For inquiries, visit your nearest bank branch with original photo ID or call official national helpline 1930. Never share passwords or PINs.'
    }
  ];

  const handleLoadSample = (sample: typeof samples[0]) => {
    setTitle(sample.title);
    setSourceChannel(sample.channel);
    setLanguage(sample.lang);
    setEvidenceType(sample.type);
    setText(sample.text);
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !text.trim()) {
      setError('Please provide a title and evidence content.');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const res = await apiClient.createIncident({
        title,
        source_channel: sourceChannel,
        language,
        evidence: [{ text, type: evidenceType }]
      });
      onSuccess(res.id);
    } catch (err: any) {
      setError(err.message || 'Failed to create investigation');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text-primary">New Investigation</h1>
        <p className="text-sm text-text-secondary mt-1">
          Paste a synthetic call transcript, message or payment request. VIGIL extracts identifiers and checks
          whether the same identifier appears in other incidents.
        </p>
      </div>

      <div className="bg-bg-elevated/40 border border-border-subtle rounded-lg p-3 text-xs text-text-secondary flex gap-2">
        <AlertCircle className="w-4 h-4 shrink-0 text-accent-primary mt-0.5" aria-hidden="true" />
        <span>Synthetic data only: do not enter real personal information, real phone numbers or real account details.</span>
      </div>

      {!live && (
        <div role="status" className="bg-risk-elevated/10 border border-risk-elevated/30 rounded-lg p-3 text-xs text-risk-elevated flex gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" aria-hidden="true" />
          <span>
            {apiMode === 'waking'
              ? 'The live analysis server is not reachable yet (a free host may be waking up). You can load a sample, but analysis starts when the server is live.'
              : 'This hosted demo shows precomputed synthetic data. Analysing new text needs the live backend, so submitting is disabled.'}
          </span>
        </div>
      )}

      {/* Quick Sample Presets */}
      <div className="bg-bg-card border border-border-subtle rounded-lg p-4 space-y-2">
        <div className="text-xs font-semibold text-text-muted uppercase tracking-wider flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-accent-primary" />
          Load Preconfigured Synthetic Benchmark Sample
        </div>
        <div className="flex flex-wrap gap-2">
          {samples.map((s, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleLoadSample(s)}
              className="text-xs bg-bg-elevated hover:bg-border-subtle text-text-secondary hover:text-text-primary px-3 py-1.5 rounded-md border border-border-subtle transition-colors"
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Intake Form */}
      <form onSubmit={handleSubmit} className="bg-bg-card border border-border-subtle rounded-lg p-6 space-y-5">
        {error && (
          <div className="p-3 bg-risk-critical/10 border border-risk-critical/30 rounded-md text-xs text-risk-critical flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div>
          <label className="block text-xs font-semibold text-text-muted uppercase tracking-wider mb-1.5">
            Investigation Case Title *
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g., Digital Arrest Call Impersonating Mumbai Cyber Cell"
            className="w-full bg-bg-main border border-border-subtle rounded-md px-3.5 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-primary"
            required
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-semibold text-text-muted uppercase tracking-wider mb-1.5">
              Source Channel
            </label>
            <select
              value={sourceChannel}
              onChange={(e) => setSourceChannel(e.target.value)}
              className="w-full bg-bg-main border border-border-subtle rounded-md px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-primary"
            >
              <option value="call">Phone Call (Transcript)</option>
              <option value="sms">SMS / WhatsApp Message</option>
              <option value="email">Email</option>
              <option value="web">Web Form / Payment Link</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-text-muted uppercase tracking-wider mb-1.5">
              Communication Language
            </label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="w-full bg-bg-main border border-border-subtle rounded-md px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-primary"
            >
              <option value="hi-Latn">Hinglish / Romanised Hindi</option>
              <option value="en">English</option>
              <option value="hi">Hindi (Devanagari)</option>
              <option value="mr">Marathi</option>
              <option value="mixed">Mixed / Multilingual</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-text-muted uppercase tracking-wider mb-1.5">
              Evidence Type
            </label>
            <select
              value={evidenceType}
              onChange={(e) => setEvidenceType(e.target.value)}
              className="w-full bg-bg-main border border-border-subtle rounded-md px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-primary"
            >
              <option value="transcript">Transcript with turns</option>
              <option value="message">Pasted text / SMS</option>
              <option value="payment_request">UPI / Bank Request</option>
              <option value="url">Phishing URL string</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-text-muted uppercase tracking-wider mb-1.5">
            Raw Evidence Content *
          </label>
          <textarea
            rows={8}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste transcript turns, message body, or transaction narrative here..."
            maxLength={MAX_EVIDENCE_CHARS}
            className="w-full bg-bg-main border border-border-subtle rounded-md p-3.5 text-sm text-text-primary font-mono focus:outline-none focus:border-accent-primary leading-relaxed"
            required
          />
          <div className="flex justify-between items-center text-[11px] text-text-muted mt-1.5">
            <span>OTPs, passwords, PINs, CVVs, card and Aadhaar numbers are removed before storage (best effort).</span>
            <span>{text.length} / {MAX_EVIDENCE_CHARS} characters</span>
          </div>
        </div>

        <div className="pt-2 flex justify-end">
          <button
            type="submit"
            disabled={submitting || !live}
            className="flex items-center gap-2 bg-accent-primary hover:bg-sky-400 text-bg-main font-semibold px-6 py-2.5 rounded-md text-sm transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send className="w-4 h-4" aria-hidden="true" />
            <span>{submitting ? 'Analysing…' : 'Analyse evidence'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};
