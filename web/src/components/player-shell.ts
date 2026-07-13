import type { PlayerUI } from "../types";

export function renderPlayerShell(
  root: HTMLElement,
  runId: string,
  onBack: () => void,
): PlayerUI {
  root.innerHTML = `
    <main class="page player-page">
      <header class="header">
        <button type="button" class="back" id="back">← runs</button>
        <h1 id="title"></h1>
        <p id="subtitle" class="muted"></p>
        <div id="verify" class="verify-bar"></div>
      </header>
      <div class="player-dock" id="dock">
        <section class="audio-panel">
          <audio id="audio" controls preload="metadata"></audio>
          <p id="audio-missing" class="warn hidden">
            No <code>conversation.wav</code> for this run. Timeline still lists with timestamps.
          </p>
          <div id="timeline" class="timeline" title="Click to seek">
            <div id="playhead" class="timeline-playhead" style="left:0"></div>
          </div>
          <div class="dock-row">
            <div class="role-key" aria-label="Speaker legend">
              <span class="role-key-item"><span class="role-dot agent"></span> Agent</span>
              <span class="role-key-item"><span class="role-dot user"></span> Caller (persona)</span>
              <span class="role-key-item"><span class="role-dot script-barge"></span> Script inject (NOT caller)</span>
            </div>
            <button type="button" class="follow-btn on" id="follow" title="When on, transcript keeps the current line in view. Scroll freely turns this off.">
              Follow live
            </button>
          </div>
          <div id="legend" class="legend"></div>
          <p class="hint muted">Stereo WAV · click a bubble, tool card, or band to seek · scroll anytime (follow pauses until you re-enable)</p>
        </section>
      </div>
      <section class="transcript-panel">
        <div class="section-head">
          <h2 class="section-title">Conversation</h2>
          <span class="section-hint">Full-width 3 columns · Agent · Agent actions · Caller</span>
        </div>
        <div class="col-headers" aria-hidden="true">
          <div class="col-h agent">Agent</div>
          <div class="col-h script">Agent actions</div>
          <div class="col-h user">Caller</div>
        </div>
        <ol id="cues" class="cues"></ol>
      </section>
      <footer id="session-footer" class="session-footer"></footer>
    </main>
  `;
  root.querySelector("#back")?.addEventListener("click", onBack);
  const title = root.querySelector("#title");
  if (title) title.textContent = runId;
  return {
    audio: root.querySelector("#audio") as HTMLAudioElement,
    cuesEl: root.querySelector("#cues") as HTMLOListElement,
    subtitle: root.querySelector("#subtitle") as HTMLElement,
    missing: root.querySelector("#audio-missing") as HTMLElement,
    timeline: root.querySelector("#timeline") as HTMLElement,
    playhead: root.querySelector("#playhead") as HTMLElement,
    legend: root.querySelector("#legend") as HTMLElement,
    verify: root.querySelector("#verify") as HTMLElement,
    followBtn: root.querySelector("#follow") as HTMLButtonElement,
    sessionFooter: root.querySelector("#session-footer") as HTMLElement,
  };
}
