import React, { useSyncExternalStore } from 'react';
import { Router, browserEnv } from './router';
import type { Route } from './routes';

let singleton: Router | null = null;

/** The app-wide router, created on first use in the browser. */
export function getRouter(): Router {
  if (!singleton) singleton = new Router(browserEnv());
  return singleton;
}

export function useRoute(): Route {
  const router = getRouter();
  return useSyncExternalStore(router.subscribe, router.getSnapshot, router.getSnapshot);
}

/** A real anchor (right-click, middle-click and copy-link work) that navigates in-app on a plain left click. */
export const Link: React.FC<
  Omit<React.AnchorHTMLAttributes<HTMLAnchorElement>, 'href'> & { to: string; onNavigate?: () => void }
> = ({ to, onNavigate, onClick, children, ...rest }) => (
  <a
    href={to}
    onClick={(e) => {
      onClick?.(e);
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || rest.target === '_blank') return;
      e.preventDefault();
      getRouter().navigate(to);
      onNavigate?.();
    }}
    {...rest}
  >
    {children}
  </a>
);
