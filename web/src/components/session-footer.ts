import { fmtMs } from "../lib/format";
import type { ChatHistoryItem, SessionSummary } from "../types";

function summarizeUsage(usage: Record<string, unknown>): string {
  const modelUsage = usage.model_usage;
  if (!Array.isArray(modelUsage) || !modelUsage.length) {
    return JSON.stringify(usage).slice(0, 120);
  }
  let input = 0;
  let output = 0;
  for (const row of modelUsage) {
    if (!row || typeof row !== "object") continue;
    const llm = (row as Record<string, unknown>).llm;
    if (!llm || typeof llm !== "object") continue;
    const l = llm as Record<string, unknown>;
    input += Number(l.input_tokens) || 0;
    output += Number(l.output_tokens) || 0;
  }
  const parts: string[] = [];
  if (input) parts.push(`${input.toLocaleString()} in`);
  if (output) parts.push(`${output.toLocaleString()} out`);
  return parts.length ? parts.join(" · ") : "usage recorded";
}

function formatHistoryItem(item: ChatHistoryItem): string {
  const type = String(item.type || "item");
  if (type === "function_call") {
    return `call ${String(item.name || "?")}(${String(item.arguments || "").slice(0, 80)})`;
  }
  if (type === "function_call_output") {
    return `output ${String(item.name || "?")}: ${String(item.output || "").slice(0, 80)}`;
  }
  if (type === "message") {
    const role = String(item.role || "?");
    const content = item.content;
    let text = "";
    if (Array.isArray(content) && content[0] && typeof content[0] === "object") {
      text = String((content[0] as Record<string, unknown>).text || "");
    }
    return `${role}: ${text.slice(0, 100)}`;
  }
  return type;
}

export function mountSessionFooter(
  el: HTMLElement,
  session: SessionSummary | null | undefined,
  chatHistory: ChatHistoryItem[] | null | undefined,
): void {
  el.innerHTML = "";
  if (!session && (!chatHistory || !chatHistory.length)) return;

  const details = document.createElement("details");
  details.className = "session-details";
  const summaryEl = document.createElement("summary");
  summaryEl.className = "session-summary-toggle";

  const usageText =
    session?.usage && typeof session.usage === "object"
      ? summarizeUsage(session.usage)
      : null;
  const transitionCount = session?.state_transitions?.length ?? 0;
  summaryEl.textContent = [
    "Session",
    usageText,
    transitionCount ? `${transitionCount} state changes` : null,
    chatHistory?.length ? `${chatHistory.length} history items` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  const body = document.createElement("div");
  body.className = "session-details-body";

  if (session?.state_transitions?.length) {
    const h = document.createElement("h3");
    h.textContent = "Agent state";
    body.append(h);
    const ul = document.createElement("ul");
    ul.className = "session-list";
    for (const t of session.state_transitions) {
      const li = document.createElement("li");
      const from = t.from ? `${t.from} → ` : "";
      li.textContent = `${fmtMs(t.at_ms)} · ${from}${t.to}`;
      ul.append(li);
    }
    body.append(ul);
  }

  if (session?.errors?.length) {
    const h = document.createElement("h3");
    h.textContent = "Session errors";
    body.append(h);
    const ul = document.createElement("ul");
    ul.className = "session-list session-errors";
    for (const err of session.errors) {
      const li = document.createElement("li");
      li.textContent = `${fmtMs(err.at_ms)} · ${err.message}`;
      ul.append(li);
    }
    body.append(ul);
  }

  if (session?.usage) {
    const h = document.createElement("h3");
    h.textContent = "Usage";
    body.append(h);
    const pre = document.createElement("pre");
    pre.className = "session-usage-json";
    pre.textContent = JSON.stringify(session.usage, null, 2);
    body.append(pre);
  }

  if (chatHistory?.length) {
    const h = document.createElement("h3");
    h.textContent = "Chat history";
    body.append(h);
    const ul = document.createElement("ul");
    ul.className = "session-list";
    for (const item of chatHistory) {
      const li = document.createElement("li");
      li.textContent = formatHistoryItem(item);
      ul.append(li);
    }
    body.append(ul);
  }

  details.append(summaryEl, body);
  el.append(details);
}
