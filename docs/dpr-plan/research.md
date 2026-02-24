# Research: Daily Production Reporting (DPR)

**Phase 0 Output** | **Date**: 2026-02-23

---

## 1. QR Code Generation for PDF Footer (FR-031a)

**Decision**: Use `qrcode[pil]` Python package  
**Rationale**: Lightweight, pure-Python QR code generation. Integrates with WeasyPrint by rendering QR as inline base64 PNG in HTML template. No external service dependency.  
**Alternatives considered**:
- `segno` — Lighter but less PIL integration; `qrcode` is more widely used
- External QR API (e.g., goqr.me) — Adds network dependency, unacceptable for offline/low-bandwidth scenarios
- Skip QR, use URL only — Spec explicitly requires QR code for insurance/bonding/legal workflows

**Implementation**: Generate QR containing `https://app.slateone.studio/dpr/{dpr_id}/verify`. Encode as base64 PNG. Embed in WeasyPrint HTML template footer via `<img src="data:image/png;base64,...">`.

**Dependency**: Add `qrcode[pil]==7.4.2` to `requirements.txt`. PIL dependency already satisfied by existing packages.

---

## 2. Charting Library for Analytics Dashboard

**Decision**: Use `recharts` (React)  
**Rationale**: Most popular React charting library. Declarative API matches existing component patterns. Supports line charts (burndown), bar charts (delays), and composed charts (velocity). Tree-shakeable for bundle size.  
**Alternatives considered**:
- `chart.js` + `react-chartjs-2` — More imperative, heavier bundle
- Custom SVG — Too much effort for burndown + delay charts; SceneArcTimeline already uses custom SVG but DPR analytics needs more chart types
- `nivo` — Beautiful but heavier, overkill for 3 chart types
- `visx` — Low-level, requires more code

**Implementation**: `npm install recharts` in frontend. Use `<LineChart>` for burndown, `<BarChart>` for delay analysis, `<ComposedChart>` for velocity gauge.

---

## 3. Snapshot Architecture (AD-2)

**Decision**: Denormalized snapshot columns on `dpr_scene_entries` table  
**Rationale**: Each scene entry stores a copy of scene metadata at DPR creation time. This is critical for legal defensibility — if scene data changes after the DPR is filed, the historical record must reflect what was planned at time of shooting. The spec explicitly requires this (FR-053–FR-057).  
**Alternatives considered**:
- Live JOINs to `scenes` table — Violates AD-2, no historical integrity
- Separate `scene_snapshots` table with versioned rows — Over-engineered; snapshot is only needed per DPR entry, not independently versionable
- JSONB blob on DPR — Loses queryability for analytics aggregation

**Implementation**: 8 snapshot columns on `dpr_scene_entries`: `snapshot_scene_number`, `snapshot_slugline`, `snapshot_int_ext`, `snapshot_location`, `snapshot_day_night`, `snapshot_planned_pages_eighths`, `snapshot_schedule_order`, `snapshot_unit_assignment`. Populated at DPR creation time from `scenes` + `shooting_day_scenes` JOIN.

---

## 4. Materialized Metrics Strategy (FR-027a)

**Decision**: Separate `dpr_materialized_metrics` table with explicit invalidation triggers  
**Rationale**: DPR analytics require aggregating across scene entries, delays, version chains, velocity flags, and multi-unit combinations. Computing this on every request would cause O(n²) query complexity. Pre-computing and invalidating on change gives O(1) reads.  
**Alternatives considered**:
- PostgreSQL materialized views — Can't do row-level invalidation; full refresh too expensive
- Application-level caching (Redis) — Adds infrastructure dependency not justified for MVP scale
- Compute on demand — Performance degrades with 60+ DPRs and multi-unit aggregation

**Implementation**: `dpr_materialized_metrics` table with `is_stale` flag. DB triggers on `dpr_scene_entries` and `dpr_delays` INSERT/UPDATE/DELETE set `is_stale = true`. Service-level `get_or_compute_metrics()` checks flag and recomputes if stale. Analytics service only reads non-stale metrics.

---

## 5. Multi-Unit Aggregation (AD-1, Gap Fix #2)

**Decision**: Three-level aggregation (unit → day → schedule) with combined-sum variance  
**Rationale**: Professional productions run 2-4 units simultaneously. Variance must be computed at each level without double-counting cross-unit pickups.  
**Alternatives considered**:
- Single-unit only — Doesn't serve professional productions
- Merge all units into one DPR — Loses per-unit accountability and department log separation

