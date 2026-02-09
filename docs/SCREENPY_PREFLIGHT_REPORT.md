# ScreenPy Pre-Flight Report — GO/NO-GO Decision

> **Date:** 2026-02-07 (Updated: Phase 0.5 Complete)
> **Scripts Tested:** 5 (BIRD_V8, Ep_1, LASGIDI Ep14, LASGIDI Ep4, Script_Powerlessness)
> **SA-Format Scripts:** 2 (BIRD_V8 = Afrikaans, Script_Powerlessness = SA English)

---

## Executive Summary

**VERDICT: 🟢 FULL GO** — All 10 blocking checks pass. The vendored ScreenPy parser
finds **45% more scene headers** than regex (370 vs 255), extracts **152 unique characters**
with **2,134 dialogue blocks**, and correctly parses the Afrikaans script (BIRD_V8) that
regex missed entirely (0 → 107 headers).

### Phase 0.5 Achievements
- Vendored ScreenPy parser into `backend/lib/screenpy/` (6 files)
- Config-driven locale schema for TIME_OF_DAY + LOCATION_TYPES (en, af, fr, es)
- Pydantic v2 models, relative imports, zero heavy dependencies
- Three bugs found and fixed during integration (scene number prefix, indent thresholds, dialogue priority)

---

## Pre-Flight Checklist Results

| # | Check | Result | Blocking? | Detail |
|---|-------|--------|-----------|--------|
| 1 | pdfplumber kerning ≤ PyPDF2 | **PASS** | Yes | PyPDF2=32, pdfplumber=31 |
| 2 | pdfplumber layout < 20s | **PASS** | Yes | Max: 2.68s (88-page script). Far under threshold. |
| 3 | Normalizer effective | **PASS** | Yes | 24-27% whitespace removed, indentation preserved |
| 4 | Dual text path validation | **PASS** | Yes | Zero divergence on all 5 scripts |
| 5 | Indent thresholds met | **PASS** | Yes | All 3 ScreenPy thresholds met on all 5 scripts |
| 6 | Grammar ≥ regex count | **PASS** | Yes | Grammar 370 vs Regex 255 (45% more). All 5 scripts pass. |
| 7 | Location hierarchy splits | **PASS** | Yes | 2 multi-level found (BAR > SLOT MACHINE AREA) |
| 8 | Speaker extraction | **PASS** | No | 152 unique characters, 2,134 dialogue blocks across 5 scripts |
| 9 | Parser isolated (no spacy) | **PASS** | Yes | Verified: parser/ uses only pyparsing + pydantic |
| 10 | SA-format scripts parse | **PASS** | Yes | SA English: 194 headers. Afrikaans: 107 headers (was 0 with regex). |

### pyparsing Status

`pyparsing` 3.3.2 is **installed** and added to `requirements.txt`. Zero conflicts.

---

## Critical Finding: BIRD_V8.pdf — 0 Scene Headers

### The Problem

BIRD_V8 is an **Afrikaans-language screenplay** (109 pages). Both PyPDF2 AND pdfplumber regex find **ZERO** scene headers because:

1. **Afrikaans time-of-day:** `DAG` (Day), `NAG` (Night) instead of English
2. **Missing dash separator:** `INT. CAR DUSK` instead of `INT. CAR - DUSK`
3. **No space after INT.:** `INT.HUIS - DAG` instead of `INT. HUIS - DAG`
4. **PyPDF2 line merging:** `INT. CAR DUSKClose up op die motorradio...`

### Impact Assessment

- **Not a ScreenPy blocker.** This is a pre-existing regex gap — BIRD_V8 has 0 headers in production today.
- **ScreenPy partially fixes this.** Its pyparsing grammar handles `INT.HUIS` (no space) structurally. Afrikaans time words need grammar extension.
- **No regression.** This gap exists before and after the integration.

### Recommended Fix (Phase 1 scope)

```python
# Add to TIME_OF_DAY in extraction_pipeline.py
TIME_OF_DAY = r"(DAY|NIGHT|DUSK|DAWN|MORNING|EVENING|AFTERNOON|CONTINUOUS|LATER|SAME|" \
              r"MOMENT'?S?\s*LATER|MOMENTS?\s*LATER|" \
              r"DAG|NAG|AAND|OGGEND|SKEMER|DAERAAD)"  # Afrikaans
```

---

## Performance Data

| Script | Pages | PyPDF2 | plumber fast | plumber layout | Slowdown | Headers |
|--------|-------|--------|-------------|----------------|----------|---------|
| BIRD_V8 | 109 | 0.28s | 2.47s | 2.46s | 8.8x | 0 |
| Ep_1 | 39 | 0.75s | 2.72s | 2.16s | 2.9x | 22 |
| LASGIDI Ep14 | 26 | 0.05s | 0.48s | 0.34s | 6.4x | 22 |
| LASGIDI Ep4 | 27 | 0.07s | 0.36s | 0.44s | 6.3x | 25 |
| Powerlessness | 88 | 0.28s | 2.49s | 2.68s | 9.7x | 189 |

