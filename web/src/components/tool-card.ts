import { fmtMs, truncateLines } from "../lib/format";
import type { ToolSpan } from "../types";

function prettyJson(raw: string | undefined): string {
  if (!raw) return "";
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
}

function createExpandableBlock(
  label: string,
  text: string,
  maxLines: number,
  extraClass: string,
): HTMLElement {
  const wrap = document.createElement("div");
  wrap.className = `tool-block ${extraClass}`;

  const head = document.createElement("button");
  head.type = "button";
  head.className = "tool-block-toggle";
  head.textContent = label;

  const body = document.createElement("pre");
  body.className = "tool-block-body";
  const full = text.trim();
  const short = truncateLines(full, maxLines);
  body.textContent = short;
  const expandable = full !== short;
  if (!expandable) head.disabled = true;

  head.addEventListener("click", (ev) => {
    ev.stopPropagation();
    if (!expandable) return;
    const expanded = wrap.classList.toggle("expanded");
    body.textContent = expanded ? full : short;
    head.textContent = expanded ? `${label} (collapse)` : label;
  });

  wrap.append(head, body);
  return wrap;
}

export function createToolCardElement(tool: ToolSpan): HTMLLIElement {
  const li = document.createElement("li");
  const err = tool.is_error;
  li.className = `cue-row tool-row ${err ? "tool-error" : "tool"}`;
  li.dataset.start = String(tool.start_ms);
  li.dataset.end = String(tool.end_ms);

  const card = document.createElement("div");
  card.className = `cue-card tool ${err ? "tool-error" : ""}`;

  const meta = document.createElement("div");
  meta.className = "cue-meta";
  const role = document.createElement("span");
  role.className = `role tool-type ${err ? "tool-error" : "tool"}`;
  role.textContent = err ? "Tool error" : "Tool";
  const time = document.createElement("span");
  time.className = "time";
  const dur =
    tool.duration_ms != null && tool.duration_ms >= 0
      ? ` · ${tool.duration_ms}ms`
      : "";
  const turn = tool.turn != null ? ` · turn ${tool.turn}` : "";
  time.textContent = `${fmtMs(tool.start_ms)} – ${fmtMs(tool.end_ms)}${dur}${turn}`;
  const tag = document.createElement("span");
  tag.className = `tag ${err ? "tool_error" : "tool"}`;
  tag.textContent = tool.name;
  meta.append(role, time, tag);

  const title = document.createElement("div");
  title.className = "tool-name";
  title.textContent = `🔧 ${tool.name}`;

  card.append(meta, title);

  if (tool.arguments) {
    card.append(
      createExpandableBlock("Args", prettyJson(tool.arguments), 4, "tool-args"),
    );
  }
  if (tool.output) {
    card.append(
      createExpandableBlock("Output", prettyJson(tool.output), 6, "tool-output"),
    );
  }
  if (err && tool.error) {
    const errBanner = document.createElement("div");
    errBanner.className = "tool-error-banner";
    errBanner.textContent = tool.error;
    card.append(errBanner);
  }

  li.append(card);
  return li;
}
