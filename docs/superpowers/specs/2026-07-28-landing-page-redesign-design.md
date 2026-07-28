# SlateOne Landing Page Redesign — Design Doc

**Date:** 2026-07-28
**Audience:** UI/design team implementing the redesign
**Repo affected:** `~/slateone` (marketing site, Vite + React 19 + TypeScript, deployed to Vercel as slateone.studio) — **not** this repo. This doc lives here because it's the current working session's spec location; hand a copy to whoever owns `~/slateone`.

## Why

The marketing site and the actual product (`app.slateone.studio`) currently look like two different companies. The landing site uses a charcoal/black background with neon-green (`#E3FF00`) and cyan accents, Space Grotesk display type, and Courier Prime mono — a sharp "enterprise infrastructure" identity. The app itself uses a dark slate background with warm amber accents, Inter throughout, and a softer, more cinematic feel (see `frontend/src/index.css` in this repo). A visitor who converts on the landing page and logs into the app currently gets visual whiplash. This redesign aligns the two.

## Scope

Full visual system swap (color, type, shape, elevation) to match the app, plus a copy/tone pass so the "Operating System for Modern Film Production" infrastructure-speak matches the warmer, concrete voice already established in `docs/landing-faq.md` and the app's own UI. Section structure is kept mostly intact — this is not an IA rebuild. See "Out of scope" below.

## 1. Visual System

Adopt the app's design tokens directly — ideally by literally referencing `frontend/src/index.css` as source of truth, so both codebases can eventually share a token file.

### Color

| Role | Current (landing) | New |
|---|---|---|
| Page background | `charcoal` / `black` | `--gray-900` (`#0f172a`); use `--gray-950` (`#020617`) for the deepest/most recessed sections (e.g. Pricing background) |
| Card/surface background | `white/[0.02]`–`white/[0.08]` opacity stacks | `--bg-card` (`--gray-800`, `#1e293b`), solid — no opacity-stack pattern |
| Card border | `white/[0.06]`–`white/[0.1]` | `--border-color` (`--gray-700`) |
| Accent (replaces neon `#E3FF00`) | neon green | `--primary-500` (`#f59e0b`) amber; hover state `--primary-400` (`#fbbf24`) |
| Body text | `white/40`, `white/50`, `white/70` opacities | `--text-primary` (headings/emphasis), `--text-secondary` (body), `--text-muted` (fine print) |
| Status/badge tints | neon-tinted boxes | `--primary-alpha-05` through `--primary-alpha-40` for badge backgrounds, matching how the app tints status chips |
| Hero demo panel accent codes | `border-cyan`, `border-pink-500`, `border-purple-400` (arbitrary) | The app's real scene-type colors: `--timeline-dream` (blue), `--timeline-fantasy` (pink), `--timeline-flashback` (purple), plus `--primary-500` for the primary/highlighted card |

Drop `cyan` and `neon` from the Tailwind theme config in `index.html` entirely once the migration is complete — don't leave them defined-but-unused.

### Typography

- Drop **Space Grotesk** (`font-display`) and **Courier Prime** (`font-mono`).
- Standardize on **Inter** (`--font-sans`) for all headlines and body text — including what were previously `font-display` headlines.
- Keep exactly one monospace moment: technical/screenplay-flavored labels (scene sluglines, timecodes, price units like "`/ breakdown`") use `--font-mono` (`'SF Mono', 'Monaco', 'Consolas', monospace`), matching how the app itself uses mono for scene/timecode data — not Courier Prime.
- Drop uppercase-with-heavy-letter-spacing button/badge labels (e.g. `tracking-wide uppercase` on CTAs) — the app doesn't use that treatment anywhere.

### Shape & Elevation

- Buttons/inputs: `--radius-lg` (8px), matching `.btn-primary`/`.btn-secondary`.
- Cards: `--radius-xl` (12px) or `--radius-2xl` (16px), matching card components in the app.
- Shadows: use `--shadow-sm` / `--shadow-md` / `--shadow-lg` instead of the neon glow shadows (`shadow-[0_0_40px_-10px_rgba(227,255,0,0.15)]` and similar).

### Motion

Keep the Hero's animated script → breakdown demo panel — it's the site's strongest asset and it's product-accurate. Only its accent colors change (see color table above); the animation timing/mechanics stay as-is.

## 2. Components & Primitives

Treat `frontend/src/components/ui/` in this repo (Button, Badge, Modal, Skeleton, LoaderOverlay) as the source of truth for how interactive elements should look, rather than inventing new Tailwind utility combinations in the landing repo.

