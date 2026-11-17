import { parseLocation, withAssoc, type Route } from './routes';

/** The few browser capabilities the router needs, so tests can supply a fake history. */
export interface RouterEnv {
  getLocation(): { pathname: string; search: string };
  getState(): unknown;
  push(url: string, state?: unknown): void;
  replace(url: string, state?: unknown): void;
  back(): void;
  /** Call `cb` when the user moves through history (Back / Forward). Returns an unsubscribe function. */
  onPop(cb: () => void): () => void;
}

export class Router {
  private current: Route;
  private listeners = new Set<() => void>();
  private stopPop: () => void;

  constructor(private env: RouterEnv) {
    const loc = env.getLocation();
    this.current = parseLocation(loc.pathname, loc.search);
    // An alias such as /associations/7 is rewritten in place so the address bar shows the canonical URL.
    if (this.current.redirectTo) {
      env.replace(this.current.redirectTo, env.getState());
      this.current = this.read();
    }
    this.stopPop = env.onPop(() => this.sync());
  }

  /** Stable between changes, as required by React's useSyncExternalStore. */
  getSnapshot = (): Route => this.current;

  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => { this.listeners.delete(listener); };
  };

  destroy(): void {
    this.stopPop();
    this.listeners.clear();
  }

  private read(): Route {
    const loc = this.env.getLocation();
    return parseLocation(loc.pathname, loc.search);
  }

  private sync(): void {
    const next = this.read();
    if (next.redirectTo) {
      this.env.replace(next.redirectTo, this.env.getState());
      this.current = this.read();
    } else {
      this.current = next;
    }
    this.listeners.forEach(l => l());
  }

  private currentUrl(): string {
    const loc = this.env.getLocation();
    return `${loc.pathname}${loc.search}`;
  }

  /** Go to a URL (a new history entry, or replace the current one). Re-navigating to the same URL never stacks entries. */
  navigate(url: string, opts: { replace?: boolean; state?: unknown } = {}): void {
    if (opts.replace || url === this.currentUrl()) this.env.replace(url, opts.state ?? null);
    else this.env.push(url, opts.state ?? null);
    this.sync();
  }

  /** Open the evidence inspector for an association on the current page (?assoc=<id>). */
  openAssociation(assocId: number): void {
    this.navigate(withAssoc(this.current.path, assocId), { state: { inspector: true } });
  }

  /** Close the inspector. If we opened it, step back so Back/Forward stay symmetrical; otherwise rewrite the URL. */
  closeAssociation(): void {
    if ((this.env.getState() as { inspector?: boolean } | null)?.inspector) this.env.back();
    else this.navigate(this.current.path, { replace: true });
  }
}

export function browserEnv(): RouterEnv {
  return {
    getLocation: () => ({ pathname: window.location.pathname, search: window.location.search }),
    getState: () => window.history.state,
    push: (url, state) => window.history.pushState(state ?? null, '', url),
    replace: (url, state) => window.history.replaceState(state ?? null, '', url),
    back: () => window.history.back(),
    onPop: (cb) => {
      window.addEventListener('popstate', cb);
      return () => window.removeEventListener('popstate', cb);
    },
  };
}