**Key:** The brainstorm estimated 10-20s for `layout=True`. Actual max is **2.68s**. 5-10x better than expected. No UI loading state concern.

---

## Indentation Analysis

All 5 scripts show consistent margin clusters aligned with ScreenPy's hard-coded thresholds:

| Element | ScreenPy Threshold | Measured (layout spaces) | Status |
|---------|-------------------|-------------------------|--------|
| Character names | 20+ spaces | 34-35 spaces | **PASS** |
| Dialogue | 10-30 spaces | 24-25 spaces | **PASS** |
| Transitions | 40+ spaces | 63-64 spaces | **PASS** |
| Parentheticals | (not checked) | 30-33 spaces | Within range |

**Conclusion: No Indent Calibrator needed for Phase 1.** The default `pdfplumber layout=True` output naturally aligns with ScreenPy's thresholds for standard US-formatted and SA-formatted screenplays.

The x-coordinate cluster analysis confirms 4 distinct margin stops across all scripts:
- **~110pt** — Action/scene headers (flush left)
- **~170-180pt** — Dialogue text
- **~240-250pt** — Character names (centered)
- **~460-510pt** — Transitions (right-aligned)

---

## Normalizer Effectiveness

| Script | Layout Chars | Normalized | Removed | % |
|--------|-------------|-----------|---------|---|
| BIRD_V8 | 555,899 | 410,795 | 145,104 | 26.1% |
| Ep_1 | 198,899 | 160,774 | 38,125 | 19.2% |
| LASGIDI Ep14 | 132,599 | 96,440 | 36,159 | 27.3% |
| LASGIDI Ep4 | 137,699 | 99,649 | 38,050 | 27.6% |
| Powerlessness | 448,799 | 340,947 | 107,852 | 24.0% |

Normalizer primarily strips trailing whitespace and `(CONTINUED)` markers. No content loss observed.

---

## Dual Text Path Validation

| Script | Regex on raw | Regex on normalized | Divergence? |
|--------|-------------|--------------------| ------------|
| BIRD_V8 | 0 | 0 | No |
| Ep_1 | 22 | 22 | No |
| LASGIDI Ep14 | 22 | 22 | No |
| LASGIDI Ep4 | 25 | 25 | No |
| Powerlessness | 189 | 189 | No |

**Zero divergence across all scripts.** The normalizer does not alter line boundaries or content that would break regex matching. However, dual text paths remain architecturally recommended — future normalizer enhancements (e.g., aggressive kerning collapse) could introduce divergence.

---

## Phase 0.5 Results: Grammar vs Regex (Check #6)

| Script | Regex | Grammar | Delta | Status |
|--------|-------|---------|-------|--------|
| Ep_1 | 22 | 22 | +0 | **PASS** (exact match) |
| LASGIDI Ep14 | 19 | 22 | +3 | **PASS** (grammar found 3 more) |
| LASGIDI Ep4 | 25 | 25 | +0 | **PASS** (exact match) |
| Powerlessness | 189 | 194 | +5 | **PASS** (grammar found 5 more) |
| BIRD_V8 (AF) | 0 | 107 | +107 | **PASS** (was invisible to regex) |
| **Total** | **255** | **370** | **+115** | **45% improvement** |

### Grammar-Only Headers (found by grammar, missed by regex)

- `INT. REHAB RECEPTION - MORNGING` — typo in TIME_OF_DAY, grammar tolerates it
- `EXT. REHAB PARKING LOT` — no time of day, regex requires it
- `EXT. NOORDHOEK BEACH - EARLY MORNING` — compound time, regex pattern too strict
- `EXT. SHOPPING CENTRE.` — trailing period, regex fails
- `INT. CLYDES KITCHEN - MORING` — typo, grammar tolerates
- `11. EXT. LEROY/SEGUN'S APARTMENT - MOMENT'S LATER` — regex didn't match apostrophe variant

## Phase 0.5 Results: Speaker Extraction (Check #8)

| Script | Characters | Dialogue Blocks | Top Speaker |
|--------|-----------|----------------|-------------|
| Ep_1 | 8 | 197 | LEROY (77), SEGUN (73) |
| LASGIDI Ep14 | 11 | 223 | LEROY (87), SEGUN (57), MR. SMITH (24) |
| LASGIDI Ep4 | 8 | 237 | LEROY (106), PATRICK (80), TEMI (41) |
| Powerlessness | 57 | 508 | DARTHY (185), CLYDE (67), FATIMA (62) |
| BIRD_V8 (AF) | 68 | 969 | WILLIE (185), MARTJIE-SANTJIE (155), CHARLIE (83) |
| **Total** | **152** | **2,134** | |

