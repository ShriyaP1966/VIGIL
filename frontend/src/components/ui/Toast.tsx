import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { CheckCircle2, AlertCircle, X } from 'lucide-react';

type ToastKind = 'success' | 'error';
interface ToastItem { id: number; kind: ToastKind; message: string }

interface ToastApi {
  success: (message: string) => void;
  error: (message: string) => void;
}

const ToastContext = createContext<ToastApi>({ success: () => undefined, error: () => undefined });

export const useToast = (): ToastApi => useContext(ToastContext);

const LIFETIME_MS = 5000;

/** Success and error toasts in a polite live region (announced by screen readers, never steals focus). */
export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(1);
  const timers = useRef(new Map<number, ReturnType<typeof setTimeout>>());

  const dismiss = useCallback((id: number) => {
    setItems(prev => prev.filter(t => t.id !== id));
    const timer = timers.current.get(id);
    if (timer) { clearTimeout(timer); timers.current.delete(id); }
  }, []);

  const push = useCallback((kind: ToastKind, message: string) => {
    const id = nextId.current++;
    setItems(prev => [...prev.slice(-3), { id, kind, message }]);
    timers.current.set(id, setTimeout(() => dismiss(id), LIFETIME_MS));
  }, [dismiss]);

  useEffect(() => () => { timers.current.forEach(clearTimeout); }, []);

  const api = useMemo<ToastApi>(() => ({
    success: (m) => push('success', m),
    error: (m) => push('error', m),
  }), [push]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div aria-live="polite" className="fixed bottom-4 right-4 left-4 sm:left-auto z-[60] flex flex-col gap-2 items-end pointer-events-none">
        {items.map(t => (
          <div
            key={t.id}
            role={t.kind === 'error' ? 'alert' : 'status'}
            className={`pointer-events-auto max-w-sm w-full sm:w-auto flex items-start gap-2 rounded-md border px-3 py-2 text-xs shadow-lg bg-bg-card ${
              t.kind === 'success' ? 'border-risk-low/50 text-text-primary' : 'border-risk-critical/50 text-text-primary'
            }`}
          >
            {t.kind === 'success'
              ? <CheckCircle2 className="w-4 h-4 text-risk-low shrink-0 mt-0.5" aria-hidden="true" />
              : <AlertCircle className="w-4 h-4 text-risk-critical shrink-0 mt-0.5" aria-hidden="true" />}
            <span className="flex-1 break-words">{t.message}</span>
            <button
              type="button"
              onClick={() => dismiss(t.id)}
              aria-label="Dismiss notification"
              className="text-text-muted hover:text-text-primary rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary"
            >
              <X className="w-3.5 h-3.5" aria-hidden="true" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};
