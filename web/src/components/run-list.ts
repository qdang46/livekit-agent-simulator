import type { RunSummary } from "../types";

export function renderRunList(
  root: HTMLElement,
  runs: RunSummary[],
  onSelect: (runId: string) => void,
): void {
  root.innerHTML = `
    <main class="page">
      <header class="header">
        <h1>lk-sim reports</h1>
        <p class="muted">Pick a run to play audio with time-synced transcript, tools, and behavior markers.</p>
      </header>
      <ul class="run-list" id="runs"></ul>
      <p class="muted ${runs.length ? "hidden" : ""}" id="empty">
        No reports found under <code>.agent-sim/reports/</code>.
      </p>
    </main>
  `;
  const ul = root.querySelector<HTMLUListElement>("#runs");
  if (!ul) return;
  for (const r of runs) {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "link";
    btn.textContent = r.run_id;
    btn.addEventListener("click", () => onSelect(r.run_id));
    const meta = document.createElement("span");
    meta.className = "muted";
    meta.textContent =
      " — " +
      [
        r.status || "?",
        r.turn_count != null ? `${r.turn_count} turns` : null,
        r.tool_count != null && r.tool_count > 0 ? `${r.tool_count} tools` : null,
        r.duration_ms != null ? `${(r.duration_ms / 1000).toFixed(1)}s` : null,
        r.has_audio ? "audio" : "no audio",
      ]
        .filter(Boolean)
        .join(" · ");
    li.append(btn, meta);
    ul.appendChild(li);
  }
}
