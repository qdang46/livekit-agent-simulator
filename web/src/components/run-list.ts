import type { RunSummary } from "../types";

type ScenarioGroup = {
  scenarioId: string;
  runs: RunSummary[];
};

function groupByScenario(runs: RunSummary[]): ScenarioGroup[] {
  const order: string[] = [];
  const map = new Map<string, RunSummary[]>();
  for (const r of runs) {
    const key = (r.scenario_id && String(r.scenario_id).trim()) || "unknown";
    if (!map.has(key)) {
      map.set(key, []);
      order.push(key);
    }
    map.get(key)!.push(r);
  }
  return order.map((scenarioId) => ({
    scenarioId,
    runs: map.get(scenarioId)!,
  }));
}

function runMetaText(r: RunSummary): string {
  return [
    r.status || "?",
    r.turn_count != null ? `${r.turn_count} turns` : null,
    r.tool_count != null && r.tool_count > 0 ? `${r.tool_count} tools` : null,
    r.duration_ms != null ? `${(r.duration_ms / 1000).toFixed(1)}s` : null,
    r.has_audio ? "audio" : "no audio",
  ]
    .filter(Boolean)
    .join(" · ");
}

export function renderRunList(
  root: HTMLElement,
  runs: RunSummary[],
  onSelect: (runId: string) => void,
): void {
  const groups = groupByScenario(runs);
  root.innerHTML = `
    <main class="page">
      <header class="header">
        <h1>lk-sim reports</h1>
        <p class="muted">Scenarios with runs under <code>.agent-sim/reports/</code>. Pick a run to play.</p>
      </header>
      <div class="scenario-list" id="scenarios"></div>
      <p class="muted ${runs.length ? "hidden" : ""}" id="empty">
        No reports found under <code>.agent-sim/reports/</code>.
      </p>
    </main>
  `;
  const container = root.querySelector<HTMLDivElement>("#scenarios");
  if (!container) return;

  for (const g of groups) {
    const section = document.createElement("section");
    section.className = "scenario-group";

    const heading = document.createElement("h2");
    heading.className = "scenario-title";
    heading.textContent = g.scenarioId;
    const count = document.createElement("span");
    count.className = "muted scenario-count";
    count.textContent = ` · ${g.runs.length} run${g.runs.length === 1 ? "" : "s"}`;
    heading.appendChild(count);

    const ul = document.createElement("ul");
    ul.className = "run-list";
    for (const r of g.runs) {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "link";
      btn.textContent = r.run_id;
      btn.addEventListener("click", () => onSelect(r.run_id));
      const meta = document.createElement("span");
      meta.className = "muted";
      meta.textContent = " — " + runMetaText(r);
      li.append(btn, meta);
      ul.appendChild(li);
    }

    section.append(heading, ul);
    container.appendChild(section);
  }
}
