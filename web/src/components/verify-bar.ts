import { fmtRecoveryMs } from "../lib/format";
import { LEGEND_ORDER, markerTitle } from "../lib/constants";
import type {
  AssertVerify,
  BehaviorSummary,
  ScriptVerify,
  ToolSummary,
} from "../types";

type Chip = { text: string; cls: string };

export function mountVerifyBar(
  el: HTMLElement,
  opts: {
    script?: ScriptVerify | null;
    assertV?: AssertVerify | null;
    counts?: Record<string, number>;
    behavior?: BehaviorSummary | null;
    toolSummary?: ToolSummary;
    observeGaps?: string[];
  },
): void {
  el.innerHTML = "";
  const chips: Chip[] = [];

  const { script, assertV, counts, behavior, toolSummary, observeGaps } = opts;

  if (script && typeof script.pass === "boolean") {
    chips.push({
      text: `script ${script.pass ? "pass" : "fail"}`,
      cls: script.pass ? "chip pass" : "chip fail",
    });
    if (script.agent_finals_after_barge_in != null) {
      chips.push({
        text: `recovery finals: ${script.agent_finals_after_barge_in}`,
        cls: "chip",
      });
    }
    if (script.agent_finals_after_silence != null) {
      chips.push({
        text: `after silence: ${script.agent_finals_after_silence}`,
        cls: "chip",
      });
    }
  }

  let assertRecoveryShown = false;
  if (assertV && typeof assertV.pass === "boolean" && !assertV.skipped) {
    chips.push({
      text: `assert ${assertV.pass ? "pass" : "fail"}`,
      cls: assertV.pass ? "chip pass" : "chip fail",
    });
    for (const chk of assertV.checks || []) {
      if (chk.type === "recovery") {
        assertRecoveryShown = true;
        const ok = chk.pass !== false;
        const parts = ["recovery"];
        if (chk.recovery_ms != null) parts.push(fmtRecoveryMs(Number(chk.recovery_ms)));
        if (chk.agent_finals_after_barge_in != null) {
          parts.push(`${chk.agent_finals_after_barge_in} finals`);
        }
        chips.push({
          text: parts.join(" · "),
          cls: ok ? "chip pass" : "chip fail",
        });
      }
    }
  }

  if (toolSummary && toolSummary.tool_count > 0) {
    chips.push({ text: `tools ×${toolSummary.tool_count}`, cls: "chip tool" });
  }
  if (toolSummary && toolSummary.tool_errors > 0) {
    chips.push({
      text: `tool errors ×${toolSummary.tool_errors}`,
      cls: "chip fail",
    });
  }
  if (observeGaps?.includes("tool_events")) {
    chips.push({ text: "tool capture off", cls: "chip warn" });
  }

  if (behavior) {
    if (behavior.barges_fired) {
      chips.push({
        text: `barges ×${behavior.barges_fired}${
          behavior.barges_during_agent
            ? ` (${behavior.barges_during_agent} mid-agent)`
            : ""
        }`,
        cls: "chip",
      });
    }
    if (behavior.silences_held) {
      chips.push({
        text: `silence holds ×${behavior.silences_held}`,
        cls: "chip",
      });
    }
    if (!assertRecoveryShown) {
      if (behavior.recovery_ms != null && behavior.recovery_ms >= 0) {
        const passCls =
          behavior.recovery_assert_pass === true
            ? "chip pass"
            : behavior.recovery_assert_pass === false
              ? "chip fail"
              : "chip";
        chips.push({
          text: `recovery ${fmtRecoveryMs(behavior.recovery_ms)}`,
          cls: passCls,
        });
      } else if (
        behavior.barges_fired &&
        (behavior.agent_finals_after_barge ?? 0) === 0
      ) {
        chips.push({ text: "recovery: none", cls: "chip fail" });
      }
    }
  }

  if (counts) {
    for (const t of LEGEND_ORDER) {
      const n = counts[t];
      if (n) chips.push({ text: `${markerTitle(t)} ×${n}`, cls: "chip" });
    }
  }

  for (const c of chips) {
    const span = document.createElement("span");
    span.className = c.cls;
    span.textContent = c.text;
    el.appendChild(span);
  }
}
