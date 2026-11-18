import { describe, expect, it } from 'vitest';
import type { IncidentListItem, ScenarioInfo, ScenarioRun, SimulationFrame } from '../types';
import { DEFAULT_FILTER, bandCounts, filterIncidents, incidentCode, isFiltered } from './investigations_view';
import { checkTone, expectationSummary, formatActual, groupByCategory, sameResult } from './scenario_view';
import { contributionDelta, gaugeFraction, newlyReached, nextStep, stagesReached } from './simulation_view';

const inc = (id: number, over: Partial<IncidentListItem> = {}): IncidentListItem => ({
  id, title: `Case ${id}`, source_channel: 'call', language: 'en', status: 'open', risk_score: 10, risk_band: 'LOW',
  created_at: `2026-11-0${id}T10:00:00`, ...over,
});

describe('investigations list: search, filters and sorting', () => {
  const items = [
    inc(1, { title: 'Digital Arrest Threat — CBI Officer', risk_score: 80, risk_band: 'CRITICAL', language: 'hi-Latn' }),
    inc(2, { title: 'Customs Contraband Parcel Demand', risk_score: 56, risk_band: 'ELEVATED' }),
    inc(3, { title: 'HDFC Official Branch Alert', source_channel: 'sms', risk_score: 0, risk_band: 'LOW' }),
    inc(4, { title: 'Untitled', risk_score: undefined, risk_band: undefined }),
  ];

  it('formats case codes', () => expect(incidentCode(7)).toBe('INC-0007'));

  it('returns everything, newest first, with no filter', () => {
    expect(filterIncidents(items, DEFAULT_FILTER).map(i => i.id)).toEqual([4, 3, 2, 1]);
    expect(isFiltered(DEFAULT_FILTER)).toBe(false);
  });

  it('searches every word across code, id, title, channel, language and band', () => {
    const ids = (q: string) => filterIncidents(items, { ...DEFAULT_FILTER, q }).map(i => i.id);
    expect(ids('customs parcel')).toEqual([2]);
    expect(ids('INC-0003')).toEqual([3]);
    expect(ids('sms')).toEqual([3]);
    expect(ids('hi-latn')).toEqual([1]);
    expect(ids('critical')).toEqual([1]);
    expect(ids('  customs   ')).toEqual([2]);              // surrounding spaces are ignored
    expect(ids('customs hdfc')).toEqual([]);               // all words must match
    expect(isFiltered({ ...DEFAULT_FILTER, q: 'x' })).toBe(true);
  });

  it('filters by risk band (a missing band counts as LOW) and by channel', () => {
    expect(filterIncidents(items, { ...DEFAULT_FILTER, band: 'LOW' }).map(i => i.id)).toEqual([4, 3]);
    expect(filterIncidents(items, { ...DEFAULT_FILTER, band: 'CRITICAL' }).map(i => i.id)).toEqual([1]);
    expect(filterIncidents(items, { ...DEFAULT_FILTER, channel: 'sms' }).map(i => i.id)).toEqual([3]);
    expect(filterIncidents(items, { ...DEFAULT_FILTER, band: 'HIGH' })).toEqual([]);
  });

  it('sorts by risk, then newest', () => {
    expect(filterIncidents(items, { ...DEFAULT_FILTER, sort: 'risk' }).map(i => i.id)).toEqual([1, 2, 4, 3]);
  });

  it('does not mutate the input list and counts bands', () => {
    const copy = [...items];
    filterIncidents(items, { ...DEFAULT_FILTER, sort: 'risk' });
    expect(items).toEqual(copy);
    expect(bandCounts(items)).toEqual({ LOW: 2, ELEVATED: 1, HIGH: 0, CRITICAL: 1 });
  });
});

