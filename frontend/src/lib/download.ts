/** Save text as a file in the browser (no server round trip, nothing leaves the page). */
export function downloadText(filename: string, mime: string, text: string): void {
  const url = URL.createObjectURL(new Blob([text], { type: `${mime};charset=utf-8` }));
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function reportFileName(incidentId: number, ext: 'json' | 'csv'): string {
  return `vigil_report_incident_${incidentId}.${ext}`;
}