- **Buttons** — replace bespoke `bg-neon text-black font-bold uppercase` primary CTAs and bordered-link secondary CTAs with the visual spec of `.btn-primary` / `.btn-secondary` / `.btn-tertiary` (`frontend/src/index.css` lines ~212–237, or `Button.jsx`/`Button.css` if porting the component itself). No uppercase/letter-spacing on labels.
- **Badges** ("Solo"/"Crew" tier labels, "Recommended" flag, "Built For" role chips) — match `Badge.jsx`'s pill shape and `--primary-alpha-*` tinted backgrounds instead of the current mono-uppercase-in-a-box style.
- **Cards** (pricing tiers, hero breakdown-demo cards, "Built For" chips) — solid `--bg-card` on `--bg-app`, `--border-color` borders, `--radius-xl`. Drop the `bg-white/[0.02]`-style opacity-stacking and neon glow shadows.
- **Modal** (`TierSelectionModal`) — restyle to match `Modal.jsx`'s structure and spacing, so the moment a visitor clicks "Get Started" the modal already looks like the app they're about to sign into.
- **Icons** — keep `lucide-react` (already shared with the app), recolor from white-opacity/neon to `--text-secondary` / `--primary-500`.
- **New: nav bar variant** — same `--header-height` and card/border treatment as the app's own header, so the jump from marketing nav → app header at login is seamless.

### Accessibility note

While retokenizing, verify contrast: several current text treatments (`text-white/30`, `text-white/40` on black) sit near or below WCAG AA. Confirm `--text-secondary`/`--text-muted` against the new `--gray-900`/`--gray-950` backgrounds meet AA before shipping — same bar the app's own UI should already be held to.

## 3. Information Architecture & Copy

Section order stays mostly the same, collapsed from 7 to 6:

**Hero → IndustryReality → OperatingLayer (merged with SystemArchitecture) → BuiltFor → Pricing → Footer**

`SystemArchitecture` (the abstract "Script → Structured Data → Reports/Kanban/Scheduling" flow diagram) merges into `OperatingLayer`: once OperatingLayer names real product surfaces concretely, a second abstract system-flow diagram is redundant.

Tone shifts from "infrastructure/operating system" abstraction toward the concrete, human voice already established in `docs/landing-faq.md` ("a first AD's prep pass, done in the background in minutes instead of days") and the app's own UI copy.

| Section | Change |
|---|---|
| Hero | New headline/subhead/primary CTA (exact copy below). Keep animated demo panel, secondary CTA ("Book a Production Demo") unchanged. |
| IndustryReality | Keep the pain-point content, drop the numbered-spec-sheet presentation (`#01`, `#02`...) in favor of a more human framing — things a producer has actually said, not a systems audit table. |
| OperatingLayer (merged) | Reframe the "Four Core Capabilities" as concrete product features (breakdown, stripboard, reports, collaboration) tied to what the app actually does, absorbing SystemArchitecture's flow diagram content where it adds value. |
| BuiltFor | Keep as-is; restyle only. |
| Pricing | Content unchanged — already written in the target voice. Restyle only. |
| Footer | Unchanged; restyle only. |

### Exact copy: Hero

- Headline: **"Upload your script.\nGet a full breakdown in minutes."**
- Subheadline: *"SlateOne reads your screenplay scene by scene and pulls out everything a production needs to track — cast, props, wardrobe, locations, and more. What used to take days with a highlighter now runs in the background while you keep working."*
- Primary CTA: **"Start Your Breakdown"** (replaces "View Pricing")
- Secondary CTA: **"Book a Production Demo"** (unchanged)

### Exact copy: Pricing

Unchanged — already in the target voice, carried forward verbatim rather than rewritten for its own sake:

- Section headline: **"Simple Pricing. Built For How You Work."**
- Subhead: *"Pay per breakdown when you need it, or license your whole team for the year. Uploading and editing scripts is always free — you only pay when you run a breakdown."*
- Mid-section line: **"Work solo. Or bring the whole crew."**
- Tier taglines, feature lists, and the "Built For" closer (*"If your production runs on spreadsheets and fragmented tools, SlateOne replaces that system."*) — unchanged.

## 4. Responsive

No structural layout changes. Existing Tailwind breakpoints (`sm`/`lg`) and existing grid-collapse behavior (Pricing tiers, BuiltFor chips → single column on mobile) carry forward as-is; only the tokens applied within that layout change.

## 5. Out of Scope

- **IA rebuild.** Replacing the abstract sections with concrete product-flow sections (Upload → Breakdown → Schedule → Collaborate → Reports) driven by real product screenshots was considered (Approach C) but deferred — it's a separate project needing product screenshots and further stakeholder input on positioning, not a UI reskin.
- **Pricing content changes.** The pricing copy and tier structure are current and correct (two-tier ZAR PayFast model, per `docs/SPEC_Tiered_Business_Model.md` in this repo) — no changes beyond visual restyle.
- **Legal pages** (`PrivacyPolicy`, `TermsOfService`) — restyle to match tokens when convenient, but no content review as part of this doc.
- **Copy for IndustryReality/OperatingLayer sections** — direction given above, but exact new sentence-level copy for these two sections was not drafted in this pass (unlike Hero/Pricing) and should get a short copy pass before implementation.

## 6. Handoff

1. **Token table** (Section 1 above) is a near-mechanical find-and-replace: old Tailwind class/arbitrary value → new CSS variable.
2. **Live reference** — no mockups were built for this pass. Use the running app at app.slateone.studio and `frontend/src/index.css` in this repo as the literal reference implementation for exact values.
3. **Merged IA outline** (Section 3) with section-by-section tone direction.
4. **Explicit non-changes** (Section 5) so the UI team doesn't second-guess scope mid-build: Pricing copy, Footer, overall page structure/routing via the `AppState` enum in `~/slateone/App.tsx` all stay as they are.
