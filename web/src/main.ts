import "./style.css";
import { fetchRuns } from "./api";
import { renderRunList } from "./components/run-list";
import { showPlayer } from "./player/show-player";
import { runFromUrl, setRunInUrl } from "./lib/url";

const appRoot = document.querySelector<HTMLDivElement>("#app");
if (!appRoot) throw new Error("#app missing");
const app: HTMLElement = appRoot;

let playerListeners: AbortController | null = null;

async function showList(): Promise<void> {
  try {
    const runs = await fetchRuns();
    renderRunList(app, runs, (runId) => {
      setRunInUrl(runId);
      void openPlayer(runId);
    });
  } catch (e) {
    app.innerHTML = `<main class="page"><p class="error">${String(e)}</p></main>`;
  }
}

async function openPlayer(runId: string): Promise<void> {
  playerListeners?.abort();
  playerListeners = new AbortController();
  await showPlayer(app, runId, playerListeners.signal, () => {
    playerListeners?.abort();
    playerListeners = null;
    setRunInUrl(null);
    void showList();
  });
}

async function boot(): Promise<void> {
  const run = runFromUrl();
  if (run) await openPlayer(run);
  else await showList();
}

window.addEventListener("popstate", () => {
  void boot();
});

void boot();
