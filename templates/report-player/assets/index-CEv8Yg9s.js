(function(){let e=document.createElement(`link`).relList;if(e&&e.supports&&e.supports(`modulepreload`))return;for(let e of document.querySelectorAll(`link[rel="modulepreload"]`))n(e);new MutationObserver(e=>{for(let t of e)if(t.type===`childList`)for(let e of t.addedNodes)e.tagName===`LINK`&&e.rel===`modulepreload`&&n(e)}).observe(document,{childList:!0,subtree:!0});function t(e){let t={};return e.integrity&&(t.integrity=e.integrity),e.referrerPolicy&&(t.referrerPolicy=e.referrerPolicy),e.crossOrigin===`use-credentials`?t.credentials=`include`:e.crossOrigin===`anonymous`?t.credentials=`omit`:t.credentials=`same-origin`,t}function n(e){if(e.ep)return;e.ep=!0;let n=t(e);fetch(e.href,n)}})();async function e(){let e=await fetch(`/api/runs`);if(!e.ok)throw Error(`Failed to load runs (${e.status})`);return e.json()}async function t(e){let t=await fetch(`/api/runs/${encodeURIComponent(e)}/cues`);if(!t.ok)throw Error(`Failed to load cues (${t.status})`);return t.json()}var n=document.querySelector(`#app`);if(!n)throw Error(`#app missing`);var r={barge_in:`Barge-in`,script_cue:`Script cue`,silence_wait:`User pause (script)`,silence:`Silence detected`,interruption:`Interruption`,recovery:`Agent recovery`},i=[`barge_in`,`silence_wait`,`silence`,`interruption`,`recovery`,`script_cue`];function a(){return new URLSearchParams(location.search).get(`run`)}function o(e){let t=new URL(location.href);e?t.searchParams.set(`run`,e):t.searchParams.delete(`run`),history.pushState({},``,t)}function s(e){let t=Math.max(0,e)/1e3;return`${Math.floor(t/60)}:${(t%60).toFixed(1).padStart(4,`0`)}`}function c(e){return r[e]||e.replace(/_/g,` `)}function l(e,t){e.innerHTML=`
    <main class="page">
      <header class="header">
        <h1>lk-sim reports</h1>
        <p class="muted">Pick a run to play audio with time-synced transcript + behavior markers.</p>
      </header>
      <ul class="run-list" id="runs"></ul>
      <p class="muted ${t.length?`hidden`:``}" id="empty">
        No reports found under <code>.agent-sim/reports/</code>.
      </p>
    </main>
  `;let n=e.querySelector(`#runs`);if(n)for(let e of t){let t=document.createElement(`li`),r=document.createElement(`button`);r.type=`button`,r.className=`link`,r.textContent=e.run_id,r.addEventListener(`click`,()=>{o(e.run_id),T(e.run_id)});let i=document.createElement(`span`);i.className=`muted`,i.textContent=` — `+[e.status||`?`,e.turn_count==null?null:`${e.turn_count} turns`,e.duration_ms==null?null:`${(e.duration_ms/1e3).toFixed(1)}s`,e.has_audio?`audio`:`no audio`].filter(Boolean).join(` · `),t.append(r,i),n.appendChild(t)}}function u(e,t){let n=e.toLowerCase();return n===`agent`?`Agent`:n===`user`?t===`script_barge`?`Script inject`:t===`script_cue`?`Script cue`:`Caller`:e}function d(e,t){let n=e.toLowerCase();return n===`agent`?`role-agent`:n===`user`&&t===`script_barge`?`role-script-barge`:n===`user`&&t===`script_cue`?`role-script-cue`:n===`user`?`role-user`:`role-other`}function f(e,t){e.innerHTML=`
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
          <p class="hint muted">Stereo WAV · click a bubble or band to seek · scroll anytime (follow pauses until you re-enable)</p>
        </section>
      </div>
      <section class="transcript-panel">
        <div class="section-head">
          <h2 class="section-title">Conversation</h2>
          <span class="section-hint">Full-width 3 columns · Agent · Script/events · Caller</span>
        </div>
        <div class="col-headers" aria-hidden="true">
          <div class="col-h agent">Agent</div>
          <div class="col-h script">Script / events</div>
          <div class="col-h user">Caller</div>
        </div>
        <ol id="cues" class="cues"></ol>
      </section>
    </main>
  `,e.querySelector(`#back`)?.addEventListener(`click`,()=>{w?.abort(),w=null,o(null),E()});let n=e.querySelector(`#title`);return n&&(n.textContent=t),{audio:e.querySelector(`#audio`),cuesEl:e.querySelector(`#cues`),subtitle:e.querySelector(`#subtitle`),missing:e.querySelector(`#audio-missing`),timeline:e.querySelector(`#timeline`),playhead:e.querySelector(`#playhead`),legend:e.querySelector(`#legend`),verify:e.querySelector(`#verify`),followBtn:e.querySelector(`#follow`)}}function p(e){return e<1e3?`${e}ms`:`${(e/1e3).toFixed(1)}s`}function m(e,t,n,r,a){e.innerHTML=``;let o=[];t&&typeof t.pass==`boolean`&&(o.push({text:`script ${t.pass?`pass`:`fail`}`,cls:t.pass?`chip pass`:`chip fail`}),t.agent_finals_after_barge_in!=null&&o.push({text:`recovery finals: ${t.agent_finals_after_barge_in}`,cls:`chip`}),t.agent_finals_after_silence!=null&&o.push({text:`after silence: ${t.agent_finals_after_silence}`,cls:`chip`}));let s=!1;if(n&&typeof n.pass==`boolean`&&!n.skipped){o.push({text:`assert ${n.pass?`pass`:`fail`}`,cls:n.pass?`chip pass`:`chip fail`});for(let e of n.checks||[])if(e.type===`recovery`){s=!0;let t=e.pass!==!1,n=[`recovery`];e.recovery_ms!=null&&n.push(p(Number(e.recovery_ms))),e.agent_finals_after_barge_in!=null&&n.push(`${e.agent_finals_after_barge_in} finals`),o.push({text:n.join(` · `),cls:t?`chip pass`:`chip fail`})}}if(a&&(a.barges_fired&&o.push({text:`barges ×${a.barges_fired}${a.barges_during_agent?` (${a.barges_during_agent} mid-agent)`:``}`,cls:`chip`}),a.silences_held&&o.push({text:`silence holds ×${a.silences_held}`,cls:`chip`}),!s))if(a.recovery_ms!=null&&a.recovery_ms>=0){let e=a.recovery_assert_pass===!0?`chip pass`:a.recovery_assert_pass===!1?`chip fail`:`chip`;o.push({text:`recovery ${p(a.recovery_ms)}`,cls:e})}else a.barges_fired&&(a.agent_finals_after_barge??0)===0&&o.push({text:`recovery: none`,cls:`chip fail`});if(r)for(let e of i){let t=r[e];t&&o.push({text:`${c(e)} ×${t}`,cls:`chip`})}for(let t of o){let n=document.createElement(`span`);n.className=t.cls,n.textContent=t.text,e.appendChild(n)}}function h(e,t){e.innerHTML=``;let n=new Set(t.map(e=>e.type)),r=i.filter(e=>n.has(e));for(let e of t)r.includes(e.type)||r.push(e.type);if(!r.length){e.innerHTML=`<span class="muted">No barge-in / silence / interruption markers in this run.</span>`;return}for(let t of r){let n=document.createElement(`span`);n.className=`legend-item`,n.innerHTML=`<span class="swatch ${t}"></span>`;let r=document.createElement(`span`);r.textContent=c(t),n.appendChild(r),e.appendChild(n)}}function g(e,t,n,r,i){for(let t of Array.from(e.querySelectorAll(`.timeline-band`)))t.remove();let a=Math.max(r,1);for(let t of n){let n=document.createElement(`button`);n.type=`button`,n.className=`timeline-band ${t.type}`;let r=t.start_ms/a*100,o=Math.max(.4,(t.end_ms-t.start_ms)/a*100);n.style.left=`${r}%`,n.style.width=`${o}%`,n.title=`${c(t.type)}: ${t.label}\n${s(t.start_ms)} – ${s(t.end_ms)}${t.detail?`
`+t.detail:``}`,n.addEventListener(`click`,e=>{e.stopPropagation(),i.src&&(i.currentTime=(t.start_ms||0)/1e3,i.play().catch(()=>void 0))}),e.appendChild(n)}e.appendChild(t),e.onclick=t=>{if(!i.src||!r)return;let n=e.getBoundingClientRect(),a=t.clientX-n.left;i.currentTime=Math.min(1,Math.max(0,a/n.width))*r/1e3,i.play().catch(()=>void 0)}}function _(e,t){let n=[];for(let t of e)n.push({kind:`cue`,start_ms:t.start_ms,end_ms:t.end_ms,cue:t});for(let e of t)n.push({kind:`marker`,start_ms:e.start_ms,end_ms:e.end_ms,marker:e});return n.sort((e,t)=>e.start_ms===t.start_ms?e.kind===t.kind?0:e.kind===`marker`?-1:1:e.start_ms-t.start_ms),n}function v(e,t,n,r){e.innerHTML=``;let i=[];for(let a of t){let t=document.createElement(`li`);if(t.dataset.start=String(a.start_ms),t.dataset.end=String(a.end_ms),a.kind===`marker`){let e=a.marker;t.className=`cue-row marker ${e.type}`,t.innerHTML=`
        <div class="cue-card marker ${e.type}">
          <div class="cue-meta">
            <span class="role marker-type ${e.type}"></span>
            <span class="time"></span>
            <span class="tag ${e.type}"></span>
          </div>
          <div class="cue-text"></div>
          <div class="cue-detail"></div>
        </div>
      `;let n=t.querySelector(`.role`),r=t.querySelector(`.time`),i=t.querySelector(`.tag`),o=t.querySelector(`.cue-text`),l=t.querySelector(`.cue-detail`);n&&(n.textContent=c(e.type)),r&&(r.textContent=`${s(e.start_ms)} – ${s(e.end_ms)}`),i&&(i.textContent=e.step_id||e.type),o&&(o.textContent=e.label+(e.say?` · “${e.say}”`:``)),l&&(l.textContent=e.detail||``,e.detail||l.classList.add(`hidden`))}else{let e=a.cue,n=(e.role||`other`).toLowerCase(),r=e.speech_origin||`natural`,i=d(n,r),o=r===`script_barge`||r===`script_cue`;t.className=`cue-row ${i}`,t.dataset.role=n,t.dataset.origin=r,t.innerHTML=o?`
        <div class="cue-card ${i} inject-card">
          <div class="script-banner" aria-hidden="true">
            <span class="script-banner-icon">⚡</span>
            <span class="script-banner-title">SCRIPT INJECT</span>
            <span class="script-banner-sub">not Caller · mid-agent cut-in</span>
          </div>
          <div class="cue-meta">
            <span class="role origin-${r}"></span>
            <span class="time"></span>
            <span class="tags"></span>
          </div>
          <div class="cue-text"></div>
          <div class="cue-detail script-origin"></div>
        </div>
      `:`
        <div class="cue-card ${i}">
          <div class="cue-meta">
            <span class="role ${n} origin-${r}"></span>
            <span class="time"></span>
            <span class="tags"></span>
          </div>
          <div class="cue-text"></div>
          <div class="cue-detail script-origin hidden"></div>
        </div>
      `;let l=t.querySelector(`.role`),f=t.querySelector(`.time`),p=t.querySelector(`.cue-text`),m=t.querySelector(`.tags`),h=t.querySelector(`.cue-detail.script-origin`);if(l&&(l.textContent=u(e.role,r)),f&&(f.textContent=o?`inject ${s(e.inject_ms??e.start_ms)} · ${s(e.start_ms)}–${s(e.end_ms)}`:`${s(e.start_ms)} – ${s(e.end_ms)}`),p&&(p.textContent=e.text),m){if(o){let t=document.createElement(`span`);if(t.className=`tag script_barge`,t.textContent=r===`script_barge`?`barge_in`:`script`,m.appendChild(t),e.synthetic){let e=document.createElement(`span`);e.className=`tag script_barge`,e.textContent=`from Script`,m.appendChild(e)}}if(e.marker_tags?.length)for(let t of e.marker_tags){if(o&&t===`barge_in`)continue;let e=document.createElement(`span`);e.className=`tag ${t}`,e.textContent=c(t),m.appendChild(e)}}h&&o&&(h.textContent=[e.script_step_id?`step: ${e.script_step_id}`:null,e.script_say&&e.script_say!==e.text?`script say: “${e.script_say}”`:null,`Do not treat as persona Caller turn`].filter(Boolean).join(` · `))}t.addEventListener(`click`,()=>{n.src&&(n.currentTime=(a.start_ms||0)/1e3,r(),n.play().catch(()=>void 0))}),e.appendChild(t),i.push(t)}return i}function y(e,t){e.classList.toggle(`on`,t),e.classList.toggle(`off`,!t),e.textContent=t?`Follow live`:`Follow paused`,e.setAttribute(`aria-pressed`,t?`true`:`false`)}function b(e){let t=e.dataset.origin||``;return e.classList.contains(`role-script-barge`)||t===`script_barge`?0:e.classList.contains(`marker`)&&e.classList.contains(`barge_in`)?1:e.classList.contains(`role-script-cue`)||t===`script_cue`?2:e.classList.contains(`marker`)?4:3}function x(e,t){let n=-1,r=99,i=1/0,a=-1;for(let o=0;o<e.length;o++){let s=Number(e[o].dataset.start),c=Number(e[o].dataset.end);if(Number.isFinite(s)&&((!Number.isFinite(c)||c<=s)&&(c=s+900),t>=s&&(a=o),t>=s&&t<c)){let t=c-s,a=b(e[o]);(a<r||a===r&&t<i)&&(r=a,i=t,n=o)}}return n>=0?n:a}function S(e,t){let n=e.querySelector(`:scope > .cue-card`)||e,r=n.querySelector(`:scope > .now-badge`);t?r||(r=document.createElement(`span`),r.className=`now-badge`,r.textContent=`Now`,n.appendChild(r)):r&&r.remove()}function C(e,t,n,r,i){let a=(t.currentTime||0)*1e3,o=x(e,a);if(e.forEach((e,t)=>{let n=t===o;e.classList.toggle(`active`,n),e.setAttribute(`aria-current`,n?`true`:`false`),S(e,n)}),i.enabled&&o>=0&&o!==i.lastActive){let t=e[o],n=document.querySelector(`.player-dock`),r=n?n.getBoundingClientRect().bottom+12:100,a=t.getBoundingClientRect();a.top>=r&&a.bottom<=window.innerHeight-24||(i.suppressScrollUntil=performance.now()+450,t.scrollIntoView({block:`nearest`,behavior:`smooth`}))}if(i.lastActive=o,r>0){let e=Math.min(100,Math.max(0,a/r*100));n.style.left=`${e}%`}}var w=null;async function T(e){w?.abort(),w=new AbortController;let{signal:r}=w,i=f(n,e),a={enabled:!0,suppressScrollUntil:0,lastActive:-1};y(i.followBtn,!0),i.followBtn.addEventListener(`click`,()=>{a.enabled=!a.enabled,y(i.followBtn,a.enabled),a.enabled&&(a.lastActive=-2)},{signal:r});let o=()=>{performance.now()<a.suppressScrollUntil||a.enabled&&(a.enabled=!1,y(i.followBtn,!1))};window.addEventListener(`wheel`,o,{passive:!0,signal:r}),window.addEventListener(`touchmove`,o,{passive:!0,signal:r}),window.addEventListener(`keydown`,e=>{(e.key===`PageUp`||e.key===`PageDown`||e.key===`Home`||e.key===`End`||(e.key===`ArrowUp`||e.key===`ArrowDown`)&&!(e.target instanceof HTMLInputElement)&&!(e.target instanceof HTMLTextAreaElement)&&!(e.target instanceof HTMLSelectElement))&&o()},{signal:r});try{let n=await t(e),r=n.markers||[],o=n.audio?.duration_ms==null?Math.max(0,...r.map(e=>e.end_ms),...(n.cues||[]).map(e=>e.end_ms))||1:Number(n.audio.duration_ms);n.scenario_id&&(i.subtitle.textContent=`scenario: ${n.scenario_id}`),n.audio?.file?i.audio.src=`/runs/${encodeURIComponent(e)}/${n.audio.file}`:i.missing.classList.remove(`hidden`);let s=n.behavior_summary||n.caller?.behavior_summary||null;m(i.verify,n.script_verify,n.assert_verify,n.marker_counts,s),h(i.legend,r),g(i.timeline,i.playhead,r,o,i.audio);let c=()=>{a.enabled=!0,y(i.followBtn,!0),a.lastActive=-2},l=_(n.cues||[],r),u=v(i.cuesEl,l,i.audio,c);u.length||(i.subtitle.textContent=(i.subtitle.textContent||``)+` · no transcript/markers found`);let d=()=>C(u,i.audio,i.playhead,o,a);i.audio.addEventListener(`timeupdate`,d),i.audio.addEventListener(`seeked`,d),i.audio.addEventListener(`play`,()=>{let e=()=>{i.audio.paused||(d(),requestAnimationFrame(e))};requestAnimationFrame(e)})}catch(e){i.subtitle.className=`error`,i.subtitle.textContent=String(e)}}async function E(){try{l(n,await e())}catch(e){n.innerHTML=`<main class="page"><p class="error">${String(e)}</p></main>`}}async function D(){let e=a();e?await T(e):await E()}window.addEventListener(`popstate`,()=>{D()}),D();
//# sourceMappingURL=index-CEv8Yg9s.js.map