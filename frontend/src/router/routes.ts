import type { ViewMode } from '../types';

/**
 * Every page is a real URL (History API, no hash), so refresh, deep links and Back/Forward work in both the
 * live-backend mode and the static demo mode. Vercel's rewrite (frontend/vercel.json) serves index.html for
 * these paths. Pure functions only, so the routing can be unit-tested without a browser.
 *
 *   /                      Overview
 *   /incidents             Investigations list (search and filters)
 *   /incidents/new         New investigation
 *   /incidents/<id>        Investigation detail
 *   /graph                 Intelligence graph
 *   /campaigns             Campaign hypotheses (first one selected)
 *   /campaigns/<id>        A specific hypothesis
 *   /scenarios             Scenario lab
 *   /simulated-call        Simulated live call analysis
 *   /reports, /settings
 *   <any page>?assoc=<id>  The evidence inspector for association <id> opened on that page
 *   /associations/<id>     Legacy form: redirects to /graph?assoc=<id>
 */

export type RouteView = ViewMode | 'not_found';

export interface Route {
  view: RouteView;
  /** Canonical pathname (no query string). For unknown URLs it is the pathname that was requested. */
  path: string;
  incidentId?: number;
  campaignId?: number;
  /** Association whose evidence inspector is open, from ?assoc=<id>. */
  assocId: number | null;
  /** Set when the requested URL is an alias that should be rewritten (history.replace) to this canonical URL. */
  redirectTo?: string;
}

const FIXED: Record<string, ViewMode> = {
  '/': 'overview',
  '/incidents': 'investigations',
  '/incidents/new': 'new_investigation',
  '/graph': 'graph',
  '/campaigns': 'campaigns',
  '/scenarios': 'scenario_lab',
  '/simulated-call': 'simulated_live_call',
  '/reports': 'reports',
  '/settings': 'settings',
};

export const TITLES: Record<RouteView, string> = {
  overview: 'Overview',
  investigations: 'Investigations',
  new_investigation: 'New investigation',
  investigation_detail: 'Investigation',
  graph: 'Intelligence graph',
  campaigns: 'Campaign hypotheses',
  scenario_lab: 'Scenario lab',
  simulated_live_call: 'Simulated call analysis',
  reports: 'Reports',
  settings: 'Settings',
  not_found: 'Page not found',
};

const positiveInt = (s: string | undefined): number | null => {
  if (!s || !/^[1-9]\d{0,9}$/.test(s)) return null;
  return Number(s);
};

export function parseAssocParam(search: string): number | null {
  const value = new URLSearchParams(search).get('assoc');
  return positiveInt(value ?? undefined);
}

/** Resolve a location to a route. Never throws: anything unknown becomes `not_found`. */
export function parseLocation(pathname: string, search = ''): Route {
  let path = pathname || '/';
  if (path.length > 1) path = path.replace(/\/+$/, '') || '/';
  const assocId = parseAssocParam(search);

  const fixed = FIXED[path];
  if (fixed) return { view: fixed, path, assocId };

  let m = /^\/incidents\/([^/]+)$/.exec(path);
  if (m) {
    const id = positiveInt(m[1]);
    return id ? { view: 'investigation_detail', path, incidentId: id, assocId } : { view: 'not_found', path, assocId: null };
  }
  m = /^\/campaigns\/([^/]+)$/.exec(path);
  if (m) {
    const id = positiveInt(m[1]);
    return id ? { view: 'campaigns', path, campaignId: id, assocId } : { view: 'not_found', path, assocId: null };
  }
  m = /^\/associations\/([^/]+)$/.exec(path);
  if (m) {
    const id = positiveInt(m[1]);
    return id
      ? { view: 'graph', path: '/graph', assocId: id, redirectTo: `/graph?assoc=${id}` }
      : { view: 'not_found', path, assocId: null };
  }
  return { view: 'not_found', path, assocId: null };
}

/** The path for a view (and optional id), used by every in-app navigation. */
export function pathFor(view: ViewMode, id?: number): string {
  switch (view) {
    case 'overview': return '/';
    case 'investigations': return '/incidents';
    case 'new_investigation': return '/incidents/new';
    case 'investigation_detail': return id != null ? `/incidents/${id}` : '/';
    case 'graph': return '/graph';
    case 'campaigns': return id != null ? `/campaigns/${id}` : '/campaigns';
    case 'scenario_lab': return '/scenarios';
    case 'simulated_live_call': return '/simulated-call';
    case 'reports': return '/reports';
    case 'settings': return '/settings';
  }
}

/** The same page with the association inspector opened (or closed when `assocId` is null). */
export function withAssoc(path: string, assocId: number | null): string {
  return assocId == null ? path : `${path}?assoc=${assocId}`;
}

/** The sidebar highlights the section a route belongs to. */
export function sectionOf(route: Route): ViewMode | null {
  if (route.view === 'not_found') return null;
  return route.view === 'investigation_detail' ? 'investigations' : route.view;   // a case belongs to the list
}
