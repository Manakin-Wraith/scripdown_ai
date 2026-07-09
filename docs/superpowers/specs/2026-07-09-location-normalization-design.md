# Location Normalization Design

**Date:** 2026-07-09
**Status:** Draft for review
**Supersedes the daily-driver role of:** `2026-07-09-location-dedup-merge.md` (manual merge stays, but only for genuine synonyms)

## Problem

Location duplicates in the breakdown are overwhelmingly **casing / whitespace / quote
noise** produced at extraction time: `villa` / `viLLA` / `VILLA`,
`WEDDING VENUE` / `wEDDING VENUE`, `reSORT pool` / `RESORT POOL`,
`Tam'S ROOM` / `tam's room` / `tam’s room`. In an all-caps slugline world casing
carries no meaning, yet each variant currently surfaces as its own location across
the breakdown, schedule, stripboard, and reports.

The manual merge tool built to clean these up has repeatedly failed in production for
**plumbing** reasons, not conceptual ones — an access gate (403), normalize-collapse
(400), and a backend deploy that did not land (old code still live). Making casing
cleanup depend on a manual click + a backend endpoint + a Railway deploy is the wrong
level to solve a data-consistency problem.

## Goal

Location identity is **normalized data**, not a manual chore. Casing/whitespace/quote
variants collapse automatically and permanently. The manual merge shrinks to its real
job: genuinely different names (`coffee shop` vs `café`).

## Core rule — one canonicalization function

```
canonicalize(setting):
    s = setting.strip()
    s = collapse_internal_whitespace(s)      # "VILLA  - X" -> "VILLA - X"
    s = s.replace('’', "'").replace('‘', "'") # curly -> straight quotes
    s = s.upper()                             # slugline convention
    return s
```

Properties:
- **Deterministic and idempotent** — `canonicalize(canonicalize(x)) == canonicalize(x)`.
- **Conservative** — it does NOT strip suffixes, articles, or guess synonyms.
  `VILLA - NEXT MORNING` stays distinct from `VILLA`; `coffee shop` stays distinct
  from `café`. Those remain a manual decision.
- **UPPERCASE** is the canonical casing (slugline convention, matches report output).

`location_canonical` (the production-view grouping key) continues to be computed by the
existing `normalize_place()` (which additionally strips leading `THE/A/AN` and
surrounding punctuation). `setting` stays human-readable (articles kept); only casing,
whitespace, and quotes are normalized. Both are derived from the same normalized text so
they never diverge.

## Part A — One-time data cleanup (no deploy)

Run `canonicalize()` over `scenes.setting` and recompute `location_canonical` for **all
scripts owned by the user** (5 scripts, 327 scenes with settings; 195 distinct settings →
181 after normalization). Executed directly against the database via Supabase — **no
Railway deploy required**, which is what fixes the currently-visible dupes immediately.

- Before-state (`id, setting, location_canonical`) captured to a scratchpad JSON file for
  full reversibility, exactly as the villa cleanup was.
- Because the breakdown UI already groups by stored `setting`, once the data is
  consistent the variants collapse into single rows with no further code change.
- The 3 `VILLA - BACHELORETTE` scenes and other genuinely-distinct suffixed labels are
  left as their own locations (conservative rule).

## Part B — Normalize at ingestion (one backend deploy)

Apply `canonicalize()` in the scene-write path of the extraction pipeline so newly
uploaded or edited scenes store the canonical form. This prevents recurrence.

- Add `canonicalize_setting()` to `backend/services/location_resolver.py`.
- Call it wherever a scene's `setting` is written: the upload/parse path plus the manual
  scene-edit endpoints in `supabase_routes.py` (`create_scene`, `update_scene`,
  `update_scene_header`, `add-scene`, split). The existing `_apply_location_alias` helper
  already runs at these sites and computes `location_canonical`; `canonicalize()` feeds
  it a clean `setting`.
- Unit tests for `canonicalize_setting()` covering casing, whitespace, curly quotes, and
  idempotency.
- **Requires Railway to actually deploy `main`.** The current failure proved the deploy
  path is unreliable; landing this (and confirming the deployed commit) is a prerequisite
  for Parts B and C to take effect. Part A does not depend on it.

## Part C — Manual merge becomes a synonym-only fallback

The raw-setting `merge_locations` already in `main` (matches scenes by raw setting
case-insensitively, rewrites to the chosen spelling, recomputes `location_canonical`) is
retained unchanged. With Part A + B in place it is rarely needed — only for merging
genuinely different names. It rides the same Part B deploy.

## Out of scope

- Synonym detection / fuzzy auto-merge (kept manual, deliberately).
- Stripping time-of-day or descriptive suffixes from `setting` (manual decision).
- Normalizing other free-text breakdown fields (characters already handled separately).

## Testing / verification

- `canonicalize_setting()` unit tests (backend).
- Part A: post-cleanup SQL assertion that no two settings within a script differ only by
  casing/whitespace/quotes.
- Production: reload the script, confirm variant rows have collapsed to single rows in the
  breakdown; confirm before-state JSON exists for rollback.
- Part B: after deploy, edit a scene setting to a lower-case variant and confirm it is
  stored uppercased.
```
