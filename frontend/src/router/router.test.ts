import { describe, expect, it, vi } from 'vitest';
import { Router, type RouterEnv } from './router';

/** A fake browser history: a stack of entries, the way Back/Forward really behave. */
function fakeBrowser(initialUrl: string) {
  const entries: Array<{ url: string; state: unknown }> = [{ url: initialUrl, state: null }];
  let index = 0;
  const pops = new Set<() => void>();
  const loc = () => {
    const u = new URL(entries[index].url, 'https://app.test');
    return { pathname: u.pathname, search: u.search };
  };
  const env: RouterEnv = {
    getLocation: loc,
    getState: () => entries[index].state,
    push: (url, state) => { entries.splice(index + 1); entries.push({ url, state }); index += 1; },
    replace: (url, state) => { entries[index] = { url, state }; },
    back: () => { if (index > 0) { index -= 1; pops.forEach(cb => cb()); } },
    onPop: (cb) => { pops.add(cb); return () => pops.delete(cb); },
  };
  return {
    env,
    url: () => `${loc().pathname}${loc().search}`,
    length: () => entries.length,
    back: () => env.back(),
    forward: () => { if (index < entries.length - 1) { index += 1; pops.forEach(cb => cb()); } },
  };
}

describe('Router', () => {
  it('opens a deep link on its own page (refresh in live and static mode alike)', () => {
    const b = fakeBrowser('/campaigns/2?assoc=5');
    const router = new Router(b.env);
    expect(router.getSnapshot()).toMatchObject({ view: 'campaigns', campaignId: 2, assocId: 5 });
    expect(b.url()).toBe('/campaigns/2?assoc=5');                       // the address bar is left untouched
  });

  it('shows page-not-found for an unknown URL without changing it', () => {
    const b = fakeBrowser('/does/not/exist');
    const router = new Router(b.env);
    expect(router.getSnapshot().view).toBe('not_found');
    expect(b.url()).toBe('/does/not/exist');
  });

  it('rewrites the legacy association URL to the canonical one at start-up', () => {
    const b = fakeBrowser('/associations/7');
    const router = new Router(b.env);
    expect(b.url()).toBe('/graph?assoc=7');
    expect(router.getSnapshot()).toMatchObject({ view: 'graph', assocId: 7 });
    expect(b.length()).toBe(1);                                          // replaced, not stacked
  });

  it('changes the URL on navigation and notifies subscribers', () => {
    const b = fakeBrowser('/');
    const router = new Router(b.env);
    const listener = vi.fn();
    router.subscribe(listener);
    router.navigate('/campaigns');
    expect(b.url()).toBe('/campaigns');
    expect(router.getSnapshot().view).toBe('campaigns');
    expect(listener).toHaveBeenCalledTimes(1);
  });

  it('Back and Forward move through the pages the user visited', () => {
    const b = fakeBrowser('/');
    const router = new Router(b.env);
    router.navigate('/graph');
    router.navigate('/incidents/3');
    router.navigate('/campaigns/1');
    expect(router.getSnapshot()).toMatchObject({ view: 'campaigns', campaignId: 1 });

    b.back();
    expect(router.getSnapshot()).toMatchObject({ view: 'investigation_detail', incidentId: 3 });
    b.back();
    expect(router.getSnapshot().view).toBe('graph');
    b.forward();
    expect(router.getSnapshot()).toMatchObject({ view: 'investigation_detail', incidentId: 3 });
    expect(b.url()).toBe('/incidents/3');
  });

  it('navigating to the page you are already on does not stack history entries', () => {
    const b = fakeBrowser('/graph');
    const router = new Router(b.env);
    router.navigate('/graph');
    router.navigate('/graph');
    expect(b.length()).toBe(1);
  });

  it('replace navigations do not add entries', () => {
    const b = fakeBrowser('/');
    const router = new Router(b.env);
    router.navigate('/settings', { replace: true });
    expect(b.length()).toBe(1);
    expect(router.getSnapshot().view).toBe('settings');
  });

  it('opens and closes the evidence inspector in the URL, and Back closes it too', () => {
    const b = fakeBrowser('/campaigns/2');
    const router = new Router(b.env);
    router.openAssociation(14);
    expect(b.url()).toBe('/campaigns/2?assoc=14');
    expect(router.getSnapshot()).toMatchObject({ view: 'campaigns', campaignId: 2, assocId: 14 });

    b.back();                                                             // browser Back closes the inspector
    expect(router.getSnapshot().assocId).toBeNull();
    expect(b.url()).toBe('/campaigns/2');

    b.forward();                                                          // Forward reopens it
    expect(router.getSnapshot().assocId).toBe(14);
    router.closeAssociation();                                            // the close button steps back, symmetrically
    expect(router.getSnapshot().assocId).toBeNull();
    expect(b.url()).toBe('/campaigns/2');
  });

  it('closing a deep-linked inspector rewrites the URL instead of leaving the site', () => {
    const b = fakeBrowser('/graph?assoc=3');                              // opened directly, no earlier entry
    const router = new Router(b.env);
    router.closeAssociation();
    expect(b.url()).toBe('/graph');
    expect(router.getSnapshot()).toMatchObject({ view: 'graph', assocId: null });
    expect(b.length()).toBe(1);
  });

  it('keeps the same snapshot object until the location changes (required by useSyncExternalStore)', () => {
    const b = fakeBrowser('/');
    const router = new Router(b.env);
    const first = router.getSnapshot();
    expect(router.getSnapshot()).toBe(first);
    router.navigate('/reports');
    expect(router.getSnapshot()).not.toBe(first);
  });

  it('stops notifying after unsubscribe or destroy', () => {
    const b = fakeBrowser('/');
    const router = new Router(b.env);
    const listener = vi.fn();
    const off = router.subscribe(listener);
    off();
    router.navigate('/graph');
    expect(listener).not.toHaveBeenCalled();
    router.destroy();
    b.back();                                                             // no error, no stale listener
  });
});
