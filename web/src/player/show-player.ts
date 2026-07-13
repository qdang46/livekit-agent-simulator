import { fetchCues } from "../api";
import { mountAudioTimeline } from "../components/audio-timeline";
import { mountLegend } from "../components/legend";
import { renderPlayerShell } from "../components/player-shell";
import { mountSessionFooter } from "../components/session-footer";
import {
  buildTimelineItems,
  mountTimelineList,
  setFollowUi,
  syncActiveTimeline,
  type FollowState,
} from "../components/timeline-list";
import { mountVerifyBar } from "../components/verify-bar";

export function bindFollowControls(
  followBtn: HTMLButtonElement,
  follow: FollowState,
  signal: AbortSignal,
): void {
  setFollowUi(followBtn, true);
  followBtn.addEventListener(
    "click",
    () => {
      follow.enabled = !follow.enabled;
      setFollowUi(followBtn, follow.enabled);
      if (follow.enabled) follow.lastActive = -2;
    },
    { signal },
  );

  const pauseFollowFromUser = () => {
    if (performance.now() < follow.suppressScrollUntil) return;
    if (!follow.enabled) return;
    follow.enabled = false;
    setFollowUi(followBtn, false);
  };

  window.addEventListener("wheel", pauseFollowFromUser, { passive: true, signal });
  window.addEventListener("touchmove", pauseFollowFromUser, {
    passive: true,
    signal,
  });
  window.addEventListener(
    "keydown",
    (ev) => {
      if (
        ev.key === "PageUp" ||
        ev.key === "PageDown" ||
        ev.key === "Home" ||
        ev.key === "End" ||
        ((ev.key === "ArrowUp" || ev.key === "ArrowDown") &&
          !(ev.target instanceof HTMLInputElement) &&
          !(ev.target instanceof HTMLTextAreaElement) &&
          !(ev.target instanceof HTMLSelectElement))
      ) {
        pauseFollowFromUser();
      }
    },
    { signal },
  );
}

export async function showPlayer(
  app: HTMLElement,
  runId: string,
  signal: AbortSignal,
  onBack: () => void,
): Promise<void> {
  const ui = renderPlayerShell(app, runId, onBack);
  const follow: FollowState = {
    enabled: true,
    suppressScrollUntil: 0,
    lastActive: -1,
  };
  bindFollowControls(ui.followBtn, follow, signal);

  try {
    const data = await fetchCues(runId);
    const markers = data.markers || [];
    const tools = data.tool_events || [];
    const durationMs =
      data.audio?.duration_ms != null
        ? Number(data.audio.duration_ms)
        : Math.max(
            0,
            ...markers.map((m) => m.end_ms),
            ...tools.map((t) => t.end_ms),
            ...(data.cues || []).map((c) => c.end_ms),
          ) || 1;

    if (data.scenario_id) {
      ui.subtitle.textContent = `scenario: ${data.scenario_id}`;
    }
    if (data.audio?.file) {
      ui.audio.src = `/runs/${encodeURIComponent(runId)}/${data.audio.file}`;
    } else {
      ui.missing.classList.remove("hidden");
    }

    const behavior =
      data.behavior_summary || data.caller?.behavior_summary || null;

    mountVerifyBar(ui.verify, {
      script: data.script_verify,
      assertV: data.assert_verify,
      counts: data.marker_counts,
      behavior,
      toolSummary: data.tool_summary,
      observeGaps: data.observe_gaps,
    });
    mountLegend(ui.legend, markers);
    mountAudioTimeline(
      ui.timeline,
      ui.playhead,
      markers,
      durationMs,
      ui.audio,
    );
    mountSessionFooter(
      ui.sessionFooter,
      data.session_summary,
      data.chat_history,
    );

    const onUserSeek = () => {
      follow.enabled = true;
      setFollowUi(ui.followBtn, true);
      follow.lastActive = -2;
    };

    const items = buildTimelineItems(data.cues || [], markers, tools);
    const els = mountTimelineList(ui.cuesEl, items, ui.audio, onUserSeek);
    if (!els.length) {
      ui.subtitle.textContent =
        (ui.subtitle.textContent || "") + " · no transcript/markers found";
    }

    const tick = () =>
      syncActiveTimeline(els, ui.audio, ui.playhead, durationMs, follow);
    ui.audio.addEventListener("timeupdate", tick, { signal });
    ui.audio.addEventListener("seeked", tick, { signal });
    ui.audio.addEventListener(
      "play",
      () => {
        const loop = () => {
          if (ui.audio.paused) return;
          tick();
          requestAnimationFrame(loop);
        };
        requestAnimationFrame(loop);
      },
      { signal },
    );
  } catch (e) {
    ui.subtitle.className = "error";
    ui.subtitle.textContent = String(e);
  }
}
