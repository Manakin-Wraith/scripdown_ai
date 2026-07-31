# SlateOne Tiered Business Model Specification

## 1. Executive Summary

SlateOne will launch with a **two-tier subscription model** designed to serve both occasional users and production teams. The model separates the cost of **analysis** (per-breakdown consumption) from **collaboration** (annual team seats).

**Core principle:** Any user, on any tier, can upload as many scripts as they want without charge. Payment is triggered only when the user requests an **AI breakdown / analysis** on a script.

## 2. Tier Overview

| Attribute | **Tier 1 — Pay-Per-Breakdown** | **Tier 2 — Team License** |
| --- | --- | --- |
| **Billing model** | Consumption / pay-as-you-go | Monthly or annual subscription + per-seat fee |
| **Cost** | ZAR 450 per breakdown/analysis | Monthly: ZAR 1,850/mo + ZAR 250/seat/mo · Annual: ZAR 18,500/yr + ZAR 2,500/seat/yr |
| **Script uploads** | Unlimited | Unlimited |
| **Teams / collaboration** | **Not enabled** | **Enabled** |
| **Seat billing** | N/A | To be determined (see §5) |
| **Target user** | Freelancers, individual writers, small producers | Production companies, ADs, producers, department heads |

## 3. Pricing Details

### 3.1 Tier 1 — Pay-Per-Breakdown
- **Price:** ZAR 450 per AI breakdown/analysis.
- **What counts as a breakdown:** Any request that triggers the AI pipeline to extract breakdown items (cast, props, wardrobe, vehicles, makeup & hair, SFX, sound, atmosphere) or narrative intelligence from a script.
- **Scoping note:**
  - Scene detection and script parsing on upload are **not** charged.
  - Manual scene editing, reordering, and locking are **not** charged.
  - Each AI analysis request (single scene or bulk "Analyze All") is a billable event.
  - Re-analysis of the same script after edits counts as a new breakdown.

### 3.2 Tier 2 — Team License
One product, two billing cadences — annual is a discounted prepay of the
same license (~17% off vs. paying monthly for a year), not a separate
offering.

| Cadence | Base license | Per-seat fee |
| --- | --- | --- |
| **Monthly** | ZAR 1,850/month per account/organization | ZAR 250/seat/month |
| **Annual** | ZAR 18,500/year per account/organization | ZAR 2,500/seat/year |

- **Includes:** Unlimited AI breakdowns for the account owner and all paid seats, on either cadence.
- **Seat term:** A seat's term always matches the license's own term/cadence — seats don't pick a separate cycle from the license they belong to.
- **Minimum seat count:** 1 (the owner).

## 4. Feature Matrix

The table below lists SlateOne's currently available features and indicates which tier includes them.

### 4.1 Common to Both Tiers

All tiers get the following features without restriction:

1. **AI-Powered Script Breakdown & Ingestion**
   - Instant scene detection on PDF upload.
   - Deep AI extraction (cast, props, wardrobe, vehicles, makeup & hair, SFX, sound, atmosphere).
   - Smart entity resolution (character name merge / dedup).
   - Cover page metadata extraction.

2. **Scene & Story Management**
   - Master-detail scene viewer (scene, character, and location perspectives).
   - Story days intelligence (auto-detection, manual lock, bulk assign, timeline codes).
   - Script editing (split, merge, omit/restore, reorder, manual add).
   - Revision tracking and script locking.

3. **Narrative & Scene Intelligence**
   - Narrative dashboard (plot structure, character arcs, pacing, emotional flow, relationship web).
   - Scene deep dive (dialogue subtext, emotions, action beats, transitions).

4. **Interactive Scheduling**
   - Zoomable stripboard with semantic zoom levels.
   - Grouping and filtering by INT/EXT, time of day, location, and story day.

5. **Exporting & Reporting**
   - All customizable production reports (scene breakdown, DOOD, location, props, wardrobe, one-liner, full binder).
   - Report filtering across 9 dimensions and saved filter presets.
   - Highlighted script PDF export.
   - Shooting script export.
   - Public share links for generated reports.

### 4.2 Tier-Specific Features

| Feature | Tier 1 | Tier 2 |
| --- | --- | --- |
| Unlimited script uploads | ✅ | ✅ |
| AI breakdown / analysis | ✅ (ZAR 450 each) | ✅ (included) |
| Exporting & reporting | ✅ | ✅ |
| Zoomable stripboard | ✅ | ✅ |
| Narrative intelligence | ✅ | ✅ |
| Scene editing & story days | ✅ | ✅ |
| **Teams — invite crew members** | ❌ **Not enabled** | ✅ **Enabled** |
| **Department workspaces** | ❌ **Not enabled** | ✅ **Enabled** |
| **Cross-department threads** | ❌ **Not enabled** | ✅ **Enabled** |
| **Department item tracking & notes** | ❌ **Not enabled** | ✅ **Enabled** |
| **Team access control & invites** | ❌ **Not enabled** | ✅ **Enabled** |

### 4.3 Tier 1 Exclusions

Users on Tier 1 **cannot**:
- Invite or add members to a script.
- Access department-specific workspaces.
- Create or participate in cross-department discussion threads.
- Assign breakdown items to crew members.
- Use team-related access controls or share scripts via the team model.

Tier 1 users can still:
- Upload unlimited scripts.
- Run unlimited scene detection and manual scene edits.
- Purchase per-breakdown analysis on any uploaded script.
- Use all personal export and reporting tools.

## 5. Team Seat Payment Model — Brainstorm & Recommendation

### 5.1 Option A: Account Owner Pays for All Seats

