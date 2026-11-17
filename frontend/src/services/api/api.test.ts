import { afterEach, describe, expect, it, vi } from 'vitest';
import { probeBackend } from './client';
import { staticAdapter } from './static_adapter';
import { LiveBackendRequiredError } from './errors';

function jsonResponse(body: unknown, init: { ok?: boolean; status?: number; type?: string } = {}) {
  return {
    ok: init.ok ?? true,
    status: init.status ?? 200,
    headers: { get: () => init.type ?? 'application/json' },
    json: async () => body,
  } as unknown as Response;
}

afterEach(() => vi.unstubAllGlobals());

describe('backend probe', () => {
  it('is live only for a JSON {status:"ok"} body', async () => {
    const f = vi.fn().mockResolvedValue(jsonResponse({ status: 'ok', mode: 'offline' }));
    expect(await probeBackend('https://api.example', f as unknown as typeof fetch)).toBe(true);
    expect(f.mock.calls[0][0]).toBe('https://api.example/api/v1/health');
  });

  it('is NOT live when a static host answers 200 with HTML (SPA rewrite)', async () => {
    const html = {
      ok: true, status: 200, headers: { get: () => 'text/html' },
      json: async () => { throw new SyntaxError('Unexpected token <'); },
    } as unknown as Response;
    expect(await probeBackend('', vi.fn().mockResolvedValue(html) as unknown as typeof fetch)).toBe(false);
  });

  it('is not live on errors, network failure or a non-ok body', async () => {
    expect(await probeBackend('', vi.fn().mockResolvedValue(jsonResponse({}, { ok: false, status: 503 })) as unknown as typeof fetch)).toBe(false);
    expect(await probeBackend('', vi.fn().mockRejectedValue(new TypeError('network')) as unknown as typeof fetch)).toBe(false);
    expect(await probeBackend('', vi.fn().mockResolvedValue(jsonResponse({ status: 'degraded' })) as unknown as typeof fetch)).toBe(false);
  });

  it('gives up after the timeout when the server never answers', async () => {
    const hang = (_url: string, init?: RequestInit) =>
      new Promise<Response>((_, reject) => init?.signal?.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError'))));
    expect(await probeBackend('', hang as unknown as typeof fetch, 20)).toBe(false);
  });
});

describe('http adapter reviews', () => {
  it('posts the decision and a trimmed note, and surfaces the backend error message', async () => {
    const { httpAdapter } = await import('./http_adapter');
    const ok = vi.fn().mockResolvedValue(jsonResponse({ id: 5, status: 'ANALYST_VERIFIED_ASSOCIATION' }));
    vi.stubGlobal('fetch', ok);
    await httpAdapter.reviewAssociation(5, 'ACCEPT', '  looks right  ');
    const [url, init] = ok.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/v1\/associations\/5\/review$/);
    expect(JSON.parse(init.body)).toEqual({ decision: 'ACCEPT', note: 'looks right' });

    await httpAdapter.reviewCampaign(2, 'FLAG', '   ');
    expect(JSON.parse(ok.mock.calls[1][1].body)).toEqual({ decision: 'FLAG', note: null });

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ error: { code: 'NOT_FOUND', message: 'Association not found' } }, { ok: false, status: 404 })));
    await expect(httpAdapter.reviewAssociation(99, 'REJECT')).rejects.toThrow('Association not found');
  });
});

describe('static adapter (precomputed data only)', () => {
  it('reads files from /demo-data/', async () => {
    const f = vi.fn().mockResolvedValue(jsonResponse([{ id: 1 }]));
    vi.stubGlobal('fetch', f);
    expect(await staticAdapter.listIncidents()).toEqual([{ id: 1 }]);
    expect(f.mock.calls[0][0]).toMatch(/demo-data\/incidents\.json$/);
    await staticAdapter.getAssociationInspector(7);
    expect(f.mock.calls[1][0]).toMatch(/demo-data\/association_7\.json$/);
  });

  it('fails visibly instead of inventing data when a file is missing or is not JSON', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(null, { ok: false, status: 404 })));
    await expect(staticAdapter.getIncident(99)).rejects.toThrow(/not available/);
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(null, { type: 'text/html' })));
    await expect(staticAdapter.getGraph()).rejects.toThrow(/not valid JSON/);
  });

  it('reads campaign hypotheses from the precomputed files', async () => {
    const f = vi.fn().mockResolvedValue(jsonResponse([{ id: 1 }]));
    vi.stubGlobal('fetch', f);
    await staticAdapter.listCampaigns();
    await staticAdapter.getCampaign(3);
    expect(f.mock.calls[0][0]).toMatch(/demo-data\/campaigns\.json$/);
    expect(f.mock.calls[1][0]).toMatch(/demo-data\/campaign_3\.json$/);
  });

  it('cannot save reviews without the live backend', async () => {
    await expect(staticAdapter.reviewAssociation(1, 'ACCEPT', 'x')).rejects.toBeInstanceOf(LiveBackendRequiredError);
    await expect(staticAdapter.reviewCampaign(1, 'REJECT')).rejects.toThrow(/live analysis backend/);
  });

  it('refuses live-only actions with an explanatory error', async () => {
    await expect(staticAdapter.createIncident({})).rejects.toBeInstanceOf(LiveBackendRequiredError);
    await expect(staticAdapter.clearAllData()).rejects.toThrow(/live analysis backend/);
  });
});
