# Team License Pricing Change — Brief for Design

**Date:** 2026-08-03
**Audience:** UI/UX design team
**Purpose:** Brainstorm landing page and billing-page changes to reflect the new Team License pricing structure.

---

## 1. What changed, in one sentence

The Team License used to sell on **2 billing cadences** (monthly, annual) with **zero included seats** — every seat was a paid add-on. It now sells on **4 cadences** (monthly, 3-month, 6-month, annual), each **bundling a number of free seats**, with additional seats priced at a flat rate that doesn't discount for longer terms.

Solo (pay-per-breakdown, R2,250/analysis) is unchanged.

---

## 2. Old vs. new pricing

### Old model (2 cadences, no included seats)

| Cadence | License price | Included seats | Extra seat price |
|---|---|---|---|
| Monthly | R1,850/mo | 0 | R250/seat/mo |
| Annual | R18,500/yr | 0 | R2,500/seat/yr |

### New model (4 cadences, included seats scale with commitment)

| Cadence | License price | Included seats | Extra seat price |
|---|---|---|---|
| **Monthly** | R1,850 | 0 | R250/mo |
| **3-Month** | R5,500 | 1 | R750 flat (= R250 × 3) |
| **6-Month** | R9,500 | 2 | R1,500 flat (= R250 × 6) |
| **Annual** | R18,500 | 3 | R3,000 flat (= R250 × 12) |

**Key rule for extra seats: no discount, ever.** Unlike the license price (which gets cheaper per month the longer you commit), an extra seat always costs exactly R250 for every month of the term. This is a deliberate contrast worth making visually clear: *"the license rewards commitment, seats don't get cheaper — they're just bundled more generously."*

---

## 3. Why this matters for the landing page / pricing page

The current pricing page (and `BillingPage.jsx` in the app) was built around a **2-way toggle** (Monthly / Annual). That's no longer sufficient — there are now **4 options**, and each one has a *different* story to tell:

1. **Monthly** — lowest commitment, no seats included, meant for a solo team lead testing the waters.
2. **3-Month** — light commitment, gets you and one collaborator in.
3. **6-Month** — a small department (2 extra people beyond the owner).
4. **Annual** — the "full team" tier: owner + 3 seats included, best per-month rate.

This changes the pricing page from "pick monthly or annual" to **"pick how big your team is and how long you're committing"** — the seat count is now a first-class part of the decision, not an afterthought bolted on after picking a cadence.

### Things design should think through:

- **How to display 4 pricing cards/columns instead of 2** without the page feeling cluttered — a horizontal toggle (like the current one) may not scale well to 4 options with genuinely different included-seat counts. Consider whether a toggle still works or whether this wants a small comparison table instead.
- **How to communicate "included seats" as a headline benefit**, not a footnote. E.g. "6-Month — R9,500, your whole 3-person crew included" reads very differently from "R9,500 + seats."
- **Savings messaging accuracy.** True monthly-equivalent savings vs. the R1,850/mo baseline:
  - 3-Month ≈ R1,833/mo → **not a meaningful discount** (don't badge it, or it'll look like false advertising).
  - 6-Month ≈ R1,583/mo → **~14% savings**.
  - Annual ≈ R1,542/mo → **~17% savings**.
- **Extra-seat pricing needs its own micro-copy**, separate from the license price — e.g. "Need more? Extra seats are R250/month, no matter which plan you pick." This flat, no-discount seat rate is actually a simplicity selling point (easy mental math) and could be framed that way rather than buried in fine print.
- **The "your first N people are free" framing** may outperform "buy the license, then buy seats" as a pitch, especially for the 6-month and annual tiers where the included count is meaningful (2–3 people, likely a whole small crew).

---

## 4. Copy/terminology changes already made in the app

For consistency, if design produces new landing-page copy it should follow these renames already live in the product:

- "**Annual Team License**" → "**Team License**" (it's no longer annual-exclusive; drop the word "Annual" from any evergreen copy).
- Tier 1 is now labelled "**Solo**" / "Pay-Per-Breakdown" internally at R2,250/analysis (unchanged by this project, just noting it sits alongside Team License on the pricing page).

---

## 5. Reference: current in-app billing page

The billing page inside the app (`frontend/src/pages/BillingPage.jsx`) has already been updated to the 4-cadence model as a functional baseline — a 4-button cycle toggle with per-cadence copy ("R9,500/6mo — includes 2 seats, unlimited breakdowns. Extra seats R1,500 each."). It is **not** meant to be the final design — it's plumbing-first, not marketing-first — but it's a working reference for the numbers, the states (which cadence is "active," what seat math looks like), and the underlying logic design should feel free to override visually.

---

## 6. Non-negotiables (constraints for any redesign)

- Whatever UI ships, the actual prices, cadence names (`monthly`/`3month`/`6month`/`annual`), and included-seat counts must match the table in §2 exactly — these are enforced server-side and in the database, so marketing copy that drifts from them will just be wrong, not aspirational.
- Seats always share the license's term — there's no "pick your own seat cadence" concept to design for.
- The owner's own membership does not count against the included-seat bundle in the backend's accounting, but §3.2 of the internal spec ties "minimum seat count: 1" to the owner being present regardless of cadence — worth a product conversation with eng if design wants to message included seats as "N teammates" vs. "N seats total including you."