describe('scenario lab helpers', () => {
  const run = (checks: ScenarioRun['checks'], over: Partial<ScenarioRun> = {}): ScenarioRun => ({
    name: 'x', title: 'X', category: 'positive', description: '', rotation: 0.5, seed: 7, incidents: [], links: [],
    hypotheses: [], summary: { observed_links: 0, candidate_links: 0, disputed_links: 0, hypotheses: 0 },
    checks, matches_expected: true, disclaimer: 'Synthetic', ...over,
  });

  it('shows pass and fail in words, never colour alone, and info for non-requirements', () => {
    expect(checkTone({ name: 'a', expected: '', actual: 1, passed: true })).toEqual({ tone: 'pass', label: 'Pass' });
    expect(checkTone({ name: 'a', expected: '', actual: 1, passed: false })).toEqual({ tone: 'fail', label: 'Differs' });
    expect(checkTone({ name: 'a', expected: '', actual: 1, passed: null })).toEqual({ tone: 'info', label: 'Info' });
  });

  it('summarises expectations honestly', () => {
    expect(expectationSummary(run([{ name: 'a', expected: '', actual: 1, passed: true }, { name: 'b', expected: '', actual: 1, passed: null }])))
      .toBe('All 1 expectations hold.');
    expect(expectationSummary(run([{ name: 'a', expected: '', actual: 1, passed: false }, { name: 'b', expected: '', actual: 1, passed: true }])))
      .toBe('1 of 2 expectations differ from what the scenario expects.');
  });

  it('formats actual values and detects an identical replay', () => {
    expect(formatActual(3)).toBe('3');
    expect(formatActual({ a: 1 })).toBe('{"a":1}');
    expect(formatActual(null)).toBe('none');
    const a = run([]);
    expect(sameResult(a, JSON.parse(JSON.stringify(a)))).toBe(true);
    expect(sameResult(a, run([], { rotation: 0.75 }))).toBe(false);
    expect(sameResult(null, a)).toBe(false);
  });

  it('groups scenarios by category in a fixed order and skips empty groups', () => {
    const mk = (name: string, category: ScenarioInfo['category']): ScenarioInfo =>
      ({ name, title: name, category, description: '', rotation_adjustable: false, default_rotation: null });
    const groups = groupByCategory([mk('d', 'decoy'), mk('p1', 'positive'), mk('p2', 'positive')]);
    expect(groups.map(g => g.category)).toEqual(['positive', 'decoy']);
    expect(groups[0].items.map(i => i.name)).toEqual(['p1', 'p2']);
  });
});

describe('simulated call helpers', () => {
  const frame = (reached: string[], contributions: Array<{ factor: string; contribution: number }> = [], score = 0): SimulationFrame => ({
    turns: 1,
    stages: ['AUTHORITY', 'ALLEGATION', 'THREAT', 'ISOLATION', 'URGENCY', 'DEMAND']
      .map((stage, i) => ({ stage, reached: reached.includes(stage), first_turn: reached.includes(stage) ? i : null })),
    risk: {
      score, band: 'LOW', version: 'risk@x',
      contributions: contributions.map(c => ({ ...c, rule_version: 'r', effect: 'SUPPORTING' as const, explanation: c.factor })),
    },
    utterances: [], injection_flags: [], guidance: { level: 'LOW', en: [], hi: [] }, disclaimer: '',
  });

  it('advances one turn at a time and stops at the end', () => {
    expect(nextStep(0, 3)).toBe(1);
    expect(nextStep(2, 3)).toBe(3);
    expect(nextStep(3, 3)).toBeNull();
  });

  it('keeps the gauge within 0 to 1', () => {
    expect(gaugeFraction(-5)).toBe(0);
    expect(gaugeFraction(40)).toBe(0.4);
    expect(gaugeFraction(250)).toBe(1);
  });

  it('reports which stages just lit up', () => {
    const before = frame(['AUTHORITY']);
    const after = frame(['AUTHORITY', 'ALLEGATION']);
    expect(stagesReached(after)).toEqual(['AUTHORITY', 'ALLEGATION']);
    expect(newlyReached(before, after)).toEqual(['ALLEGATION']);
    expect(newlyReached(null, after)).toEqual(['AUTHORITY', 'ALLEGATION']);
    expect(stagesReached(null)).toEqual([]);
  });

  it('lists the contributions that are new since the last frame, largest first', () => {
    const before = frame([], [{ factor: 'a', contribution: 6 }]);
    const after = frame([], [{ factor: 'a', contribution: 6 }, { factor: 'b', contribution: 10 }, { factor: 'c', contribution: 24 }]);
    expect(contributionDelta(before, after).map(c => c.factor)).toEqual(['c', 'b']);
    expect(contributionDelta(null, null)).toEqual([]);
  });
});
