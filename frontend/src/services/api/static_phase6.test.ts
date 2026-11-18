import { afterEach, describe, expect, it, vi } from 'vitest';
import { STATIC_ROTATION_LEVELS, scenarioFile, snapRotation, staticAdapter } from './static_adapter';
import { reportFileName } from '../../lib/download';
import type { SimulationScript } from '../../types';

function res(body: unknown, init: { ok?: boolean; status?: number; type?: string; text?: string } = {}) {
  return {
    ok: init.ok ?? true, status: init.status ?? 200,
    headers: { get: () => init.type ?? 'application/json' },
    json: async () => body, text: async () => init.text ?? JSON.stringify(body),
  } as unknown as Response;
}
afterEach(() => vi.unstubAllGlobals());

describe('static Scenario Lab data', () => {
  it('has the same five rotation levels as the experiment', () => {
    expect([...STATIC_ROTATION_LEVELS]).toEqual([0, 0.25, 0.5, 0.75, 1]);
  });

  it('snaps a slider value to the nearest precomputed level', () => {
    expect(snapRotation(0)).toBe(0);
    expect(snapRotation(0.1)).toBe(0);
    expect(snapRotation(0.15)).toBe(0.25);
    expect(snapRotation(0.6)).toBe(0.5);
    expect(snapRotation(0.9)).toBe(1);
    expect(snapRotation(7)).toBe(1);
    expect(snapRotation(-3)).toBe(0);
    expect(snapRotation(Number.NaN)).toBe(0.5);
  });

  it('names the file of a rotation scenario by percent and of a fixed scenario plainly', () => {
    expect(scenarioFile('digital_arrest_cbi', 0.6)).toBe('scenario_digital_arrest_cbi__r50.json');
    expect(scenarioFile('digital_arrest_cbi', 1)).toBe('scenario_digital_arrest_cbi__r100.json');
    expect(scenarioFile('digital_arrest_cbi', 0)).toBe('scenario_digital_arrest_cbi__r0.json');
    expect(scenarioFile('legitimate_notices', null)).toBe('scenario_legitimate_notices.json');
  });

  it('loads a scenario from /demo-data and fails visibly when it is missing', async () => {
    const f = vi.fn().mockResolvedValue(res({ name: 'x' }));
    vi.stubGlobal('fetch', f);
    await staticAdapter.runScenario('x', null);
    expect(f.mock.calls[0][0]).toMatch(/demo-data\/scenario_x\.json$/);
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(res({}, { ok: false, status: 404 })));
    await expect(staticAdapter.runScenario('x', null)).rejects.toThrow(/not available/);
  });
});

describe('static reports and simulations', () => {
  it('names downloads predictably', () => {
    expect(reportFileName(4, 'csv')).toBe('vigil_report_incident_4.csv');
    expect(reportFileName(12, 'json')).toBe('vigil_report_incident_12.json');
  });

  it('does not mistake the SPA fallback (HTML) for a CSV report', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(res({}, { type: 'text/html; charset=utf-8', text: '<!doctype html>' })));
    await expect(staticAdapter.getReportCsv(1)).rejects.toThrow(/not available/);
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(res({}, { type: 'text/csv', text: 'section,record,field,value\n' })));
    expect(await staticAdapter.getReportCsv(1)).toContain('section,record');
  });

  it('serves simulation frames from one cached file per script', async () => {
    const script: SimulationScript = { name: 'demo_script', title: 't', language: 'en', description: '', turns: 2, utterances: [] };
    const f = vi.fn().mockResolvedValue(res({ name: 'demo_script', frames: [{ turns: 1 }, { turns: 2 }] }));
    vi.stubGlobal('fetch', f);
    expect((await staticAdapter.getSimulationFrame(script, 1)).turns).toBe(1);
    expect((await staticAdapter.getSimulationFrame(script, 2)).turns).toBe(2);
    expect(f).toHaveBeenCalledTimes(1);                                   // the file is read once
    await expect(staticAdapter.getSimulationFrame(script, 3)).rejects.toThrow(/frame 3/);
  });
});