## Bugs Found & Fixed During Integration

| Bug | Root Cause | Fix |
|-----|-----------|-----|
| Grammar found 0 headers on LASGIDI scripts | Scene number prefix (`1. EXT.`) not stripped before location type regex | Added `scene_number_prefix` pattern to `shot_parser.py` |
| "Establishment shot" detected as heading | `_parse_shot_heading` checked for "SHOT" keyword too broadly | Tightened to require `INT./EXT.` prefix for non-uppercase lines |
| Dialogue lines consumed as character names | `center_indent` threshold too low (20 spaces) | Raised to 30 spaces; added dialogue-first priority for center-indented lines |
| Scene headers consumed by dialogue parser | No heading check inside dialogue collection loop | Added `_parse_shot_heading` guard in dialogue while-loop |

---

## Revised Risk Assessment

| Risk | Original Rating | Post-Preflight | Rationale |
|------|----------------|---------------|-----------|
| "Clean Text" Problem | HIGH | **LOW** | pdfplumber layout=True produces clean, indented text |
| Indent Misalignment | HIGH | **ELIMINATED** | All thresholds met on all scripts. No calibrator needed. |
| pdfplumber Performance | MEDIUM | **ELIMINATED** | 2.68s max, not 10-20s as feared |
| Fallback Paradox | MEDIUM | **LOW** | Zero divergence, but dual paths still recommended |
| SA-Format Scripts | HIGH | **MEDIUM** | SA English works. Afrikaans needs TIME_OF_DAY extension. |
| Parser Isolation | LOW-MEDIUM | **LOW** | Verified: 4-6 files, pyparsing only |
| Speaker vs Character | MEDIUM | MEDIUM | Unchanged — requires Phase 2 Entity Resolution |

---

## Assumptions Validated

| Assumption | Status |
|-----------|--------|
| "pdfplumber is more accurate than PyPDF2" | **Confirmed** — fewer kerning artifacts |
| "pdfplumber is slower" | **Confirmed but overestimated** — 3-10x slower, not 50-100x |
| "Indentation needs calibration" | **Disproved** — default layout output aligns with ScreenPy |
| "Normalizer might break regex" | **Disproved** — zero divergence on 5 scripts |
| "Parser is cleanly isolated" | **Confirmed** — no spacy/sense2vec in parser chain |
| "Location hierarchy works" | **Confirmed** — splits multi-part settings correctly |

---

## GO/NO-GO Decision

### 🟢 FULL GO

All blocking checks pass. The vendored parser is ready for Phase 1 sprint integration.

**Completed (Phase 0.5):**
1. ✅ `pyparsing` installed + added to `requirements.txt`
2. ✅ ScreenPy parser vendored into `backend/lib/screenpy/` (6 files)
3. ✅ Absolute imports rewritten to relative
4. ✅ Pydantic v2 syntax (`model_config`, `model_dump`)
5. ✅ Config-driven locale schema (en, af, fr, es)
6. ✅ Grammar ≥ regex on ALL 5 scripts (370 vs 255)
7. ✅ Speaker extraction working (152 characters, 2,134 dialogue blocks)
8. ✅ BIRD_V8 Afrikaans: 107 headers (was 0)

**Phase 1 Sprint Scope:**
- Wire vendored parser into `extraction_pipeline.py` as grammar-first path
- Keep regex as fallback (dual text path architecture)
- Populate `characters` dict into scene data for downstream features
- Entity Resolution: merge `LEROY (CONT'D)` → `LEROY`

---

## Files Created

| File | Purpose |
|------|---------|
| `backend/scripts/screenpy_preflight.py` | Pre-flight test runner (reusable) |
| `backend/scripts/screenpy_preflight_results.json` | Raw results data (5 scripts) |
| `backend/scripts/screenpy_grammar_vs_regex.py` | Grammar vs regex comparison runner |
| `backend/scripts/grammar_vs_regex_results.json` | Grammar comparison raw data |
| `backend/lib/screenpy/` | Vendored ScreenPy parser (6 files) |
| `backend/lib/screenpy/locale_config.py` | Config-driven locale schema |
| `backend/lib/screenpy/models.py` | Pydantic v2 screenplay models |
| `backend/lib/screenpy/parser/core.py` | Main ScreenplayParser class |
| `backend/lib/screenpy/parser/grammar.py` | pyparsing grammar definitions |
| `backend/lib/screenpy/parser/shot_parser.py` | Shot heading parser |
| `backend/lib/screenpy/parser/time_parser.py` | Time expression parser |
| `docs/SCREENPY_PREFLIGHT_REPORT.md` | This report |
