/** Raised by the static adapter for actions that need the live backend. */
export class LiveBackendRequiredError extends Error {
  constructor(action: string) {
    super(
      `${action} needs the live analysis backend, which is not reachable right now. ` +
      'The hosted demo shows precomputed synthetic data only.'
    );
    this.name = 'LiveBackendRequiredError';
  }
}

/** Pull a readable message out of the backend's standard error body {error:{code,message}}. */
export async function readApiError(res: Response, fallback: string): Promise<string> {
  try {
    const body = await res.json();
    const msg = body?.error?.message;
    if (typeof msg === 'string' && msg) return msg;
  } catch {
    // not JSON
  }
  return `${fallback} (HTTP ${res.status})`;
}
