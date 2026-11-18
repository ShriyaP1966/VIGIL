import { describe, expect, it } from 'vitest';
import vercelJson from '../../vercel.json?raw';
import { parseLocation, pathFor } from './routes';
import type { ViewMode } from '../types';

// The hosted site is a single-page app: Vercel must answer every page URL with index.html (so a refresh or a
// pasted deep link works) while API, demo-data and asset URLs must never fall back to it.
const config = JSON.parse(vercelJson);
const rewrite = config.rewrites?.[0];
// Vercel's `source` is a path-to-regexp pattern; this one is a single regex group, so it is also a valid RegExp.
const matches = (pathname: string) => new RegExp(`^${rewrite.source}$`).test(pathname);

describe('frontend/vercel.json SPA rewrite', () => {
  it('sends matching URLs to index.html', () => {
    expect(rewrite).toBeDefined();
    expect(rewrite.destination).toBe('/index.html');
  });

  const views: ViewMode[] = ['overview', 'investigations', 'new_investigation', 'graph', 'campaigns', 'scenario_lab', 'simulated_live_call', 'reports', 'settings'];

  it.each(views)('rewrites the %s page URL (a refresh or deep link reaches the app)', (view) => {
    const path = pathFor(view);
    expect(matches(path)).toBe(true);
    expect(parseLocation(path).view).toBe(view);          // and the app then knows that URL
  });

  it.each(['/incidents/12', '/campaigns/3', '/associations/8', '/campaigns/', '/does/not/exist'])(
    'rewrites %s (the app decides between a page and "not found")', (path) => {
      expect(matches(path)).toBe(true);
    });

  it.each(['/api/v1/health', '/api/v1/incidents/1', '/demo-data/campaigns.json', '/assets/index-abc123.js'])(
    'never rewrites %s to index.html', (path) => {
      expect(matches(path)).toBe(false);
    });

  it('is a Vite build served from the frontend folder', () => {
    expect(config.framework).toBe('vite');
    expect(config.outputDirectory).toBe('dist');
  });
});
