# 06 · The Dashboard

> Folder: [`dashboard/`](../dashboard/) (Vite + React + Tailwind)

## Architecture

```
┌──────────────┐       /api/*       ┌──────────────┐
│ React (Vite) │ ──────────────────►│ Flask (5050) │
│ port 5173    │ ◄──────────────────│              │
└──────────────┘                    └──────────────┘
                                          │
                                          ▼
                                  ┌────────────────┐
                                  │ LangGraph run  │
                                  │ JSON in api/   │
                                  │ data/runs/     │
                                  └────────────────┘
```

The dashboard never talks to the LLM, the scraper, or MCP directly. It
only reads JSON files via Flask. That isolation is why you can demo it
offline with sample data.

## Folder structure

```
dashboard/
├── index.html
├── package.json
├── vite.config.js          ← Vite proxies /api to Flask
├── tailwind.config.js
└── src/
    ├── main.jsx
    ├── App.jsx              ← tab + week router
    ├── api.js               ← fetch wrapper
    ├── styles.css
    └── components/
        ├── Sidebar.jsx
        ├── WeeklyPulse.jsx  ← the main view from the screenshot
        ├── FeeExplainer.jsx
        ├── RunHistory.jsx
        ├── Settings.jsx
        └── EmailModal.jsx
```

## State model

`App.jsx` owns three pieces of state:

| state | source |
|---|---|
| `tab` | which sidebar nav item is active |
| `week` | which run to show — switches via the sidebar select or RunHistory |
| `data` | the response from `/api/weekly?week=…` |

Everything below `App.jsx` is presentational. Components receive props,
render UI, and call `api.*` from `api.js`. No global store needed.

## The vite proxy

`vite.config.js`:

```js
server: {
  proxy: { '/api': 'http://127.0.0.1:5050' }
}
```

This lets the React app call `/api/weekly` in dev without CORS pain. In
production you'd either serve the built React bundle from Flask or front
both with nginx.

## Tailwind tips used here

- **Arbitrary colors** via the theme: `bg-[#0e1729]` matches the screenshot.
- **Gradient bars** for sentiment: `bar-grad-neg/neu/pos` are utility
  classes in `styles.css`.
- **Grid for the dashboard layout**: the middle row is `grid-cols-12` with
  `col-span-5 / 5 / 2`, which mirrors the screenshot exactly.

## Email Snapshot modal

The "View Email Snapshot" badge opens `EmailModal.jsx`. It loads the same
HTML that the Gmail draft would contain via `/api/email-snapshot`. Two
buttons:

- **Append to Doc** — POSTs to `/api/mcp/approve` with `gate=doc`
- **Create Gmail Draft** — POSTs with `gate=email`

Either button is the explicit, gated human approval. No auto-send.

## Run it

```bash
# terminal 1 — pipeline + API
python -m pipeline.run_weekly        # one-time, seeds api/data/runs/
python -m api.app                    # serves Flask on :5050

# terminal 2 — dashboard
cd dashboard
npm install
npm run dev                          # opens :5173
```
