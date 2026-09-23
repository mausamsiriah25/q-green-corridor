# SIH Screenshot Set — capture guide

**Why this is a guide and not a folder of PNGs:** this build environment has no network access
to npm/pip registries and no browser/display, so `npm install` and `pip install` can't run here
and the app can't actually be launched or screenshotted in this sandbox. Every screenshot below
must be captured by *you*, running the real app locally (§7 of the README), following the exact
state/action sequence given — nothing here is a mockup, so the sequence below reproduces real
application state.

Save files into `/screenshots/sih/` using the names below.

Setup once, before shooting anything:

```bash
# terminal 1
cd backend && uvicorn main:app --reload --port 8000
# terminal 2
cd frontend && npm install && npm run dev
```

Open the frontend URL Vite prints (typically `http://localhost:5173`). For mobile shots, use
your browser's device toolbar (Chrome DevTools → Toggle device toolbar, or Firefox Responsive
Design Mode) set to **390 × 844**. For desktop shots, use a normal window sized to
**1440 × 900**. Close any DevTools panel before capturing so it doesn't appear in frame.

---

### 01_driver_emergency.png — Driver, emergency activation

1. Set viewport to 390×844, reload.
2. Click **🚑 DRIVER MODE** in the header if not already selected.
3. Confirm you see the idle state: "Ambulance AMB-01 · Standing by" and the big
   **🚨 ACTIVATE EMERGENCY** button.
4. Screenshot the idle state first (optional bonus shot), then click the button.
5. Wait ~1–2s for QPSO to return a route (the button disables briefly).
6. Screenshot once the sheet shows **🚨 EMERGENCY ACTIVE** and **GREEN CORRIDOR: ACTIVE**.

*Supports: Proposed Solution slide.*

### 02_driver_navigation.png — Driver, live navigation

1. Immediately after (01), leave the tab open — the ambulance is now moving.
2. Wait until the instruction card shows a genuine turn (not just "Continue straight") — watch
   for **"Turn LEFT in …"** or **"Turn RIGHT in …"**; this can take a few seconds depending on
   the route QPSO returned. If the first route has no turn near the start, that's fine — any
   real instruction works, or wait for the ambulance to approach a signal so you also capture
   "🚦 Approaching S… — PREPARE/PRIORITY".
3. Screenshot showing: route on map, instruction card, ETA + distance stats, green corridor pill.

*Supports: Proposed Solution / Innovation slide.*

### 03_control_center.png — Traffic Control Center overview

1. Set viewport to 1440×900.
2. Click **🖥️ CONTROL CENTER** in the header.
3. With the same mission still active (or start a new one via "START EMERGENCY" in the left
   panel), screenshot the full dashboard: map, emergency panel, optimization panel, command log.

*Supports: Proposed Solution / System Overview slide.*

### 04_green_corridor.png — Green corridor active

1. Still in Control Center, with an active mission on a route that passes at least two signals
   (S2, S5 or S8 — if your QPSO route only touches one, click **🔄 RE-OPTIMIZE** once or twice;
   the seeded traffic drift will occasionally produce a different route).
2. Wait until the map shows one signal marker glowing green (PRIORITY) and another amber
   (PREPARE) — check the Command Log panel for a `PRIORITY` line to confirm timing.
3. Screenshot with the map framed on the priority signal and the command log visible.

*Supports: Innovation / Proposed Solution slide.*

### 05_incident_rerouting.png — Incident + re-routing

1. Still in Control Center with an active mission, click **⚠ INJECT TRAFFIC INCIDENT**.
2. Screenshot within ~1s of clicking — you should see the alert banner
   ("⚠ Incident on … — route disrupted, re-optimizing…"), the old route (purple dashed) and the
   blocked road (red dashed) both visible on the map before the new route replaces it.

*Supports: Innovation / Impact slide.*

### 06_new_green_corridor.png — New green corridor after re-routing

1. Immediately after (05), wait ~1s for the alert "New route found — green corridor updated."
2. Screenshot the map with the new route highlighted green, updated signal states, and (if in
   Driver Mode instead) the updated instruction card / ETA.

*Supports: Innovation slide.*

### 07_mission_completed.png — Mission completed

1. Easiest path: click **🚀 RUN FULL DEMO** from a fresh reset and let it play through to the
   end (it injects its own incident and re-optimizes automatically) — watch the demo progress
   bar reach 100% / "🏥 Hospital reached — mission complete!"
2. In Driver Mode you'll see the **🏥 ARRIVED — MISSION COMPLETED** banner over the map and the
   sheet's **✅ MISSION COMPLETE** pill; in Control Center the mission tag shows `COMPLETED` and
   all signals have returned to NORMAL (grey) in both the map and the command log's last
   entries.
3. Screenshot either view (Driver Mode arrival banner is the more visual choice).

*Supports: Impact / Results slide.*

### 08_qpso_analytics.png — QPSO / analytics dashboard

1. In Control Center, scroll to the Analytics panel at the bottom.
2. Click **RUN BENCHMARK** to populate the Dijkstra/A*/QPSO/PSO/GA comparison table with real
   numbers, and make sure the QPSO convergence chart has data (it populates automatically after
   any `optimize`/`reoptimize` call — run one first if the chart is empty).
3. Screenshot the Convergence tab and/or Benchmark tab with real values visible.

*Supports: Technical credibility / Research slide.*

---

## Index for the SIH PPT

| Screenshot | Demonstrates | Suggested slide |
|---|---|---|
| `01_driver_emergency.png` | Emergency activation from the ambulance app | Proposed Solution |
| `02_driver_navigation.png` | Turn-by-turn navigation computed from route geometry | Proposed Solution / Innovation |
| `03_control_center.png` | Full Traffic Control Center dashboard | System Overview |
| `04_green_corridor.png` | ETA-based signal priority coordination | Innovation / Proposed Solution |
| `05_incident_rerouting.png` | Live incident detection + disrupted route | Innovation / Impact |
| `06_new_green_corridor.png` | QPSO re-optimization + new signal sequence | Innovation |
| `07_mission_completed.png` | End-to-end mission completion, signals reset | Impact / Results |
| `08_qpso_analytics.png` | QPSO convergence + algorithm benchmark | Technical credibility / Research |

## Responsive check (no dedicated screenshot required, but verify before shooting)

Resize the browser (or DevTools device toolbar) through 320 / 375 / 390 / 430 / 768 / 1024 /
1280 / 1440 / 1920px in both Driver Mode and Control Center. Nothing should horizontally scroll,
overlap, or require a hover to reach — the emergency button and instruction card must stay fully
visible and tappable at every width down to 320px.
