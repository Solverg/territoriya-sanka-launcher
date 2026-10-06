# Prototype Instructions

Run the local server yourself and open the preview in the browser available to this environment. Do not give the user server-start instructions when you can run it.

Before making substantial visual changes, use the Product Design plugin's `get-context` skill when the visual source is unclear or no longer matches the current goal. When the user gives durable prototype-specific design feedback, preferences, or decisions, record them in `AGENTS.md`.

When implementing from a selected generated mock, treat that image as the source of truth for layout, component anatomy, density, spacing, color, typography, visible content, and hierarchy.

Build app UI in `src/`. Keep `.openai/hosting.json`, `worker/index.js`, `scripts/prepare-sites-build.mjs`, and `tests/sites-worker.test.mjs` intact so the same local prototype can be handed to Sites. Before a Sites handoff, run `npm run build` and `npm run test:sites`; the build must leave `dist/client/index.html`, `dist/server/index.js`, and `dist/.openai/hosting.json`.

## Publication safety

Treat the local worktree and public `origin/main` as distinct release tracks.
Before a push, tag, or GitHub Release, fetch `origin/main --tags`, inspect the
history graph and review exactly what will be published. Do not force-push or
reset published history. Never upload local configuration, app-data paths,
MODLOG/design logs, game installations, saves, extracted assets, decompiled
code, signing keys, credentials, or unreviewed build output. The only permitted
game payloads are intentionally packaged project-owned PBO ZIPs under `mods/`
(currently Contact Fuse Drone and Fuel Canister), after each manifest and
SHA-256 have been verified. See `MODLOG.md` for the v1.2.1
history/authentication gotcha before attempting the next GitHub synchronization.
