# Landing Page Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reskin the `~/slateone` marketing site (slateone.studio) from its charcoal/neon-green/Space-Grotesk identity to the same slate/amber/Inter visual system as the actual product app, and rewrite Hero copy plus tone-adjust two sections, per `docs/superpowers/specs/2026-07-28-landing-page-redesign-design.md`.

**Architecture:** No structural/routing changes. Every section component in `~/slateone/components/` gets its Tailwind classes swapped from the custom `charcoal`/`neon`/`cyan` theme to Tailwind's **built-in** `slate` and `amber` palettes — chosen because Tailwind's default `slate-900` (`#0f172a`), `slate-800` (`#1e293b`), `slate-700` (`#334155`), `slate-950` (`#020617`), `amber-500` (`#f59e0b`), `amber-400` (`#fbbf24`), and `amber-600` (`#d97706`) are **exact hex matches** for the app's `--gray-900`/`--gray-800`/`--gray-700`/`--gray-950`/`--primary-500`/`--primary-400`/`--primary-600` CSS variables (`ScripDown_AI/frontend/src/index.css`). This means no custom Tailwind config colors are needed at all — just delete the custom theme extension and use stock utility classes. `SystemArchitecture.tsx` is deleted and its one useful line folds into `OperatingLayer.tsx`.

**Tech Stack:** Vite + React 19 + TypeScript, Tailwind via CDN `<script>` (no build-step config file — theme lives in `index.html`), `lucide-react` icons. No test runner or linter configured in this repo — verification is `npm run build` (TypeScript/Vite compile check) plus a visual check via `npm run dev`.

## Global Constraints

- Repo root for all file paths below: `/Users/thecasterymedia/slateone` (a separate repo from `ScripDown_AI` — do not confuse paths).
- Color substitution is mechanical and must be exact — do not introduce new arbitrary hex values; use only stock Tailwind `slate-*` / `amber-*` utilities so the palette stays a literal match to `ScripDown_AI/frontend/src/index.css`.
- Drop `font-display` (Space Grotesk) and the Courier Prime import entirely — every heading uses the default `font-sans` (Inter) stack; `font-mono` keeps working via Tailwind's built-in monospace stack once Courier Prime is removed.
- No uppercase/letter-spaced button or badge labels (remove `uppercase`, `tracking-wide`, `tracking-widest`, `tracking-[0.2em]` from interactive labels) — the app doesn't use that treatment.
- Replace opacity-stacked surfaces (`bg-white/[0.02]`, `bg-white/[0.03]`, `bg-white/[0.06]`) with solid `bg-slate-800` / `bg-slate-700` — no translucent card backgrounds.
- No neon glow box-shadows (`shadow-[0_0_...rgba(227,255,0,...)]`) — use stock `shadow-lg` / `shadow-2xl`.
- Pricing copy (headlines, tier names, feature lists, taglines) does not change — token/class swap only.
- After each task, run `npm run build` in `~/slateone` and confirm it exits 0 before committing.

---

### Task 1: Tailwind theme & global HTML cleanup

**Files:**
- Modify: `/Users/thecasterymedia/slateone/index.html`

**Interfaces:**
- Produces: the color/font vocabulary every later task's class names assume (`slate-900/950/800/700/600/500/400/300`, `amber-500/400/600`, no `charcoal`/`neon`/`cyan`/`font-display`/`font-mono`-via-Courier-Prime).

- [ ] **Step 1: Replace the Tailwind config script**

Replace the `tailwind.config = {...}` block (currently lines 29–43) with:

```html
    <script>
      tailwind.config = {
        theme: {
          extend: {
            fontFamily: {
              sans: ['Inter', 'sans-serif'],
            }
          }
        }
      }
    </script>
```

This removes the `charcoal`, `slate-black`, `neon`, `cyan`, `paper`, `soft-grey` custom colors and the `display`/`mono` custom font families entirely. `slate-*` and `amber-*` are already built into Tailwind by default — no extension needed. `font-mono` falls back to Tailwind's default monospace stack (`ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace`), which is close enough to the app's `--font-mono` that no override is needed.

- [ ] **Step 2: Trim the Google Fonts import**

Replace the fonts `<link>` (currently line 27) with:

```html
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap" rel="stylesheet">
```

- [ ] **Step 3: Update the custom `<style>` block**

Replace the `<style>` block (currently lines 45–62) with:

```html
    <style>
      /* Custom scrollbar for dark theme */
      ::-webkit-scrollbar {
        width: 8px;
      }
      ::-webkit-scrollbar-track {
        background: #0f172a;
      }
      ::-webkit-scrollbar-thumb {
        background: #475569;
        border-radius: 4px;
      }
      ::-webkit-scrollbar-thumb:hover {
        background: #64748b;
      }
    </style>
```

This drops the `.neon-glow` text-shadow utility (no longer used once neon is gone) and matches scrollbar colors to `slate-900`/`slate-600`/`slate-500`.

- [ ] **Step 4: Update the body tag and meta copy**

Replace:
```html
  <body class="bg-charcoal text-paper antialiased overflow-x-hidden">
```
with:
```html
  <body class="bg-slate-900 text-slate-50 antialiased overflow-x-hidden">
```

