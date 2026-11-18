import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AlertTriangle, Pause, Play, RotateCcw, ShieldAlert, SkipForward } from 'lucide-react';
import { apiClient } from '../services/api/client';
import type { SimulationFrame, SimulationScript, UtteranceView } from '../types';
import { EmptyState, ErrorBanner, Skeleton } from '../components/ui/States';
import { TacticTranscript } from '../components/tactics/TacticTranscript';
import { CANONICAL_STAGES } from '../components/tactics/segments';
import {
  BAND_BG, BAND_TEXT, SPEEDS, contributionDelta, gaugeFraction, newlyReached, nextStep,
} from './simulation_view';

const focusRing = 'focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary';
const STAGE_NAME: Record<string, string> = {
  AUTHORITY: 'Authority', ALLEGATION: 'Allegation', THREAT: 'Threat', ISOLATION: 'Isolation', URGENCY: 'Urgency', DEMAND: 'Demand',
};

export const SimulatedLiveCall: React.FC = () => {
  const [scripts, setScripts] = useState<SimulationScript[] | null>(null);
  const [name, setName] = useState<string | null>(null);
  const [step, setStep] = useState(0);
  const [frame, setFrame] = useState<SimulationFrame | null>(null);
  const [previous, setPrevious] = useState<SimulationFrame | null>(null);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const request = useRef(0);

  const loadScripts = useCallback(async () => {
    setError(null);
    try {
      const list = await apiClient.listSimulations();
      setScripts(list);
      setName(prev => prev ?? list[0]?.name ?? null);
    } catch (e: any) {
      setError(e?.message || 'Failed to load the call simulations.');
    }
  }, []);
  useEffect(() => { void loadScripts(); }, [loadScripts]);

  const script = scripts?.find(s => s.name === name) ?? null;

  const goTo = useCallback(async (n: number) => {
    if (!script) return;
    const id = ++request.current;
    setBusy(true);
    try {
      const next = await apiClient.getSimulationFrame(script, n);
      if (id !== request.current) return;
      setPrevious(prev => (n === 0 ? null : frame ?? prev));
      setFrame(next);
      setStep(n);
      setError(null);
    } catch (e: any) {
      if (id === request.current) { setPlaying(false); setError(e?.message || 'The simulated call could not be analysed.'); }
    } finally {
      if (id === request.current) setBusy(false);
    }
  }, [script, frame]);

  const reset = useCallback(() => {
    request.current += 1;
    setPlaying(false); setStep(0); setFrame(null); setPrevious(null); setError(null); setBusy(false);
  }, []);

  const choose = (n: string) => { setName(n); reset(); };

  // Playback: advance one turn per tick while playing.
  useEffect(() => {
    if (!playing || !script || busy) return;
    const upcoming = nextStep(step, script.turns);
    if (upcoming === null) { setPlaying(false); return; }
    const timer = setTimeout(() => { void goTo(upcoming); }, step === 0 ? 300 : SPEEDS[speed].ms);
    return () => clearTimeout(timer);
  }, [playing, step, busy, script, speed, goTo]);

  const togglePlay = () => {
    if (!script) return;
    if (step >= script.turns) { reset(); setPlaying(true); return; }
    setPlaying(p => !p);
  };

  const utterances: UtteranceView[] = useMemo(
    () => (frame?.utterances ?? []).map(u => ({ ...u, id: u.idx, t_start_sec: null, language: null })), [frame]);
  const justLit = useMemo(() => newlyReached(previous, frame), [previous, frame]);
  const delta = useMemo(() => contributionDelta(previous, frame), [previous, frame]);
  const finished = !!script && step >= script.turns;

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto space-y-6">
      <div role="note" className="bg-risk-high/10 border-2 border-risk-high/40 rounded-lg p-4 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-risk-high shrink-0 mt-0.5" aria-hidden="true" />
        <p className="text-xs text-text-primary font-medium">
          <strong>Simulation:</strong> scripted transcript playback. VIGIL does not intercept or listen to real calls. The text below is synthetic and the risk indicator is an experimental heuristic, not a probability.
        </p>
      </div>

      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text-primary">Simulated Call Analysis</h1>
          <p className="text-sm text-text-secondary mt-1">
            Each turn of a scripted call is analysed by the real pipeline as it arrives: stages light up, the risk indicator moves and guidance appears in English and Hindi.
          </p>
        </div>
        {script && (
          <div className="flex flex-wrap items-center gap-2">
            <label className="text-xs text-text-secondary flex items-center gap-2">
              Script
              <select
                value={name ?? ''} onChange={e => choose(e.target.value)}
                className={`bg-bg-card border border-border-subtle rounded-md px-2 py-2 text-sm text-text-primary ${focusRing}`}
              >
                {scripts!.map(s => <option key={s.name} value={s.name}>{s.title}</option>)}
              </select>
            </label>
            <button type="button" onClick={togglePlay} disabled={busy && !playing}
              className={`inline-flex items-center gap-2 bg-accent-primary hover:bg-sky-400 text-bg-main font-semibold px-4 py-2 rounded-md text-sm disabled:opacity-50 ${focusRing}`}>
              {playing ? <Pause className="w-4 h-4" aria-hidden="true" /> : <Play className="w-4 h-4" aria-hidden="true" />}
              <span>{playing ? 'Pause' : finished ? 'Play again' : step === 0 ? 'Play' : 'Resume'}</span>
            </button>
            <button type="button" onClick={() => { setPlaying(false); void goTo(step + 1); }} disabled={busy || finished}
              className={`inline-flex items-center gap-2 border border-border-subtle text-text-primary px-3 py-2 rounded-md text-sm hover:bg-bg-card disabled:opacity-50 ${focusRing}`}>
              <SkipForward className="w-4 h-4" aria-hidden="true" /><span>Next turn</span>
            </button>
            <button type="button" onClick={reset}
              className={`inline-flex items-center gap-2 border border-border-subtle text-text-primary px-3 py-2 rounded-md text-sm hover:bg-bg-card ${focusRing}`}>
              <RotateCcw className="w-4 h-4" aria-hidden="true" /><span>Reset</span>
            </button>
            <label className="text-xs text-text-secondary flex items-center gap-2">
              Speed
              <select value={speed} onChange={e => setSpeed(Number(e.target.value))}
                className={`bg-bg-card border border-border-subtle rounded-md px-2 py-2 text-sm text-text-primary ${focusRing}`}>
                {SPEEDS.map((s, i) => <option key={s.label} value={i}>{s.label}</option>)}
              </select>
            </label>
          </div>
        )}
      </div>

      {error && <ErrorBanner message={error} onRetry={scripts ? () => void goTo(Math.max(step, 1)) : loadScripts} />}
      {scripts === null && !error ? <Skeleton rows={3} label="Loading the simulations" /> : scripts && scripts.length === 0 ? (
        <EmptyState title="No simulations available" />
      ) : script && (
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4 min-w-0">
            <p className="text-xs text-text-secondary">{script.description}</p>
            <p className="text-xs font-mono text-text-muted" role="status" aria-live="polite">
              Turn {step} of {script.turns}{finished ? ' · script finished' : ''}
            </p>

            {frame && frame.injection_flags.length > 0 && (
              <div role="alert" className="flex items-start gap-2 rounded-lg border-2 border-risk-critical/60 bg-risk-critical/10 p-3 text-xs text-text-primary">
                <ShieldAlert className="w-4 h-4 text-risk-critical shrink-0 mt-0.5" aria-hidden="true" />
                <span>
                  <strong>Manipulation attempt detected and ignored.</strong> Text in this call tries to instruct the analyser ({frame.injection_flags.join(', ')}). It cannot lower the risk and is shown as a warning sign.
                </span>
              </div>
            )}

            {frame ? <TacticTranscript utterances={utterances} /> : (
              <div className="rounded-lg border border-dashed border-border-subtle p-8 text-center text-xs text-text-muted">
                Press Play (or Next turn) to start the scripted call.
              </div>
            )}
          </div>

          <div className="space-y-4 min-w-0">
            <section aria-labelledby="sim-stages" className="bg-bg-card border border-border-subtle rounded-lg p-4 space-y-3">
              <h2 id="sim-stages" className="text-sm font-semibold text-text-primary">Playbook stages</h2>
              <ol className="grid grid-cols-2 gap-2">
                {CANONICAL_STAGES.map((stage, i) => {
                  const s = frame?.stages.find(x => x.stage === stage);
                  const on = !!s?.reached;
                  return (
                    <li key={stage}
                      className={`rounded-md border px-2 py-1.5 text-xs flex items-center justify-between transition-colors ${
                        on ? 'border-accent-primary bg-accent-primary/15 text-text-primary font-semibold'
                           : 'border-border-subtle text-text-muted'} ${justLit.includes(stage) ? 'ring-2 ring-accent-primary' : ''}`}>
                      <span>{i + 1}. {STAGE_NAME[stage]}</span>
                      <span className="font-mono text-[10px]">{on ? `turn ${(s?.first_turn ?? 0) + 1}` : 'not yet'}</span>
                    </li>
                  );
                })}
              </ol>
            </section>

            <section aria-labelledby="sim-risk" className="bg-bg-card border border-border-subtle rounded-lg p-4 space-y-3">
              <h2 id="sim-risk" className="text-sm font-semibold text-text-primary">Risk indicator (heuristic)</h2>
              <div className="flex items-end justify-between">
                <span className={`text-3xl font-mono font-bold ${frame ? BAND_TEXT[frame.risk.band] : 'text-text-muted'}`}>{frame ? frame.risk.score : 0}</span>
                <span className={`text-xs font-mono font-bold ${frame ? BAND_TEXT[frame.risk.band] : 'text-text-muted'}`}>{frame ? frame.risk.band : 'LOW'}</span>
              </div>
              <div role="meter" aria-label="Risk indicator, an experimental heuristic" aria-valuemin={0} aria-valuemax={100}
                aria-valuenow={frame?.risk.score ?? 0} aria-valuetext={`${frame?.risk.score ?? 0} out of 100, ${frame?.risk.band ?? 'LOW'}`}
                className="h-3 rounded-full bg-bg-elevated border border-border-subtle overflow-hidden">
                <div className={`h-full transition-all duration-500 motion-reduce:transition-none ${frame ? BAND_BG[frame.risk.band] : 'bg-risk-low'}`}
                  style={{ width: `${gaugeFraction(frame?.risk.score ?? 0) * 100}%` }} />
              </div>
              {frame && frame.risk.contributions.length > 0 && (
                <div>
                  <h3 className="text-[11px] uppercase text-text-muted mb-1">What adds to the score</h3>
                  <ul className="space-y-1">
                    {frame.risk.contributions.map((c, i) => (
                      <li key={i} className={`text-[11px] rounded px-1.5 py-1 ${delta.some(d => d.factor === c.factor && d.evidence_ref === c.evidence_ref) ?'bg-accent-primary/10 border border-accent-primary/40' : ''} text-text-secondary`}>
                        <span className="font-mono text-text-primary">{c.contribution > 0 ? '+' : ''}{c.contribution}</span> {c.explanation}
                      </li>
                    ))}
                  </ul>
                  <p className="text-[10px] text-text-muted mt-1">The contributions sum exactly to the score.</p>
                </div>
              )}
            </section>

            <section aria-labelledby="sim-guide" className="bg-bg-card border border-border-subtle rounded-lg p-4 space-y-3">
              <h2 id="sim-guide" className="text-sm font-semibold text-text-primary">Guidance</h2>
              {frame ? (
                <div className="space-y-3">
                  <ul className="space-y-1.5" lang="en">
                    {frame.guidance.en.map((g, i) => <li key={i} className="text-xs text-text-primary border-l-2 border-accent-primary pl-2">{g}</li>)}
                  </ul>
                  <ul className="space-y-1.5" lang="hi">
                    {frame.guidance.hi.map((g, i) => <li key={i} className="text-xs text-text-primary border-l-2 border-accent-secondary pl-2">{g}</li>)}
                  </ul>
                </div>
              ) : <p className="text-xs text-text-muted">Guidance appears as the call unfolds.</p>}
              <p className="text-[10px] text-text-muted">General safety advice in a simulation, not a legal or financial instruction.</p>
            </section>
          </div>
        </div>
      )}
    </div>
  );
};
