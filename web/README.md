# lk-sim web UI (Vite + TypeScript)

Standard Vite layout. CI builds `web/dist/` and Hatch force-includes it into the
wheel as `livekit_agent_simulator/web_static/`. Built assets are **not** committed.

## Dev (HMR)

Terminal 1 — API + reports:

```bash
uv run lk-sim web --root /path/to/target
```

Terminal 2 — frontend:

```bash
pnpm install
pnpm dev
```

Open http://localhost:5173 — proxies `/api` and `/runs` to port 8765.

## Build (maintainers)

```bash
pnpm install
pnpm build          # → web/dist/
```

Then `uv build` (or release CI) packs `web/dist` into the wheel as `web_static`.
Editable checkouts also serve `web/dist` directly via `lk-sim web`.

## Layout

```
web/
  index.html
  public/
  src/
    main.ts
    components/
    lib/
    player/
    types.ts
    api.ts
    style.css
  dist/             # gitignored — vite build output
```