Replace the `<title>` and the three "Operating System" meta descriptions (lines 6, 12, 15, 19, 20) with copy consistent with the new Hero headline. Specifically:

```html
    <title>SlateOne | AI Script Breakdown for Film & TV Production</title>
    <meta name="description" content="Upload your script and get a full production breakdown in minutes. SlateOne extracts cast, props, wardrobe, and locations automatically, then helps you schedule and share it with your team." />
```
```html
    <meta property="og:title" content="SlateOne | Upload your script. Get a full breakdown in minutes." />
    <meta property="og:description" content="SlateOne reads your screenplay scene by scene and extracts everything a production needs to track — cast, props, wardrobe, locations, and more." />
```
```html
    <meta name="twitter:title" content="SlateOne | Upload your script. Get a full breakdown in minutes." />
    <meta name="twitter:description" content="SlateOne reads your screenplay scene by scene and extracts everything a production needs to track — cast, props, wardrobe, locations, and more." />
```

- [ ] **Step 5: Verify build**

Run: `cd /Users/thecasterymedia/slateone && npm run build`
Expected: exits 0. (React components still reference `charcoal`/`neon`/`font-display` classes at this point — that's expected and fixed in later tasks. Tailwind's CDN script doesn't fail the Vite build for unknown utility classes, so this build check here just confirms `index.html` itself is well-formed; full visual verification happens once all components are converted, in Task 9.)

- [ ] **Step 6: Commit**

```bash
cd /Users/thecasterymedia/slateone
git add index.html
git commit -m "style: swap Tailwind theme to stock slate/amber, drop neon/display fonts"
```

---

### Task 2: Nav bar (`App.tsx`)

**Files:**
- Modify: `/Users/thecasterymedia/slateone/App.tsx`

**Interfaces:**
- Consumes: Tailwind vocabulary from Task 1.

- [ ] **Step 1: Replace the nav and legal footer bar markup**

Replace lines 37–109 (the full `return (...)` block) with:

```tsx
  return (
    <div className="min-h-screen flex flex-col font-sans selection:bg-amber-500 selection:text-slate-900">
      {/* Navigation */}
      <nav className="fixed top-0 w-full z-50 bg-slate-900/90 backdrop-blur-md border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div
              className="flex items-center cursor-pointer group"
              onClick={handleLogoClick}
            >
              <Film className="h-5 w-5 text-amber-500 mr-2" />
              <span className="font-bold text-xl tracking-tight text-slate-50">
                Slate<span className="text-amber-500">One</span>
              </span>
            </div>
            <div className="flex items-center gap-4">
              <a
                href="#pricing"
                onClick={(e) => { e.preventDefault(); document.getElementById('pricing')?.scrollIntoView({ behavior: 'smooth' }); }}
                className="hidden sm:inline-block text-sm text-slate-400 hover:text-amber-500 transition-colors cursor-pointer"
              >
                Pricing
              </a>
              <a
                href="https://app.slateone.studio/login?mode=login"
                className="text-sm font-medium bg-slate-800 border border-slate-700 px-4 py-2 rounded-lg text-slate-300 hover:text-amber-500 hover:border-amber-500/50 transition-all"
              >
                Login
              </a>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="flex-grow pt-16">
        {appState === AppState.LANDING ? (
          <>
            <Hero />
            <IndustryReality />
            <OperatingLayer />
            <BuiltFor />
            <Pricing />
            <Footer />
          </>
        ) : appState === AppState.PRIVACY_POLICY ? (
          <PrivacyPolicy onBack={handleBackToHome} />
        ) : appState === AppState.TERMS_OF_SERVICE ? (
          <TermsOfService onBack={handleBackToHome} />
        ) : null}
      </main>

      {/* Legal footer bar */}
      <div className="bg-slate-950 text-slate-600 text-xs py-4 text-center border-t border-slate-800">
        <p>&copy; {new Date().getFullYear()} SlateOne. Production Infrastructure for Film & TV.</p>
        <div className="mt-2 space-x-4">
          <button
            onClick={handlePrivacyPolicyClick}
            className="hover:text-slate-300 transition-colors"
          >
            Privacy Policy
          </button>
          <button
            onClick={handleTermsOfServiceClick}
            className="hover:text-slate-300 transition-colors"
          >
            Terms of Service
          </button>
        </div>
      </div>
    </div>
  );
};

export default App;
```

Note this also removes the `<SystemArchitecture />` render (component is deleted in Task 5) and its now-dangling import.

- [ ] **Step 2: Remove the now-unused `SystemArchitecture` import**

Delete this line from the top of the file:
```tsx
import { SystemArchitecture } from './components/SystemArchitecture';
```

- [ ] **Step 3: Verify build**

Run: `cd /Users/thecasterymedia/slateone && npm run build`
Expected: exits 0.

- [ ] **Step 4: Commit**

```bash
cd /Users/thecasterymedia/slateone
git add App.tsx
git commit -m "style: reskin nav and legal footer, drop SystemArchitecture render"
```

---

### Task 3: Hero (`Hero.tsx`) — copy + reskin

**Files:**
- Modify: `/Users/thecasterymedia/slateone/components/Hero.tsx`

- [ ] **Step 1: Replace the headline, subheadline, and CTAs**

Replace lines 23–56 (the "Left: Copy" block) with:

```tsx
          <div className="z-10">

            {/* Headline */}
            <h1 className="text-5xl sm:text-6xl lg:text-[5.5rem] font-bold leading-[0.95] tracking-tight text-slate-50 mb-8">
              Upload your script.<br/>
              Get a full breakdown<br/>
              <span className="text-amber-500">in minutes.</span>
            </h1>

            {/* Subheadline */}
            <p className="text-xl md:text-2xl text-slate-400 max-w-2xl leading-relaxed mb-12 font-light">
              SlateOne reads your screenplay scene by scene and pulls out everything a production needs to track — cast, props, wardrobe, locations, and more. What used to take days with a highlighter now runs in the background while you keep working.
            </p>

            {/* CTAs */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
              <a
                href="#pricing"
                onClick={scrollToPricing}
                className="bg-amber-500 text-slate-900 font-bold px-8 py-4 rounded-lg hover:bg-amber-400 transition-all duration-300 flex items-center gap-3 text-sm"
              >
                Start Your Breakdown
                <ArrowRight className="w-4 h-4" />
              </a>
              <a
                href="mailto:hello@slateone.studio?subject=Production Demo Request"
                target="_blank"
                rel="noopener noreferrer"
                className="text-slate-400 hover:text-amber-500 border border-slate-700 hover:border-amber-500/30 px-8 py-4 rounded-lg transition-all duration-300 text-sm font-medium"
              >
                Book a Production Demo
              </a>
            </div>
          </div>
```

- [ ] **Step 2: Reskin the animated demo panel**

Replace lines 12–17 (section wrapper + background glow) with:

```tsx
    <section id="hero-cta" className="relative overflow-hidden min-h-[100vh] flex items-end lg:items-center border-b border-slate-800">
      {/* Subtle grid background */}
      <div className="absolute inset-0 opacity-[0.03] bg-[linear-gradient(rgba(255,255,255,0.1)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.1)_1px,transparent_1px)] [background-size:60px_60px]" />
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden -z-10">
        <div className="absolute -top-[30%] -left-[15%] w-[50%] h-[50%] rounded-full bg-amber-500/[0.03] blur-[150px]" />
      </div>
```

Replace lines 58–116 (the "Right: Script-to-Breakdown Animation" block) with:

```tsx
          {/* Right: Script-to-Breakdown Animation */}
          <div className="relative h-[400px] sm:h-[500px] w-full bg-slate-950/60 border border-slate-700 rounded-xl overflow-hidden shadow-2xl backdrop-blur-sm hidden lg:block">
            <div className="absolute top-0 w-full h-8 bg-slate-950 flex items-center px-4 gap-2 border-b border-slate-800 z-20">
              <div className="w-2.5 h-2.5 rounded-full bg-slate-700"></div>
              <div className="w-2.5 h-2.5 rounded-full bg-slate-700"></div>
              <div className="w-2.5 h-2.5 rounded-full bg-slate-700"></div>
              <span className="ml-3 text-[10px] font-mono text-slate-600 tracking-wider uppercase">SlateOne — Breakdown Engine</span>
            </div>

            <div className="flex h-full pt-8">
              {/* Script Side */}
              <div className="w-1/2 border-r border-slate-800 p-5 overflow-hidden relative">
                <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-slate-950/80 z-10 pointer-events-none"></div>
                <div className="animate-[heroScroll_12s_linear_infinite] font-mono text-[11px] text-slate-400 space-y-5 leading-relaxed">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <div key={i} className="space-y-3">
                      <p className="text-slate-300 font-bold tracking-wide">EXT. MABONENG PRECINCT — DAY</p>
                      <p>A RED TAXI swerves through traffic.</p>
                      <br/>
                      <p className="text-slate-300 font-bold tracking-wide">INT. JOHANNESBURG APARTMENT — DAY</p>
                      <p>THABO (30s) sits at a cluttered desk.</p>
                      <p className="pl-8 text-slate-500">THABO</p>
                      <p className="pl-6 text-slate-500">I can't believe I have to type<br/>this all out again.</p>
                      <p>He takes a sip of COFFEE.</p>
                      <br/>
                      <p className="text-slate-300 font-bold tracking-wide">INT. JOHANNESBURG APARTMENT — DAY</p>
                      <p>THABO (30s) sits at a cluttered desk.</p>
                      <p className="pl-8 text-slate-500">THABO</p>
                      <p className="pl-6 text-slate-500">I can't believe I have to type<br/>this all out again.</p>
                      <p>He takes a sip of COFFEE.</p>
                      <br/>
                      <p className="text-slate-300 font-bold tracking-wide">EXT. MABONENG PRECINCT — DAY</p>
                      <p>A RED TAXI swerves through traffic.</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Breakdown Side */}
              <div className="w-1/2 p-4 bg-slate-950 relative">
                <div className="space-y-3 pt-1">
                  <BreakdownCard delay="0s" title="1. INT. JHB APARTMENT" meta="D1 • 1/8 PGS • CAST: THABO" color="border-amber-500" />
                  <BreakdownCard delay="1.2s" title="2. EXT. MABONENG" meta="D1 • 4/8 PGS • CAST: TAXI DRIVER" color="border-blue-500" />
                  <BreakdownCard delay="2.4s" title="3. INT. HOSPITAL" meta="N1 • 2/8 PGS • CAST: DOCTOR" color="border-pink-500" />
                  <BreakdownCard delay="3.6s" title="4. EXT. ROOFTOP" meta="N1 • 6/8 PGS • CAST: THABO, SARAH" color="border-purple-500" />
                </div>

                {/* Processing overlay */}
                <div className="absolute inset-0 flex items-center justify-center bg-slate-950/70 backdrop-blur-[2px] animate-[heroFade_5s_forwards] pointer-events-none">
                  <div className="flex flex-col items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center animate-pulse">
                      <span className="text-amber-500 text-sm font-bold">S1</span>
                    </div>
                    <span className="font-mono text-[10px] text-amber-500/80 tracking-[0.2em] uppercase">Processing Script</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>
```

Note `border-blue-500`/`border-pink-500`/`border-purple-500` on the breakdown cards approximate the app's `--timeline-dream`/`--timeline-fantasy`/`--timeline-flashback` hues (`#3b82f6`, `#ec4899`, `#a855f7`) — Tailwind's stock `blue-500`/`pink-500`/`purple-500` are the closest built-in matches and avoid introducing arbitrary hex values.

The `BreakdownCard` component at the bottom of the file (lines 140–148) needs no changes — it already takes `color` as a prop and its own classes (`bg-[#111]`) should become `bg-slate-800`:

- [ ] **Step 3: Reskin the `BreakdownCard` helper**

Replace lines 140–148 with:

```tsx
const BreakdownCard = ({ delay, title, meta, color }: { delay: string; title: string; meta: string; color: string }) => (
  <div
    className={`bg-slate-800 p-3.5 rounded-lg border-l-[3px] ${color} opacity-0`}
    style={{ animation: `heroSlideIn 0.5s ease-out forwards ${delay}` }}
  >
    <div className="font-bold text-slate-300 text-xs mb-1 tracking-wide">{title}</div>
    <div className="text-[10px] text-slate-500 font-mono tracking-wider">{meta}</div>
  </div>
);
```

- [ ] **Step 4: Verify build**

Run: `cd /Users/thecasterymedia/slateone && npm run build`
Expected: exits 0.

- [ ] **Step 5: Commit**

```bash
cd /Users/thecasterymedia/slateone
git add components/Hero.tsx
git commit -m "feat: rewrite hero copy and reskin to slate/amber palette"
```

---

### Task 4: IndustryReality (`IndustryReality.tsx`) — de-numbered pain points + reskin

**Files:**
- Modify: `/Users/thecasterymedia/slateone/components/IndustryReality.tsx`

- [ ] **Step 1: Replace the full component**

Replace the entire file with:

```tsx
import React from 'react';

const painPoints = [
  { label: 'Manual script breakdowns', detail: 'Line-by-line, page-by-page data entry' },
  { label: 'Static PDF reports', detail: 'Outdated the moment a revision drops' },
  { label: 'Excel-based scheduling', detail: 'Disconnected from breakdown data' },
  { label: 'Fragmented crew communication', detail: 'WhatsApp threads, email chains, lost context' },
  { label: 'No central production data layer', detail: 'Every department operates in isolation' },
];

export const IndustryReality: React.FC = () => {
  return (
    <section className="py-32 bg-slate-950 border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

        <div className="grid lg:grid-cols-2 gap-16 items-start">

          {/* Left: Statement */}
          <div>
            <h2 className="text-4xl md:text-5xl font-bold text-slate-50 mb-8 leading-[1.1]">
              The Way Productions<br/>Still Operate
            </h2>
            <p className="text-lg text-slate-400 leading-relaxed max-w-lg">
              Most productions still rely on disconnected systems — spreadsheets for breakdown,
              PDFs for reports, chat apps for coordination. The result is friction at every stage
              of production.
            </p>

            {/* Consequence block */}
            <div className="mt-10 border-l-2 border-slate-700 pl-6">
              <p className="text-sm text-slate-500 uppercase tracking-widest font-mono mb-3">The Cost</p>
              <div className="flex flex-wrap gap-3">
                {['Administrative drag', 'Data duplication', 'Version confusion', 'Lost time', 'Operational risk'].map((item) => (
                  <span key={item} className="text-xs text-slate-400 bg-slate-800 border border-slate-700 px-3 py-1.5 rounded font-mono">
                    {item}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Right: Pain points */}
          <div className="space-y-0">
            {painPoints.map((point, i) => (
              <div key={i} className="group border-b border-slate-800 py-6 first:pt-0 last:border-b-0">
                <div className="flex items-start gap-4">
                  <span className="w-2 h-2 rounded-full bg-amber-500/40 mt-2 flex-shrink-0 group-hover:bg-amber-500 transition-colors" />
                  <div>
                    <p className="text-slate-200 font-medium mb-1">{point.label}</p>
                    <p className="text-sm text-slate-500">{point.detail}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>

        </div>
      </div>
    </section>
  );
};
```

This replaces the `01`/`02`-style spec-sheet numbering with a small dot marker (matching the `BuiltFor` section's role-list style) per the design doc's direction to drop the "systems audit" presentation.

- [ ] **Step 2: Verify build**

Run: `cd /Users/thecasterymedia/slateone && npm run build`
Expected: exits 0.

- [ ] **Step 3: Commit**

```bash
cd /Users/thecasterymedia/slateone
git add components/IndustryReality.tsx
git commit -m "style: reskin IndustryReality, drop numbered spec-sheet presentation"
```

---

### Task 5: Merge SystemArchitecture into OperatingLayer, delete SystemArchitecture

**Files:**
- Modify: `/Users/thecasterymedia/slateone/components/OperatingLayer.tsx`
- Delete: `/Users/thecasterymedia/slateone/components/SystemArchitecture.tsx`

**Interfaces:**
- Consumes: `App.tsx` no longer renders or imports `SystemArchitecture` (done in Task 2).

- [ ] **Step 1: Replace `OperatingLayer.tsx` in full**

```tsx
import React from 'react';
import { FileText, BarChart3, LayoutGrid, Calendar } from 'lucide-react';

const capabilities = [
  {
    icon: <FileText className="w-5 h-5" />,
    title: 'Script → Structured Data',
    description: 'Your script is converted into structured production data — scenes, cast, props, locations, FX, wardrobe, and vehicles extracted and classified automatically.',
  },
  {
    icon: <BarChart3 className="w-5 h-5" />,
    title: 'Breakdown → Dynamic Reports',
    description: 'Reports generate directly from your breakdown data — no static PDFs to redo by hand. When a revision drops, every report and view updates with it.',
  },
  {
    icon: <LayoutGrid className="w-5 h-5" />,
    title: 'Visualization → Stripboard Control',
    description: 'See your production by story day, location, and character on a zoomable stripboard — one shared view your whole team can work from.',
  },
  {
    icon: <Calendar className="w-5 h-5" />,
    title: 'Scheduling → Connected to Breakdown',
    description: 'Your shooting schedule stays connected to the breakdown it came from — change one and the other reflects it, instead of drifting apart in separate spreadsheets.',
  },
];

export const OperatingLayer: React.FC = () => {
  return (
    <section className="py-32 bg-slate-900 border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

        <div className="max-w-3xl mb-20">
          <h2 className="text-4xl md:text-5xl font-bold text-slate-50 mb-6 leading-[1.1]">
            From Script to<br/>Shooting Schedule
          </h2>
          <p className="text-lg text-slate-400 leading-relaxed">
            SlateOne isn't a script analyzer, a breakdown app, and a scheduling tool bolted
            together — it's one system that takes your script all the way to a shootable
            schedule, with everything staying connected along the way.
          </p>
        </div>

        {/* Capability grid */}
        <div className="grid md:grid-cols-2 gap-px bg-slate-800 border border-slate-800 rounded-xl overflow-hidden">
          {capabilities.map((cap, i) => (
            <div key={i} className="bg-slate-900 p-10 group hover:bg-slate-800/60 transition-colors duration-300">
              <div className="flex items-center gap-3 mb-5">
                <div className="w-10 h-10 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-500 group-hover:bg-amber-500/20 transition-colors">
                  {cap.icon}
                </div>
                <span className="text-[10px] font-mono text-slate-600 uppercase tracking-widest">
                  {String(i + 1).padStart(2, '0')}
                </span>
              </div>
              <h3 className="text-xl font-bold text-slate-50 mb-3">
                {cap.title}
              </h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                {cap.description}
              </p>
            </div>
          ))}
        </div>

        {/* Reinforcement line — folded in from the retired SystemArchitecture section */}
        <p className="mt-12 text-center text-sm text-slate-500 font-mono tracking-widest uppercase">
          One script in. One connected system out.
        </p>

      </div>
    </section>
  );
};
```

Changes from the original beyond reskinning: capability titles/descriptions rewritten to name real product surfaces (stripboard, shooting schedule) instead of abstract "Kanban Control"/"Connected Intelligence" framing, and the retired `SystemArchitecture` section's closing line ("One System. Complete Visibility. Operational Control.") is replaced with a shorter line reflecting the same "connected, not fragmented" point without repeating a whole second flow diagram.

- [ ] **Step 2: Delete `SystemArchitecture.tsx`**

```bash
cd /Users/thecasterymedia/slateone
rm components/SystemArchitecture.tsx
```

- [ ] **Step 3: Verify build**

Run: `cd /Users/thecasterymedia/slateone && npm run build`
Expected: exits 0 (confirms nothing still imports the deleted file — `App.tsx`'s import was already removed in Task 2).

- [ ] **Step 4: Commit**

```bash
cd /Users/thecasterymedia/slateone
git add components/OperatingLayer.tsx
git rm components/SystemArchitecture.tsx
git commit -m "feat: merge SystemArchitecture into OperatingLayer, reskin, name concrete features"
```

---

### Task 6: BuiltFor (`BuiltFor.tsx`) — reskin

**Files:**
- Modify: `/Users/thecasterymedia/slateone/components/BuiltFor.tsx`

- [ ] **Step 1: Replace the full component**

```tsx
import React from 'react';

const roles = [
  { title: 'Production Companies', description: 'Centralized operational control across all active productions.' },
  { title: 'Producers', description: 'System-level visibility from script to scheduling to execution.' },
  { title: 'Line Producers', description: 'Structured breakdown data connected directly to budget and schedule.' },
  { title: 'UPMs', description: 'Dynamic reporting and resource allocation from a single data source.' },
  { title: 'First Assistant Directors', description: 'Connected scheduling intelligence built on real breakdown data.' },
];

export const BuiltFor: React.FC = () => {
  return (
    <section className="py-32 bg-slate-900 border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

        <div className="grid lg:grid-cols-2 gap-16 items-start">

          {/* Left: Statement */}
          <div>
            <h2 className="text-4xl md:text-5xl font-bold text-slate-50 mb-8 leading-[1.1]">
              Built for Serious<br/>Production Teams
            </h2>
            <p className="text-lg text-slate-400 leading-relaxed max-w-lg mb-8">
              SlateOne is designed for production companies that treat filmmaking as an
              operational discipline — not a collection of disconnected tools.
            </p>
            <div className="border-l-2 border-amber-500/30 pl-6">
              <p className="text-slate-300 text-sm leading-relaxed italic">
                "I am loving SlateOne and will highly recommend it to my colleagues! It just did an excellent script breakdown and DOOD's for my film Umbulali — saved me so much time and $'s."
              </p>
              <p className="text-xs text-slate-500 font-mono mt-3 tracking-wide">
                — Dan Jawitz, Film producer
              </p>
            </div>
          </div>

          {/* Right: Roles */}
          <div className="space-y-0">
            {roles.map((role, i) => (
              <div key={i} className="border-b border-slate-800 py-6 first:pt-0 last:border-b-0 group">
                <div className="flex items-start gap-4">
                  <span className="w-2 h-2 rounded-full bg-amber-500/40 mt-2.5 flex-shrink-0 group-hover:bg-amber-500 transition-colors" />
                  <div>
                    <p className="text-slate-50 font-medium mb-1">{role.title}</p>
                    <p className="text-sm text-slate-500">{role.description}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>

        </div>
      </div>
    </section>
  );
};
```

Copy unchanged, per the design doc — restyle only.

- [ ] **Step 2: Verify build**

Run: `cd /Users/thecasterymedia/slateone && npm run build`
Expected: exits 0.

- [ ] **Step 3: Commit**

```bash
cd /Users/thecasterymedia/slateone
git add components/BuiltFor.tsx
git commit -m "style: reskin BuiltFor to slate/amber palette"
```

---

### Task 7: Pricing (`Pricing.tsx`) — reskin only

**Files:**
- Modify: `/Users/thecasterymedia/slateone/components/Pricing.tsx`

- [ ] **Step 1: Replace section/background classes**

Replace line 80–81:
```tsx
    <section id="pricing" className="bg-black relative overflow-hidden">
      <div className="absolute inset-0 opacity-[0.02] bg-[linear-gradient(rgba(255,255,255,0.1)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.1)_1px,transparent_1px)] [background-size:40px_40px]" />
```
with:
```tsx
    <section id="pricing" className="bg-slate-950 relative overflow-hidden">
      <div className="absolute inset-0 opacity-[0.02] bg-[linear-gradient(rgba(255,255,255,0.1)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.1)_1px,transparent_1px)] [background-size:40px_40px]" />
```

- [ ] **Step 2: Replace the header block (lines 88–103)**

```tsx
        <div className="py-32 border-b border-slate-800">

          <div className="max-w-3xl mb-8">
            <h2 className="text-4xl md:text-5xl font-bold text-slate-50 mb-6 leading-[1.1]">
              Simple Pricing.<br/>Built For How You Work.
            </h2>
            <p className="text-lg text-slate-400 leading-relaxed mb-6">
              Pay per breakdown when you need it, or license your whole
              team for the year. Uploading and editing scripts is always
              free &mdash; you only pay when you run a breakdown.
            </p>
            <p className="text-sm text-slate-500 font-mono">
              Prices in ZAR. No lock-in.
            </p>
          </div>
        </div>
```

- [ ] **Step 3: Replace the tier grid block (lines 108–207)**

```tsx
        <div className="py-32 border-b border-slate-800">

          <p className="text-center text-2xl md:text-3xl font-bold text-slate-200 mb-12">
            Work solo. Or bring the whole crew.
          </p>

          <div className="grid md:grid-cols-2 gap-6 max-w-5xl mx-auto items-stretch">
            {TIERS.map((tier) => (
              <div
                key={tier.id}
                className={`relative border rounded-2xl overflow-hidden flex flex-col ${
                  tier.highlighted
                    ? 'border-amber-500/30 bg-amber-500/[0.03] shadow-lg'
                    : 'border-slate-700 bg-slate-800'
                }`}
              >
                {tier.highlighted && (
                  <div className="absolute top-0 right-0 text-[10px] font-mono font-bold uppercase tracking-[0.2em] text-slate-900 bg-amber-500 px-3 py-1 rounded-bl-lg">
                    Recommended
                  </div>
                )}

                {/* Plan Header */}
                <div className="p-10 border-b border-slate-700">
                  <span
                    className={`text-[10px] font-mono font-bold uppercase tracking-[0.2em] px-3 py-1 rounded inline-block mb-6 ${
                      tier.highlighted
                        ? 'text-amber-500 bg-amber-500/10 border border-amber-500/20'
                        : 'text-slate-400 bg-slate-700 border border-slate-600'
                    }`}
                  >
                    {tier.badge}
                  </span>
                  <h3 className="text-xl font-bold text-slate-50 mb-4">{tier.name}</h3>
                  <div className="flex items-baseline gap-1 mb-1">
                    <span className="text-5xl font-bold text-slate-50">{tier.price}</span>
                    <span className="text-base text-slate-500 font-mono">{tier.priceUnit}</span>
                  </div>
                  {tier.priceNote && (
                    <p className="text-sm text-amber-500/70 font-mono mb-3">{tier.priceNote}</p>
                  )}
                  <p className="text-slate-400 text-sm mt-3">{tier.tagline}</p>
                </div>

                {/* Features List */}
                <div className="p-10 space-y-4 flex-1">
                  {tier.features.map((item, i) => (
                    <div key={i} className="flex items-start gap-3 text-[15px] text-slate-400">
                      <Check className="w-4 h-4 text-amber-500/50 flex-shrink-0 mt-1" />
                      {item}
                    </div>
                  ))}

                  {tier.footnote && (
                    <p className="text-[13px] text-slate-500 italic pt-2">{tier.footnote}</p>
                  )}

                  {tier.teamsBand && (
                    <div className="mt-4 rounded-xl border border-amber-500/20 bg-amber-500/[0.06] p-6">
                      <div className="flex items-center gap-2 mb-3">
                        <Users className="w-4 h-4 text-amber-500" />
                        <span className="text-[10px] font-mono font-bold uppercase tracking-[0.2em] text-amber-500">
                          {tier.teamsBand.eyebrow}
                        </span>
                      </div>
                      <h4 className="text-lg font-bold text-slate-50 mb-2 leading-tight">
                        {tier.teamsBand.headline}
                      </h4>
                      <p className="text-sm text-slate-400 leading-relaxed mb-5">
                        {tier.teamsBand.line}
                      </p>
                      <div className="space-y-3">
                        {tier.teamsBand.features.map((item, i) => (
                          <div key={i} className="flex items-center gap-3 text-[15px] text-slate-200">
                            <Check className="w-4 h-4 text-amber-500 flex-shrink-0" />
                            {item}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* CTA */}
                <div className="px-10 pb-10">
                  <button
                    onClick={() => setSelectedTier(tier.id)}
                    className={`w-full font-bold py-4 px-6 rounded-lg transition-all duration-300 text-sm cursor-pointer ${
                      tier.highlighted
                        ? 'bg-amber-500 text-slate-900 hover:bg-amber-400'
                        : 'bg-slate-700 text-slate-50 border border-slate-600 hover:bg-slate-600'
                    }`}
                  >
                    {tier.cta}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
```

(Removed `uppercase tracking-wide` from the CTA button per the no-uppercase-labels constraint; the small mono eyebrow labels like "Recommended" and tier badges keep their uppercase/tracked mono treatment since those mirror the app's own dense-label convention, e.g. `--text-2xs` badges.)

- [ ] **Step 4: Replace the "Who This Is For" block (lines 212–234)**

```tsx
        <div className="py-32">
          <div className="max-w-3xl mx-auto text-center">
            <p className="text-[10px] font-mono text-slate-500 uppercase tracking-[0.2em] mb-6">Built For</p>
            <h3 className="text-3xl md:text-4xl font-bold text-slate-50 mb-8 leading-[1.1]">
              Who This Is For
            </h3>

            <div className="flex flex-wrap justify-center gap-3 mb-10">
              {['Indie filmmakers', 'Production companies', 'Studios', 'Producers', 'Line producers', 'UPMs'].map((role) => (
                <span key={role} className="text-sm text-slate-400 bg-slate-800 border border-slate-700 px-5 py-2.5 rounded-lg font-mono">
                  {role}
                </span>
              ))}
            </div>

            <p className="text-lg text-slate-400 leading-relaxed mb-2">
              If your production runs on spreadsheets and fragmented tools,
            </p>
            <p className="text-lg text-slate-200 font-medium">
              SlateOne replaces that system.
            </p>
          </div>
        </div>
```

- [ ] **Step 5: Verify build**

Run: `cd /Users/thecasterymedia/slateone && npm run build`
Expected: exits 0.

- [ ] **Step 6: Commit**

```bash
cd /Users/thecasterymedia/slateone
git add components/Pricing.tsx
git commit -m "style: reskin Pricing to slate/amber palette, copy unchanged"
```

---

### Task 8: TierSelectionModal (`TierSelectionModal.tsx`) — reskin

**Files:**
- Modify: `/Users/thecasterymedia/slateone/components/TierSelectionModal.tsx`

- [ ] **Step 1: Replace the return block (lines 67–135)**

```tsx
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <div className="relative bg-slate-800 border border-slate-700 rounded-xl max-w-md w-full p-8 shadow-2xl">

        {/* Close */}
        <button
          onClick={handleClose}
          disabled={isSubmitting}
          className="absolute top-4 right-4 text-slate-500 hover:text-slate-200 transition-colors disabled:opacity-50"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="mb-6">
          <p className="text-[10px] font-mono text-amber-500/70 uppercase tracking-[0.2em] mb-3">
            Continue to Signup
          </p>
          <h2 className="text-xl font-bold text-slate-50 mb-1">{details.name}</h2>
          <p className="text-sm text-slate-500">{details.tagline}</p>
        </div>

        {/* Price */}
        <div className="bg-slate-700 border border-slate-600 rounded-lg p-4 mb-6 flex items-center justify-between">
          <span className="text-sm text-slate-300">{details.priceLabel}</span>
          <span className="text-lg font-bold text-amber-500">{details.price}</span>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-3">
          <input
            type="email"
            name="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email address"
            disabled={isSubmitting}
            className="w-full bg-slate-700 border border-slate-600 text-slate-50 placeholder-slate-500 px-4 py-3 rounded-lg focus:outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/30 transition-all text-sm disabled:opacity-50"
          />

          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-amber-500 text-slate-900 font-bold px-6 py-3.5 rounded-lg hover:bg-amber-400 transition-all duration-300 flex items-center justify-center gap-2 text-sm disabled:opacity-50"
          >
            {isSubmitting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                Continue to Signup
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>

          <p className="text-[10px] text-slate-600 text-center pt-1">
            You'll be taken to app.slateone.studio to create your account.
          </p>
        </form>
      </div>
    </div>
  );
};
```

(Removed `uppercase tracking-wide` from the submit button per the no-uppercase-labels constraint; kept it on the small "Continue to Signup" mono eyebrow label, consistent with Task 7's treatment of dense mono labels.)

- [ ] **Step 2: Verify build**

Run: `cd /Users/thecasterymedia/slateone && npm run build`
Expected: exits 0.

- [ ] **Step 3: Commit**

```bash
cd /Users/thecasterymedia/slateone
git add components/TierSelectionModal.tsx
git commit -m "style: reskin TierSelectionModal to slate/amber palette"
```

---

### Task 9: Footer (`Footer.tsx`) — reskin, then full visual verification pass

**Files:**
- Modify: `/Users/thecasterymedia/slateone/components/Footer.tsx`

- [ ] **Step 1: Replace the full component**

```tsx
import React from 'react';
import { Film } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="py-12 bg-slate-900 border-t border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">

          {/* Logo */}
          <div className="flex items-center gap-2">
            <Film className="h-5 w-5 text-amber-500" />
            <span className="font-bold text-lg tracking-tight text-slate-50">
              Slate<span className="text-amber-500">One</span>
            </span>
            <span className="text-slate-600 text-xs font-mono ml-3">Production Infrastructure</span>
          </div>

          {/* Contact */}
          <div className="flex items-center gap-6 text-xs text-slate-500">
            <a href="mailto:hello@slateone.studio" target="_blank" rel="noopener noreferrer" className="hover:text-amber-500 transition-colors">
              hello@slateone.studio
            </a>
          </div>

        </div>
      </div>
    </footer>
  );
};
```

- [ ] **Step 2: Run full build**

Run: `cd /Users/thecasterymedia/slateone && npm run build`
Expected: exits 0, with no remaining references to `charcoal`, `neon`, `cyan`, `soft-grey`, `paper`, or `font-display` anywhere in `dist/` output.

- [ ] **Step 3: Grep-verify no legacy tokens remain**

Run:
```bash
cd /Users/thecasterymedia/slateone
grep -rn "neon\|charcoal\|cyan\|font-display\|soft-grey\|Space Grotesk\|Courier Prime" components/ App.tsx index.html
```
Expected: no output (all removed). If any hits remain, fix them before proceeding — they indicate a component missed during Tasks 2–9.

- [ ] **Step 4: Manual visual check**

Run: `cd /Users/thecasterymedia/slateone && npm run dev`
Open `http://localhost:3000` in a browser and scroll through the full page: confirm slate/amber palette throughout, no neon-green anywhere, Inter font on headlines (not a display serif/geometric font), Hero shows the new headline copy, and the merged Operating Layer section reads as one section (no separate System Architecture flow diagram below it). Stop the dev server after checking (`Ctrl+C`).

- [ ] **Step 5: Commit**

```bash
cd /Users/thecasterymedia/slateone
git add components/Footer.tsx
git commit -m "style: reskin Footer to slate/amber palette"
```

---

## Self-Review Notes

- **Spec coverage:** Color/typography/shape tokens (spec §1) → Tasks 1–9. Component reuse conventions (spec §2, e.g. no-uppercase buttons, solid card surfaces, badge treatment) → applied throughout Tasks 2–9. IA merge (spec §3) → Task 5. Hero/Pricing exact copy (spec §3) → Tasks 3 and 7 respectively (Pricing copy intentionally unchanged, matching spec). Accessibility contrast note (spec §2) → covered by using Tailwind's stock `slate-400`/`slate-500` for secondary/muted text, which are the same values already used at matching opacity levels in the live app; no separate automated contrast test exists in this repo to wire up, so Task 9's manual visual check is the closest available verification.
- **Out of scope confirmed untouched:** Legal pages (`PrivacyPolicy.tsx`, `TermsOfService.tsx`) are not part of this plan, matching the design doc's "Out of Scope" section — restyle them in a follow-up pass.