**Implementation**:
- **Per-unit**: Direct query on single DPR
- **Per-day (combined)**: Sum planned snapshots across all units for that day. Sum actual pages across all units. Compute net variance once from combined sums (NOT sum of per-unit variances).
- **Per-schedule (burndown)**: Planned baseline from unique scene pages in the schedule (each scene counted once). Actual pages summed across all canonical DPRs.

---

## 6. Velocity Denominator (Gap Fix #3, FR-073)

**Decision**: Distinct shooting days, not DPR record count  
**Rationale**: If 3 units shoot on the same day (3 DPR records), that's 1 day in the denominator. Using DPR count would deflate velocity.  

**Formula**: `Avg Pages/Day = Sum(actual_pages WHERE include_in_velocity = true) / Count(DISTINCT shooting_day_id WHERE ≥1 included DPR exists)`

---

## 7. Version Chain Architecture (AD-5)

**Decision**: Self-referential `parent_version_id` on DPR table with `is_superseded` flag  
**Rationale**: Simpler than a separate versions table. The DPR IS the version — each clone is a new DPR row. Canonical = latest non-superseded.  
**Alternatives considered**:
- Separate `dpr_versions` table — Adds JOIN complexity to every query
- Soft-delete + audit only — Loses immutability guarantee

**Implementation**: `daily_production_reports.parent_version_id` FK self-reference. `is_superseded` boolean. UNIQUE constraint on `(shooting_day_id, unit_id) WHERE is_superseded = false` ensures exactly one canonical DPR per day+unit. Clone copies all sub-entities, resets status/signoffs, preserves dept log submission state.

---

## 8. Time Entry Overnight Wrap (FR-021b)

**Decision**: TIMESTAMPTZ for call/wrap + `wrap_next_day` boolean flag  
**Rationale**: Using full timestamps handles day boundaries naturally. The `wrap_next_day` flag is a UI hint for the frontend to present "wraps next day" toggle rather than a date picker.  
**Alternatives considered**:
- TIME fields only — Can't handle day boundaries without hacks
- Two DATE + TIME fields — Over-complicated for the user
- Duration-only — Loses actual call/wrap time information

**Calculation**: `hours = wrap_time - call_time - sum(break_durations)`. If `wrap_next_day`, wrap_time is interpreted as next calendar day.

---

## 9. Approval Mode Configuration (AD-9)

**Decision**: Per-production config table with day-type overrides  
**Rationale**: Different productions and different day types have different department requirements. A Travel day shouldn't require Camera logs.  

**Implementation**: `production_approval_config` table with:
- `approval_mode` enum (Strict/Soft)
- `required_departments` JSONB (default list)
- `required_departments_by_day_type` JSONB (overrides per day type)

---

## 10. RLS Policy Chain for DPR Tables

**Decision**: Chain through `schedule → script → auth.uid()` for all DPR tables  
**Rationale**: DPR tables don't have a direct `user_id` column. Access is determined by script ownership through the schedule chain. This matches the existing pattern in `shooting_schedules` RLS policies.  
**Risk**: Deep subquery chains (4+ levels for sub-entities like scene entries). Mitigated by indexing FK columns.

**Future consideration**: When team-based access is needed (HODs editing their dept logs), RLS will need to include `script_members` JOIN. For MVP, service-key Supabase client bypasses RLS (existing pattern in all backend routes).

---

## 11. Low Bandwidth Mode (FR-043a)

**Decision**: Frontend-only toggle, persisted in localStorage  
**Rationale**: The backend API is already JSON-only. Low bandwidth mode is a UI concern — disabling image previews, attachment uploads, and heavy components. No backend changes needed.  

**Implementation**: `useLowBandwidthMode()` hook reads localStorage. Components conditionally render based on flag. Attachment uploads deferred until flag is toggled off.

---

## 12. Existing Schedule Extension Requirements

**Decision**: Minimal extension to `shooting_days` table  
**Rationale**: The DPR needs `shooting_days` to support unit assignments. Currently `shooting_day_scenes` only tracks scene→day mapping without unit. Migration 041 adds any necessary columns.  

**Analysis**: The `units` table (migration 031) adds the unit concept. Scene-to-unit assignment can be managed through the DPR scene entry snapshots (`snapshot_unit_assignment`) rather than modifying `shooting_day_scenes`. This minimizes changes to the existing schedule module.

---

## All Unknowns Resolved ✅

No NEEDS CLARIFICATION items remain. All technology choices, architecture patterns, and integration points have been researched and decided.
