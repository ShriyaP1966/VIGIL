import { describe, expect, it } from 'vitest';
import { parseLocation, pathFor, sectionOf, withAssoc, TITLES } from './routes';
import type { ViewMode } from '../types';

describe('parseLocation: every page is a real URL', () => {
  const cases: Array<[string, string, Partial<ReturnType<typeof parseLocation>>]> = [
    ['/', '', { view: 'overview' }],
    ['/incidents/new', '', { view: 'new_investigation' }],
    ['/incidents/12', '', { view: 'investigation_detail', incidentId: 12 }],
    ['/graph', '', { view: 'graph' }],
    ['/campaigns', '', { view: 'campaigns' }],
    ['/campaigns/3', '', { view: 'campaigns', campaignId: 3 }],
    ['/scenarios', '', { view: 'scenario_lab' }],
    ['/simulated-call', '', { view: 'simulated_live_call' }],
    ['/reports', '', { view: 'reports' }],
    ['/settings', '', { view: 'settings' }],
  ];

  it.each(cases)('%s resolves to its page', (pathname, search, expected) => {
    expect(parseLocation(pathname, search)).toMatchObject(expected);
  });

  it('/campaigns selects no hypothesis explicitly (the page shows the first)', () => {
    expect(parseLocation('/campaigns').campaignId).toBeUndefined();
  });

  it('opens a deep link on the right page with its id (what a refresh does)', () => {
    expect(parseLocation('/incidents/7')).toEqual({ view: 'investigation_detail', path: '/incidents/7', incidentId: 7, assocId: null });
    expect(parseLocation('/campaigns/2')).toEqual({ view: 'campaigns', path: '/campaigns/2', campaignId: 2, assocId: null });
  });

  it('restores the evidence inspector from ?assoc=<id> on any page', () => {
    expect(parseLocation('/graph', '?assoc=14')).toMatchObject({ view: 'graph', assocId: 14 });
    expect(parseLocation('/campaigns/2', '?assoc=5')).toMatchObject({ view: 'campaigns', campaignId: 2, assocId: 5 });
    expect(parseLocation('/incidents/1', '?assoc=9&x=1')).toMatchObject({ incidentId: 1, assocId: 9 });
  });

  it.each(['?assoc=0', '?assoc=-3', '?assoc=abc', '?assoc=1.5', '?assoc=', '?assoc=99999999999', '?other=1'])(
    'ignores an invalid inspector parameter (%s)', (search) => {
      expect(parseLocation('/graph', search).assocId).toBeNull();
    });

  it('tolerates trailing slashes', () => {
    expect(parseLocation('/campaigns/').view).toBe('campaigns');
    expect(parseLocation('/incidents/4/')).toMatchObject({ view: 'investigation_detail', incidentId: 4 });
  });

  it('rewrites the legacy /associations/<id> alias to /graph?assoc=<id>', () => {
    expect(parseLocation('/associations/8')).toMatchObject({ view: 'graph', assocId: 8, redirectTo: '/graph?assoc=8' });
  });

  it.each(['/nope', '/incidents', '/incidents/abc', '/incidents/0', '/incidents/-1', '/incidents/1/extra', '/campaigns/x',
    '/associations/x', '/graph/extra', '/Graph', '/api/v1/health', '/demo-data/missing.json'])(
    'shows "page not found" for %s', (pathname) => {
      const r = parseLocation(pathname);
      expect(r.view).toBe('not_found');
      expect(r.assocId).toBeNull();
      expect(r.path).toBe(pathname);
    });

  it('never throws on odd input', () => {
    for (const p of ['', '//', '/%E0%A4%A', '/incidents/%00', '/\\', '/ ']) expect(() => parseLocation(p)).not.toThrow();
  });
});

describe('pathFor and withAssoc build the URLs that parseLocation reads back', () => {
  const views: ViewMode[] = ['overview', 'new_investigation', 'graph', 'campaigns', 'scenario_lab', 'simulated_live_call', 'reports', 'settings'];

  it.each(views)('%s round-trips', (view) => {
    expect(parseLocation(pathFor(view)).view).toBe(view);
  });

  it('round-trips ids', () => {
    expect(parseLocation(pathFor('investigation_detail', 21))).toMatchObject({ view: 'investigation_detail', incidentId: 21 });
    expect(parseLocation(pathFor('campaigns', 4))).toMatchObject({ view: 'campaigns', campaignId: 4 });
    expect(pathFor('investigation_detail')).toBe('/');                  // no id: fall back to home rather than a broken URL
  });

  it('adds and removes the inspector parameter', () => {
    expect(withAssoc('/graph', 3)).toBe('/graph?assoc=3');
    expect(withAssoc('/campaigns/2', null)).toBe('/campaigns/2');
    const url = new URL(withAssoc('/campaigns/2', 3), 'https://x.test');
    expect(parseLocation(url.pathname, url.search)).toMatchObject({ view: 'campaigns', campaignId: 2, assocId: 3 });
  });

  it('every route has a page title and the sidebar section follows the route', () => {
    for (const view of [...views, 'investigation_detail', 'not_found'] as const) expect(TITLES[view]).toBeTruthy();
    expect(sectionOf(parseLocation('/incidents/2'))).toBe('investigation_detail');
    expect(sectionOf(parseLocation('/nope'))).toBeNull();
  });
});
