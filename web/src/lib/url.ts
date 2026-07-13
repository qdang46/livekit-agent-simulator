export function runFromUrl(): string | null {
  return new URLSearchParams(location.search).get("run");
}

export function setRunInUrl(runId: string | null): void {
  const url = new URL(location.href);
  if (runId) url.searchParams.set("run", runId);
  else url.searchParams.delete("run");
  history.pushState({}, "", url);
}