**Description:** The Tier 2 account owner / script owner is billed the per-seat fee (matching the license's own cadence — ZAR 250/mo or ZAR 2,500/yr) for every seat they invite, regardless of who accepts.

**Pros:**
- Simple billing relationship (owner = customer).
- No friction for invited members (one-click accept).
- Mirrors common SaaS patterns (Notion, Slack, Figma).
- Easy to invoice and support.

**Cons:**
- Owner bears cost if invited members are slow to accept or under-use.
- May discourage wide collaboration on cost-sensitive productions.

### 5.2 Option B: Invited Member Pays for Their Own Seat

**Description:** Each invited crew member pays the per-seat fee individually (matching the license's cadence) to activate their seat after accepting the invite.

**Pros:**
- Distributes cost across the production team.
- Owner does not front cash for large crews.
- Members are financially committed, potentially leading to higher activation.

**Cons:**
- High friction during invite flow; members may abandon.
- Billing is fragmented across many users.
- Harder to support and reconcile.
- Conflicts with the "team license" concept where the owner is the customer.

### 5.3 Option C: Hybrid — Owner Pays, with Member Reimbursement Optional

**Description:** The owner pays for all seats by default. The UI can optionally display per-member cost so productions can internally recover the fee from departments or crew members.

**Pros:**
- Keeps billing simple for SlateOne.
- Gives productions flexibility to charge back internally.
- Maintains low-friction invite acceptance.

**Cons:**
- Still requires owner to have budget / cash flow.
- Internal chargebacks are out of SlateOne's control.

### 5.4 Recommendation

**Adopt Option A as the primary model**, with Option C as a documented flexibility note.

**Rationale:**
- Production companies, line producers, and heads of department are the natural customers for SlateOne.
- Centralized billing aligns with how film/ TV productions budget software tools.
- It minimizes drop-off in the invite flow and keeps support overhead low.
- The UI should still show the per-seat cost for the account's chosen cadence so owners can internally allocate the expense.

**Decision:**
- **The Tier 2 account owner pays for each seat.**
- Seats are billed on the same cadence as the base license (monthly or annual — a seat never has its own separate cycle).
- Owners can invite / remove seats at any time; prorated credits/refunds for removed seats can be a Phase 2 enhancement.

## 6. Script Upload Policy

- **All tiers:** Unlimited script uploads are allowed.
- Uploading a PDF, parsing it into scenes, and manually editing scenes are **free**.
- AI analysis is the only billable event in Tier 1; it is included without incremental cost in Tier 2.
- Script storage quotas and fair-use limits may be added in future phases if operational costs require them.

## 7. Usage Scenarios

### 7.1 Tier 1 Example — Solo Screenwriter
1. Signs up for free / Tier 1.
2. Uploads 5 scripts over 3 months.
3. Runs AI breakdown on 2 scripts.
4. **Cost:** 2 × ZAR 450 = **ZAR 900**.
5. Cannot invite a producer or AD to collaborate.

### 7.2 Tier 2 Example — Small Production (Annual)
1. Production company subscribes to Tier 2, annual cadence.
2. Base license: ZAR 18,500/year.
3. Invites 4 crew members (producer, 1st AD, costume, locations).
4. Seats: 4 × ZAR 2,500 = ZAR 10,000.
5. **First-year cost:** ZAR 18,500 + ZAR 10,000 = **ZAR 28,500**.
6. Team can run unlimited AI breakdowns and use department workspaces.

### 7.3 Tier 2 Example — Small Production (Monthly)
1. Same production, monthly cadence instead.
2. Base license: ZAR 1,850/month.
3. Seats: 4 × ZAR 250 = ZAR 1,000/month.
4. **Monthly cost:** ZAR 1,850 + ZAR 1,000 = **ZAR 2,850/month** (ZAR 34,200/year if never switched to annual).

## 8. Billing & Enforcement

### 8.1 Tier 1 Billing
- Breakdowns are purchased via a "credit" or direct charge model.
- User must confirm payment before AI analysis begins.
- Wallet / credit balance can be displayed in the UI.
- Failed payment blocks further analysis until resolved.

### 8.2 Tier 2 Billing
- Monthly or annual subscription (customer's choice at signup), with automatic renewal.
- Seat count can be changed mid-cycle; changes apply at next renewal unless prorating is implemented.
- A seat's term always matches its license's own cadence — switching the license's cadence is a new subscription, not a seat-level setting.
- Failed renewal downgrades the account to Tier 1; team features become read-only or inaccessible.

### 8.3 Feature Gating
- The backend must enforce the Tier 1 exclusion for team endpoints (`/members`, `/invites`, `/threads`, `/departments`, `/workspace`).
- UI should hide or disable team-related buttons for Tier 1 users, with an upsell message.
- Tier 2 users should see seat management in account settings.

## 9. Open Decisions & Next Steps

1. **Payment provider integration:** Yoco / Stripe / Paystack support for ZAR.
2. **Refund / credit policy for failed or partial analyses.**
3. **Proration rules for seat changes mid-cycle.**
4. **Trial plan:** Should new users get one free breakdown or a 7-day Tier 2 trial?
5. **Non-profit / student pricing:** Future consideration.
6. **Tax (VAT) handling for South African customers.**

## 10. Summary

- **Tier 1** is a pure pay-per-analysis model for individuals: ZAR 450 per breakdown, unlimited uploads, no team features.
- **Tier 2** is a team license with monthly or annual cadence (ZAR 1,850/mo + ZAR 250/seat/mo, or ZAR 18,500/yr + ZAR 2,500/seat/yr — annual is a ~17% discounted prepay of the same product), includes all analysis and full team collaboration.
- **Team seats are paid by the account owner** (recommended Option A) to minimize friction and align with production budgeting workflows.
- **Script uploads and manual scene work are always free**; only AI-driven breakdowns trigger charges in Tier 1.
