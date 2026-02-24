# Feature Specification: Daily Production Reporting

**Feature Branch**: `feature/daily-production-reporting`  
**Created**: 2026-02-23  
**Status**: Draft (Rev 4 — State Synchronization & Attribution Fixes)  
**Input**: Brainstorm document `docs/CONCEPT_Daily_Production_Reporting.md`

---

## Purpose

Extend SlateOne from a pre-production planning tool into a production-day execution tracker. The Daily Production Report (DPR) captures what *actually* happens on set each shoot day, compares it against the planned schedule, and generates production intelligence analytics.

### Problem Statement

Once principal photography begins, SlateOne has no structured way to record what happened on set. Production teams currently rely on disconnected PDFs, spreadsheets, and manual compilation. This results in:

- No linkage between planned schedule and actual execution
- Limited visibility into schedule variance
- Manual overhead compiling daily reports
- No production intelligence from daily data

### Success Criteria

- Production teams can file a complete DPR within 30 minutes of wrap *(assumes connectivity; see FR-043a for low-bandwidth mode)*
- Planned vs actual page/scene variance is visible in real time
- DPRs can be exported as industry-standard formatted PDFs
- Cumulative analytics show production health across all shoot days
- Multi-unit productions can file separate DPRs per unit per day
- Locked DPRs maintain an immutable version chain for legal defensibility

---

## Architecture Decisions

The following decisions were resolved during spec review and have material impact on the feature design.

### AD-1: Multi-Unit Support (Option B — Multiple DPRs per Day)

Professional productions often run multiple units simultaneously (1st Unit, 2nd Unit, Splinter Unit). The system supports **one DPR per shooting day per unit**. A new **Unit** entity sits between Shooting Day and DPR:

```
ShootingSchedule → ShootingDay → Unit → DPR
                                        ├── SceneEntries
                                        ├── DepartmentLogs
                                        ├── TimeEntries
                                        ├── Incidents
                                        └── Delays
```

Units are customizable per production. Analytics aggregate at three levels: per unit, per shooting day (combined units), and per schedule.

**Combined-day aggregation rule** *(Gap Fix #2)*: When computing combined-day variance across units, the planned baseline belongs to the unit originally assigned in the schedule snapshot. Combined-day aggregation sums planned snapshots across all units for that day and sums actual pages across all units. Net variance is computed once from these combined sums — not by summing per-unit variances (which would double-count cross-unit pickups).

**Schedule-level burndown baseline** *(Rev 3 Gap Fix #2)*: For cumulative schedule burndown, the planned baseline MUST be derived from **unique scene planned pages in the schedule** (each scene counted once, regardless of how many DPR snapshots reference it), NOT from the sum of per-DPR snapshot planned pages. Actual pages are summed across all canonical DPRs. This prevents baseline inflation when a scene is partially shot across multiple days or units.

### AD-2: Planned Page Count Snapshot

Scene entries MUST store **snapshot data at DPR creation time**, not live references. Each scene entry records:
- Scene number (snapshot)
- **Scene heading / slugline** (snapshot) *(Gap Fix #5)*
- **INT/EXT** (snapshot) *(Gap Fix #5)*
- **Location name** (snapshot) *(Gap Fix #5)*
- **Day/Night** (snapshot) *(Gap Fix #5)*
- Planned page count in eighths (snapshot)
- Planned schedule order (snapshot)
- Planned unit assignment (snapshot)

All variance and analytics computations MUST use snapshot values, preserving historical integrity even if the schedule or scene data is later modified. This is critical for legal defensibility — if a scene's location or description is changed in the breakdown after the DPR is filed, the historical record must reflect what was planned at the time of shooting.

**Snapshot re-sync for Draft DPRs** *(Rev 4 Gap Fix #1)*: If the schedule changes after a DPR is created but the DPR is still in **Draft** status, the system MUST provide a "Re-sync with Schedule" action. This updates snapshot values to match the current schedule while preserving any entered actual data (pages, takes, times, logs). If a scene was removed from the schedule, its entry transitions to "Added" status. If a scene was added to the schedule, a new entry is created with "Not Shot" status. Re-sync is NOT available once DPR leaves Draft status — Submitted/Approved/Locked DPRs retain their original snapshots.

### AD-3: Day Classification

Each DPR MUST have a **day type** classification:
- **Shoot** — Standard production day
- **Company Move** — Relocation day
- **Prep** — Preparation day
- **Travel** — Travel day
- **Holiday** — Scheduled break
- **Dark** — No activity
- **Strike** — Set teardown

Velocity calculations (avg pages/day, projected wrap date) include **only Shoot days**. Overtime logic may vary by day type. Analytics exclude non-shoot days by default.

### AD-4: Carryover Pages Definition

**Planned Pages (Day)** = Sum of planned page snapshots for scenes assigned to that unit/day.
**Actual Pages (Day)** = Sum of actual page eighths where status is Complete or Partial.
**Carryover Pages** = Planned Pages − Actual Pages.

Rules:
- **Partial** → Remaining pages become a carryover candidate
- **Not Shot** → Full planned snapshot becomes a carryover candidate
- **Added** → No planned baseline impact (does not affect carryover)
- Carryover does NOT auto-reschedule — it becomes a flag available to the scheduling module
- Users decide per scene: carry over to next day or reschedule manually

### AD-5: Locked DPR Versioning (Immutable Version Chain)

Locked DPRs are legally binding documents. To support corrections:
- Unlocking creates a **new version** (clone of the locked DPR)
- The original locked version is marked as **superseded** but remains immutable
- Each version records: version number, parent DPR reference, locked timestamp
- Only Line Producer or AD can initiate an unlock; the correction is audit-logged
- PDF exports MUST indicate version number
- The latest non-superseded version is the canonical record

**Version clone behavior** *(Gap Fix #1)*: When creating a new version, the system:
- **Clones as-is**: Scene entries, department logs (with submission state), time entries, delays, incidents, attachment references
- **Resets**: DPR status → Draft, all sign-offs → cleared, approval timestamps → cleared, locked_at → null
- **Preserves**: Department log submission state (remains Submitted if previously submitted — logs are NOT reset to Pending)

This prevents accidental "auto-approval" in the new version while preserving department work.

**Pre-lock reversion** *(Rev 3 Gap Fix #1)*: The status workflow allows a **Submitted → Draft** transition (by AD or Line Producer only) without creating a version. Versioning only begins once a DPR has reached Locked status. This prevents version-chain pollution for minor pre-lock corrections. The reversion is audit-logged.

**Sign-off audit trail across versions** *(Rev 3 Gap Fix #8)*: When a new version is created, the audit trail of the new version MUST include the previous version's signatories, timestamps, and the reason for correction. This provides forensic traceability across the version chain for legal defensibility.

### AD-6: Camera Log — Data Integrity Verification

The Camera department log is extended beyond basic roll tracking to include media integrity fields:
- Media/card identifier, roll number
- Codec, resolution
- Checksum (for verification)
- Offload destination, offload completion timestamp
- Verified-by person
- LTO backup completed flag, LTO backup verification timestamp

MVP captures integrity metadata only — full DIT/LTO workflow engine is deferred.

### AD-7: Velocity Inclusion Logic

Each DPR carries an explicit **include in velocity** flag (defaults to true for Shoot days, false for others). Analytics formula:

- Average Pages/Day = Sum(actual pages where include_in_velocity = true) / Count(**distinct shooting days** where at least one included DPR exists)

*(Gap Fix #3)*: The denominator is **distinct shooting days**, NOT count of DPR records. If 3 units shoot on the same day (3 DPR records), that counts as 1 day in the denominator. This prevents velocity inflation in multi-unit productions.

*(Rev 3 Gap Fix #3)*: All analytics computations (velocity, burndown, delay aggregation, cumulative totals) MUST use **only canonical versions** (latest non-superseded) of each DPR. Superseded versions MUST be excluded from all aggregate calculations.

*(Rev 4 Gap Fix #6)*: Velocity analytics MUST distinguish between **Main Unit Velocity** and **Combined Velocity**:
- **Main Unit Velocity** = pages/day using only the designated main unit's DPRs (typically 1st Unit)
- **Combined Velocity** = pages/day using all units' DPRs
- **Projected Wrap Date** MUST default to Main Unit Velocity unless the production admin explicitly configures it to use Combined Velocity

This prevents projection distortion when a temporary Splinter Unit inflates the combined daily rate for a short period.

This makes projections defensible by allowing manual overrides (e.g., exclude an abnormal shoot day).

### AD-8: Attachments Model

A new **Attachment** entity supports file uploads across DPR sub-entities:
- Linked to: DPR, Incident, Department Log, or Scene Entry
- Records: file URL, file type, file size, uploader, upload timestamp
- Rules: max file size configurable per production, images auto-compressed, signed URLs for access
- In PDF exports: thumbnails only (optional)
- *(Gap Fix #8)*: When a DPR is versioned, the new version copies **attachment references** (pointers to the canonical file record), NOT the binary files themselves. This prevents storage duplication across version chains.

### AD-9: Approval Requirements (Option C — Configurable per Production)

Productions can configure approval strictness:
- **Strict mode** — All required departments must submit logs before DPR can be approved
- **Soft mode** — Approval allowed with pending departments, but a warning is shown
- **Configurable** — Production admin chooses which mode applies

This affects workflow enforcement, notification triggers, and UI warnings.

*(Gap Fix #4)*: Approval mode changes apply **only to future submissions**. DPRs already in Submitted or Approved status retain their current state and are not retroactively invalidated. This prevents workflow deadlocks.

*(Rev 3 Gap Fix #4)*: The list of **required departments** MUST be configurable at two levels:
1. **Per production** — Default required departments for all DPRs
2. **Per day type** — Override per day type (e.g., Travel days may not require Camera or Sound logs)

Without day-type-aware required departments, Strict mode conflicts with non-shoot days (e.g., a Travel DPR cannot be submitted if Camera log is required but no camera was used).

*(Rev 4 Gap Fix #3)*: Department logs support a **"Not Applicable Today" (N/A)** status in addition to Pending and Submitted. The AD can mark a required department's log as N/A (with a mandatory reason), which satisfies Strict mode requirements without forcing the department HOD to log in and submit an empty form. This handles production reality where a scheduled department (e.g., VFX) may not work on a given day.

---

## User Types & Roles

| Role | Description | Primary Actions |
|------|-------------|-----------------|
| **2nd AD / Production Coordinator** | Primary DPR author | Creates DPR, records scene progress, enters times, consolidates department inputs, submits for approval |
| **Department HOD** | Camera, Sound, Script Supervisor, Art, Costume, Makeup, Locations, VFX, Stunts, Transport | Submits department-specific log for the day |
| **Script Supervisor** | Special department role | Submits circle takes, continuity notes, dialogue changes |
| **1st AD / UPM / Line Producer** | Reviewer | Reviews and approves submitted DPR |
| **Producer** | Final authority | Signs off on DPR, views analytics dashboard |
| **Accounting / Payroll** | Consumer | Reads time sheet data from approved DPRs |

### Permission Matrix (Resolved)

| Action | AD | Line Producer | HOD | Producer | Accounting |
|--------|:--:|:-------------:|:---:|:--------:|:----------:|
| Create DPR | ✅ | ✅ | — | — | — |
| Edit DPR fields | ✅ | ✅ | — | — | — |
| Edit own dept log | ✅ | ✅ | ✅ | — | — |
| Submit DPR | ✅ | ✅ | — | — | — |
| Approve DPR | ✅ | ✅ | — | — | — |
| Lock DPR | ✅ | ✅ | — | — | — |
| Unlock (version) | ✅ | ✅ | — | — | — |
| Sign off | ✅ | ✅ | — | ✅ | — |
| View analytics | ✅ | ✅ | — | ✅ | — |
| View time sheets | ✅ | ✅ | — | ✅ | ✅ |
| Export PDF | ✅ | ✅ | — | ✅ | ✅ |

---

## User Scenarios & Testing

### Primary User Story

At the end of each shoot day, the 2nd AD opens the shooting day in SlateOne, selects the unit (1st Unit, 2nd Unit, etc.), and creates or resumes the Daily Production Report for that unit. The AD records which scenes were shot (complete, partial, not shot), enters call/wrap times, weather, day type classification, and general notes. Department heads submit their individual logs (camera with data integrity verification, sound, script supervisor). The AD enters cast time sheets. Once all data is captured, the AD submits the DPR for review. The Line Producer approves it and locks it as the official record. If a correction is needed after locking, the Line Producer or AD creates a new version (the original remains immutable). The DPR is exported as a versioned PDF for distribution via shareable link.

### Acceptance Scenarios

#### Scene Progress

1. **Given** a shooting day with 5 planned scenes, **When** the AD creates a DPR, **Then** all 5 scenes appear as entries with "Not Shot" status and their planned page counts pre-filled from the schedule.

2. **Given** a DPR with scene entries, **When** the AD marks scene 42 as "Complete" with 7 takes and 3 setups, **Then** the entry updates and daily totals recalculate automatically.

3. **Given** a DPR, **When** the AD marks scene 44 as "Partial" with 1 4/8 pages shot (planned was 3 1/8), **Then** the variance shows -1 5/8 pages for that scene.

4. **Given** a DPR, **When** the AD adds scene 12 (not on today's schedule), **Then** it appears with "Added" status, no planned page count, and an indicator that it was unscheduled.

5. **Given** 3 of 5 scenes marked Complete and 1 Added, **When** viewing the summary, **Then** totals show: 3 complete, 0 partial, 2 not shot, 1 added, and correct page variance.

#### Time Sheets

6. **Given** a DPR, **When** the AD enters cast member "John Smith" (playing DETECTIVE) with call 06:00, on-set 07:30, wrap 19:00, lunch 12:00–13:00, **Then** hours worked calculates to 12 hours (13h - 1h lunch).

7. **Given** a DPR for a day with scenes featuring characters DETECTIVE and NURSE, **When** the AD triggers "auto-populate cast," **Then** time entries are pre-created for DETECTIVE and NURSE with names and character fields filled, times blank.

#### Department Logs

8. **Given** a DPR, **When** the Camera HOD submits a camera log with rolls, codec, and backup status, **Then** the log appears under the Camera department section with "Submitted" status and the submitter's name.

9. **Given** a DPR with 3 departments having submitted logs and 2 pending, **When** viewing the DPR summary, **Then** a submission tracker shows 3/5 departments complete.

#### Delays & Incidents

10. **Given** a DPR, **When** the AD logs a 45-minute weather delay affecting scene 44, **Then** the delay appears in the delays section and the daily delay total updates to 45 minutes.

11. **Given** a DPR, **When** the AD logs a minor injury incident with persons involved and action taken, **Then** the incident appears in the safety section with all recorded details.

#### Workflow

12. **Given** a DPR in "Draft" status, **When** the AD clicks "Submit," **Then** the status changes to "Submitted" and the DPR becomes read-only for the AD.

13. **Given** a "Submitted" DPR, **When** the UPM clicks "Approve," **Then** status changes to "Approved" and the approver's name and timestamp are recorded.

14. **Given** an "Approved" DPR, **When** the producer clicks "Lock," **Then** status changes to "Locked" and no further edits are possible by anyone.

15. **Given** a "Locked" DPR, **When** any user attempts to edit any field, **Then** the system prevents the edit and indicates the report is locked.

#### Variance & Analytics

16. **Given** 10 completed DPRs for a schedule, **When** the producer views the analytics dashboard, **Then** a burndown chart shows cumulative planned vs actual pages for all 10 days, and KPI cards show average pages/day, total delays, and a schedule health score.

17. **Given** delay data across multiple DPRs, **When** viewing analytics, **Then** a breakdown shows total delay minutes by category (Weather, Technical, Talent, etc.).

18. **Given** cumulative analytics data, **When** viewing the dashboard, **Then** a projected wrap date is calculated based on average pages/day velocity.

#### Export

19. **Given** a complete DPR (any status), **When** the AD clicks "Export PDF," **Then** a formatted PDF is generated containing all sections: header, scene progress, time sheets, department notes, incidents, delays, totals, and sign-offs.

20. **Given** a complete DPR, **When** the AD clicks "Print," **Then** a printable view opens in the browser with the same content as the PDF.

#### Multi-Unit

21. **Given** a shooting day with 1st Unit and 2nd Unit configured, **When** the AD creates a DPR for 1st Unit, **Then** only scenes assigned to 1st Unit appear as entries. A separate DPR can be created for 2nd Unit.

22. **Given** DPRs for both 1st Unit and 2nd Unit on the same day, **When** viewing the daily summary, **Then** analytics show both per-unit totals and combined totals for the shooting day.

23. **Given** a scene assigned to 1st Unit is marked "Not Shot," **When** 2nd Unit picks it up, **Then** the scene can appear as "Pickup" on 2nd Unit's DPR (cross-unit pickup).

#### Day Classification & Velocity

24. **Given** a DPR with day type "Company Move," **When** the AD files it with zero scenes and crew time only, **Then** the system accepts it and excludes it from pages/day velocity calculations.

25. **Given** 8 Shoot-day DPRs and 2 Company-Move DPRs, **When** viewing average pages/day, **Then** the calculation uses only the 8 Shoot days.

26. **Given** a Shoot-day DPR where the AD manually sets "include in velocity" to false, **When** viewing analytics, **Then** that day is excluded from velocity calculations.

#### Versioning

27. **Given** a Locked DPR (version 1), **When** the Line Producer clicks "Unlock for Correction," **Then** a new DPR version 2 is created in Draft status, version 1 is marked as superseded but remains immutable, and an audit entry is recorded.

28. **Given** a DPR version 2, **When** exported as PDF, **Then** the PDF header indicates "Version 2" and the footer references the original version.

#### Carryover

29. **Given** a DPR where scene 44 is marked "Not Shot" (planned 3 1/8 pages), **When** viewing the carryover summary, **Then** scene 44 shows as a carryover candidate with 3 1/8 pages flagged for rescheduling.

30. **Given** a DPR where scene 45 is marked "Partial" (1 2/8 of 2 6/8 pages shot), **When** viewing the carryover summary, **Then** scene 45 shows 1 4/8 remaining pages as a carryover candidate.

31. **Given** carryover candidates exist, **When** the AD views the next day's schedule, **Then** carryover flags are visible but scenes are NOT auto-added — the user decides whether to carry over or reschedule manually.

#### Attachments

32. **Given** a DPR incident log, **When** the AD uploads a photo of the incident location, **Then** the photo is attached to the incident, visible in the DPR, and included as a thumbnail in the PDF export.

33. **Given** a Camera department log, **When** the DIT uploads a screenshot of the checksum verification report, **Then** it is attached to the camera log entry.

#### Approval Configuration

34. **Given** a production configured in "Strict" approval mode with 5 required departments, **When** the AD tries to submit a DPR with only 3 departments submitted, **Then** the system blocks submission and indicates which departments are still pending.

35. **Given** a production configured in "Soft" approval mode, **When** the AD submits a DPR with 2 departments still pending, **Then** the system allows submission but shows a warning listing the pending departments.

#### Snapshots

36. **Given** a DPR was created with scene 42 planned at 2 3/8 pages, **When** the schedule is later changed to 3 1/8 pages for scene 42, **Then** the DPR still shows 2 3/8 as the planned baseline (snapshot preserved).

#### Notifications

37. **Given** a DPR status changes from Draft to Submitted, **When** the transition occurs, **Then** the Line Producer and Producer receive a notification.

### Edge Cases

- **Non-shoot days**: A DPR with day type "Company Move," "Travel," "Prep," "Dark," "Holiday," or "Strike" may have zero scene entries. The system allows filing with times, notes, and crew time only.
- **Duplicate DPR attempt (same unit)**: If a DPR already exists for a shooting day + unit combination, the system opens the existing DPR rather than creating a new one.
- **Scene on multiple days**: A scene can be "Partial" on Day 5 and "Pickup" on Day 8. Both DPRs reference the same scene with different statuses. Snapshot data is independent per DPR.
- **Scene across units**: A scene can be "Partial" on 1st Unit and "Pickup" on 2nd Unit on the same or different days (cross-unit pickup).
- **Schedule changes after DPR creation**: DPR scene entries remain as-is (snapshot at creation per AD-2). The user IS notified of the discrepancy. If the DPR is still in Draft, they can use "Re-sync with Schedule" (FR-053e) to update snapshots while preserving actual data. If Submitted/Approved/Locked, the original snapshot is preserved.
- **Correction after lock**: Unlocking creates a new version per AD-5. Only Line Producer or AD can initiate. The original version remains immutable. The correction is audit-logged.
- **No schedule exists**: If a user tries to access DPR without any shooting schedules, the system indicates that a schedule must be created first.
- **Carried scenes**: Scenes marked "Not Shot" do NOT auto-carry to the next day. They appear as carryover candidates (per AD-4). The user decides per scene whether to carry over or reschedule manually.
- **Version chain integrity**: If a superseded DPR (version N) is viewed, it displays a clear banner indicating it has been superseded by version N+1 with a link to the current version.
- **Attachment size limits**: If a user attempts to upload a file exceeding the configured max size, the system rejects the upload with a clear error message.
- **Approval mode conflict**: If approval mode is changed from Soft to Strict while a DPR is in Submitted status with pending departments, the DPR remains in Submitted status but cannot advance to Approved until departments comply.
- **Pre-lock correction** *(Rev 3)*: If a DPR is in Submitted status and a department log needs correction, the AD/LP reverts the DPR to Draft (FR-004a). No version is created. Department logs become editable again. This avoids version-chain pollution for minor pre-lock fixes.
- **Overnight wrap** *(Rev 3)*: Night shoots where call is 18:00 and wrap is 03:00 (next day) must calculate correctly as 9 hours. The system handles day-boundary crossings via date-time values or a "wrap next day" flag (FR-021b).
- **Actor on multiple units** *(Rev 4 — replaces Rev 3)*: If actor works on both 1st Unit and 2nd Unit same day, they MAY have time entries on both DPRs, each flagged as "Shared Resource" (FR-021c). Unit-level analytics keep entries separate; global/payroll totals de-duplicate by person ID.
- **Scene shot across multiple days inflating burndown** *(Rev 3)*: If scene 44 (3 pages) is partially shot on Day 5 (1 page) and picked up on Day 8 (2 pages), the schedule burndown counts 3 planned pages once (from the schedule), not twice from both DPR snapshots (FR-028a).
- **Strict mode on Travel day** *(Rev 3)*: If production is in Strict approval mode but day type is Travel with no Camera department, required departments are determined by day-type override (FR-086a). Camera log is not required for Travel days.
- **Stale analytics after edit** *(Rev 3)*: If a scene entry is updated after materialized metrics were computed, the metrics are invalidated and recomputed before serving analytics (FR-027b).
- **Stale snapshot in Draft DPR** *(Rev 4)*: DPR created at 06:00, schedule changed at 08:00 (scene added, pages changed). AD has already entered crew times. AD uses "Re-sync with Schedule" to update snapshots while preserving entered data. Removed scenes transition to "Added"; new scenes appear as "Not Shot" (FR-053e).
- **Department not on set** *(Rev 4)*: VFX is a required department in Strict mode, but VFX did not work today. AD marks VFX log as "N/A" with reason "VFX not on set today" (FR-014a). This satisfies Strict mode without forcing VFX HOD to submit an empty form.
- **Over-shot scene (negative carryover)** *(Rev 4)*: Scene planned for 2 pages, actually shot 2.5 pages. Carryover = Max(0, 2−2.5) = 0 (no carryover). The 0.5 surplus is tracked as Page Gain in analytics (FR-074a). Scheduler sees zero carryover for this scene.
- **Downloaded PDF becomes superseded** *(Rev 4)*: User downloads DPR_Day4_v1.pdf, saves locally. Later v2 is created. The PDF footer contains a QR code / deep link labeled "Verify latest version status" that resolves to the canonical version check page (FR-031a).
- **Splinter unit inflating velocity** *(Rev 4)*: 3rd Unit runs for 1 week of a 10-week shoot. Combined velocity spikes to 12 pgs/day during that week. Projected Wrap Date uses Main Unit Velocity by default (FR-073a), preventing distorted projections.
- **Remote location with no connectivity** *(Rev 4)*: AD wraps in a desert location with Edge/3G only. They switch to Low Bandwidth / Text-Only mode (FR-043a), disabling image uploads and heavy UI. DPR text data transmits as lightweight JSON. Attachments uploaded later at hotel with WiFi.

---

## Requirements

### Functional Requirements — Core DPR

- **FR-001**: System MUST allow creating exactly one Daily Production Report **per shooting day per unit**. Multiple units on the same day each have their own DPR. *(Updated per AD-1)*
- **FR-002**: When a DPR is created, the system MUST auto-populate scene entries from the shooting day's planned schedule **for the selected unit**, each defaulting to "Not Shot" status with **snapshot data** pre-filled (see FR-053–FR-056). *(Updated per AD-1, AD-2)*
- **FR-003**: System MUST allow recording general shoot-day information: call time, first shot time, lunch break start/end, camera wrap time, company wrap time, weather conditions, **day type classification (per AD-3)**, and general notes.
- **FR-004**: System MUST enforce a status workflow: **Draft → Submitted → Approved → Locked**. Transitions must be forward-only under normal operation. Reverse transitions (unlock) follow the versioning protocol (see FR-065–FR-070).
- **FR-004a** *(Rev 3 Gap Fix #1)*: The system MUST allow a **Submitted → Draft** reversion (by AD or Line Producer only) WITHOUT creating a new version. This enables minor pre-lock corrections. The reversion is audit-logged. Department logs become editable again upon reversion to Draft. Versioning (version chain creation) ONLY applies once a DPR has reached Locked status.
- **FR-005**: System MUST treat a Locked DPR as **immutable**. To make corrections, an authorized user creates a new version per the versioning protocol (AD-5). The original locked version is never modified.
- **FR-006**: System MUST record an audit trail of all status transitions and version events (who, when, what changed).

### Functional Requirements — Scene Progress

- **FR-007**: System MUST allow updating each scene entry's status to one of: **Complete**, **Partial**, **Not Shot**, **Added**, or **Pickup**.
- **FR-008**: System MUST allow recording per-scene actual data: pages shot (in eighths of a page), number of setups, number of takes, circle takes, start/end times, and free-text notes.
- **FR-009**: System MUST allow adding scenes not originally on the day's schedule, automatically marked as "Added." Added scenes have no planned baseline and do not affect carryover calculations.
- **FR-010**: System MUST display the **snapshot** planned page count alongside actual page count for each scene, with a visual variance indicator (ahead/behind). *(Updated per AD-2)*
- **FR-011**: System MUST compute and display daily totals: scenes shot (by status), total pages shot, total setups, total takes, and net page variance vs planned. For multi-unit days, both per-unit and combined-day totals MUST be available.

### Functional Requirements — Department Logs

- **FR-012**: System MUST allow department representatives to submit structured logs for their department. Supported department types: Camera, Sound, Script Supervisor, Art, Costume, Makeup, Locations, VFX, Stunts, Transport, and General.
- **FR-013**: Each department log type MUST have a defined data structure appropriate to that department:
  - **Camera** *(expanded per AD-6)*: Media/card identifier, roll number, codec, resolution, checksum (for verification), offload destination, offload completion timestamp, verified-by person, LTO backup completed flag, LTO backup verification timestamp, lenses used
  - **Sound**: Sound rolls, format, microphones used, sync notes, issues
  - **Script Supervisor**: Circle takes per scene, dialogue changes, continuity notes, coverage notes
  - **General** (all others): Free-form notes
- **FR-014**: Department logs MUST track submission status (Pending, Submitted, or **Not Applicable**) and who submitted or marked them.
- **FR-014a** *(Rev 4 Gap Fix #3)*: The AD or Line Producer MUST be able to mark a required department's log as **"Not Applicable Today" (N/A)** with a mandatory reason text (e.g., "VFX not on set today"). N/A status satisfies Strict mode approval requirements. Only the AD or Line Producer can set N/A status, not the department HOD.
- **FR-015**: The DPR summary MUST show a department submission tracker indicating which departments have submitted and which are pending.
- **FR-015a** *(Gap Fix #7)*: Department logs MUST follow an editability lifecycle tied to DPR status:
  - **Draft** → Logs are fully editable by the department HOD
  - **Submitted** → Logs are frozen; no edits allowed by HOD (only AD/Line Producer can request reversion to Draft)
  - **Approved / Locked** → Logs are immutable
  This is critical for Camera data integrity fields (checksums, LTO verification) which lose meaning if editable after submission.

### Functional Requirements — Time Tracking

- **FR-016**: System MUST allow recording time entries for **cast** members: person name, character name, call time, on-set time, wrap time, first meal break, second meal break, travel hours, and notes.
- **FR-017**: System MUST allow recording time entries for **crew** members: person name, department/role, call time, wrap time, meal breaks, travel hours, and notes.
- **FR-018**: System MUST auto-calculate total hours worked and overtime hours from recorded times.
- **FR-019**: System MUST flag meal penalty conditions when applicable. Meal penalty rules (break duration thresholds, penalty triggers) MUST be **configurable per production** to accommodate different union agreements and jurisdictions.
- **FR-020**: System MUST flag forced call conditions when applicable. Forced call turnaround thresholds (e.g., <10h or <12h between wrap and next call) MUST be **configurable per production**.
- **FR-021**: System MUST support pre-populating cast time entries from the characters scheduled for that day's scenes.
- **FR-021a** *(Gap Fix #6)*: DPR time tracking is **informational only, NOT payroll-authoritative**. The system does not store pay rates, union categories, or tier rules. Time data is intended for production coordination and daily reporting purposes. Any payroll integration is explicitly out of scope. This disclaimer MUST be visible in the time tracking UI and included in the PDF export footer.
- **FR-021b** *(Rev 3 Gap Fix #5)*: Time entries MUST support **overnight wraps** (call on one date, wrap on the next). The system MUST either use full date-time values for call/wrap fields or provide an explicit "wrap next day" flag. Hour calculations MUST correctly handle day-boundary crossings (e.g., call 18:00, wrap 03:00 = 9 hours, not negative).
- **FR-021c** *(Rev 4 Gap Fix #2 — replaces Rev 3 Gap Fix #6)*: In multi-unit productions, a cast or crew member MAY have time entries on **multiple unit DPRs** for the same shooting day if they work across units. Each such entry MUST be flagged as a **"Shared Resource"** entry. When aggregating for **global/payroll totals**, the system MUST de-duplicate shared resource entries by person ID (using the longest span or summing non-overlapping segments). When viewing **unit-level analytics**, shared resource entries are kept separate to reflect actual per-unit labor allocation. This prevents both data loss (primary-unit-only attribution) and double-counting (naive summing).

### Functional Requirements — Incidents & Delays

- **FR-022**: System MUST allow logging production delays with: type (Weather, Technical, Talent, Location, Medical, Meal Penalty, Company Move, Other), duration in minutes, description, and optional scene association.
- **FR-023**: System MUST compute total delay minutes and a breakdown by delay type for each DPR.
- **FR-024**: System MUST allow logging health & safety incidents with: type (Injury, Near Miss, Safety Violation, Equipment Damage), severity (Minor, Moderate, Serious, Critical), description, location, time, persons involved, witnesses, action taken, and follow-up requirements.
- **FR-025**: Incidents with severity "Serious" or "Critical" MUST require follow-up notes to be recorded.

### Functional Requirements — Variance & Analytics

- **FR-026**: System MUST compute per-day variance using **snapshot** planned data (per AD-2) including: planned scene count vs actual scene count (by status), planned pages vs actual pages (in eighths), variance percentage, total setups, total takes, and total delay minutes. For multi-unit days, variance MUST be available per unit and combined.
- **FR-026a** *(Gap Fix #2)*: Combined-day variance MUST be computed by summing planned snapshots across all units for that day and summing actual pages across all units, then computing net variance once from these combined sums. Per-unit variances MUST NOT be summed to derive combined-day variance (which would double-count cross-unit pickups).
- **FR-027**: System MUST compute cumulative production analytics across all DPRs for a schedule: total pages shot to date, average pages per day **(using only DPRs where include_in_velocity = true, per AD-7)**, projected remaining shoot days, and projected wrap date.
- **FR-027a** *(Gap Fix #9)*: For MVP, the system SHOULD maintain **materialized daily metrics** per DPR (pre-computed totals for pages, setups, takes, delays, variance) rather than computing all analytics dynamically on every request. This avoids performance degradation from multi-unit aggregation, snapshot joins, velocity filtering, delay grouping, and version filtering (canonical only) at query time.
- **FR-027b** *(Rev 3 Gap Fix #7)*: Materialized metrics MUST be recomputed (invalidated) when any of the following events occur: scene entry created/updated/deleted, delay added/edited/deleted, DPR version created (new canonical), include_in_velocity flag changed, DPR status changes affecting canonical status. Stale metrics MUST never be served to analytics consumers.
- **FR-028**: System MUST display a production burndown visualization showing cumulative planned pages vs cumulative actual pages over time. Analytics MUST aggregate at three levels: per unit, per shooting day (combined units), and per schedule (per AD-1).
- **FR-028a** *(Rev 3 Gap Fix #2)*: Schedule-level cumulative burndown MUST derive the planned baseline from **unique scene planned pages in the schedule** (each scene counted once, from its original schedule assignment), NOT from the sum of per-DPR snapshot planned pages. Actual pages are summed across all canonical DPRs. This prevents baseline inflation when a scene is partially shot across multiple days or units.
- **FR-029**: Schedule health score is **deferred to post-MVP**. The analytics dashboard reserves a placeholder for this metric.
- **FR-030**: System MUST display a delay analysis view showing total delay minutes broken down by category across all shoot days.

### Functional Requirements — Export & Distribution

- **FR-031**: System MUST generate a formatted PDF of the DPR including all sections: header/conditions, scene progress table with variance, cast time sheets, crew summary, department log notes, incidents, delays, daily totals, cumulative totals, and sign-off block.
- **FR-031a** *(Rev 4 Gap Fix #5)*: Every generated PDF MUST include a **verification link** (QR code and/or deep link URL) in the footer, explicitly labeled "Verify latest version status." This link resolves to the DPR's canonical version status page, allowing a holder of a printed or locally saved PDF to instantly verify whether the document is still the current canonical record. This supports insurance, bonding, and legal audit workflows.
- **FR-032**: The PDF MUST follow industry-standard DPR layout conventions.
- **FR-033**: System MUST provide a printable browser view of the DPR with the same content as the PDF.
- **FR-034**: System MUST allow sharing completed DPRs with external stakeholders using the **existing shareable-link mechanism** (token-based, with configurable expiry). Future: Telegram/WhatsApp conversational integration.

### Functional Requirements — Sign-Off

- **FR-035**: System MUST allow authorized users to digitally sign off on a DPR, recording their name, role, and timestamp.
- **FR-036**: Multiple sign-offs MUST be supported on a single DPR (e.g., 2nd AD, UPM, Producer).
- **FR-037**: All sign-offs MUST be displayed on the DPR summary view and included in the PDF export.
- **FR-037a** *(Rev 3 Gap Fix #8)*: When a new DPR version is created, the audit trail of the new version MUST include the previous version's signatories, their timestamps, and the reason for correction. This historical sign-off data MUST be accessible in the version's audit view and optionally included in the PDF for forensic traceability.

### Functional Requirements — Access & Permissions

- **FR-038**: System MUST restrict DPR creation to **AD and Line Producer** roles.
- **FR-039**: System MUST restrict DPR approval to **Line Producer and AD** roles.
- **FR-040**: System MUST restrict DPR locking to **Line Producer and AD** roles.
- **FR-041**: Department HODs MUST only be able to edit their own department's log, not other departments' logs or the main DPR fields. *(Confirmed)*

### Functional Requirements — Usability

- **FR-042**: System MUST auto-save DPR data as a draft while the user is editing, without requiring a manual save action.
- **FR-043**: System MUST be usable on tablet devices with touch-optimized inputs (minimum 44px touch targets, native time pickers, toggle controls).
- **FR-043a** *(Rev 4 Gap Fix #7)*: System MUST provide a **Low Bandwidth / Text-Only mode** that disables image uploads, attachment previews, and heavy UI elements, allowing the DPR text data payload (JSON) to be transmitted over weak Edge/3G connections. This mode MUST be user-selectable and MUST preserve full data entry capability (scene progress, times, logs, notes). Attachments can be uploaded later when connectivity improves.
- **FR-044**: System MUST be accessible from the existing shooting schedule interface (e.g., a "File DPR" action on each shooting day).
- **FR-045**: System MUST clearly indicate when a shooting day + unit combination already has a DPR and allow navigating directly to it.

### Functional Requirements — Integration

- **FR-046**: Each DPR MUST be linked to its corresponding shooting day **and unit** in the schedule.
- **FR-047**: System MUST use the shooting day's planned scene list **for the selected unit** as the baseline for the DPR's scene entries, storing snapshots at creation time.
- **FR-048**: System MUST only allow DPR creation for shooting days that belong to an active schedule.
- **FR-049**: Scenes marked "Not Shot" MUST NOT auto-carry forward. They appear as **carryover candidates** (per AD-4). The user decides per scene whether to carry over to the next day or reschedule manually. Future: schedule suggestions based on scene variables.
- **FR-050**: DPR status changes (Submitted, Approved, Locked) MUST **trigger notifications** to relevant team members (Line Producer, Producer).
- **FR-051**: The DPR MUST support **file attachments** (photos, documents) on DPR-level, Incidents, Department Logs, and Scene Entries (per AD-8).
- **FR-052**: The system MUST support **multiple shooting units per day**, each with their own DPR. Units are customizable per production (per AD-1).

### Functional Requirements — Planned Data Snapshots *(NEW — per AD-2)*

- **FR-053**: When a DPR is created, each scene entry MUST store a **snapshot** of the scene number at that point in time.
- **FR-053a** *(Gap Fix #5)*: Each scene entry MUST store a **snapshot** of the scene heading / slugline at DPR creation time.
- **FR-053b** *(Gap Fix #5)*: Each scene entry MUST store a **snapshot** of INT/EXT at DPR creation time.
- **FR-053c** *(Gap Fix #5)*: Each scene entry MUST store a **snapshot** of the location name at DPR creation time.
- **FR-053d** *(Gap Fix #5)*: Each scene entry MUST store a **snapshot** of Day/Night (time of day) at DPR creation time.
- **FR-054**: Each scene entry MUST store a **snapshot** of the planned page count (in eighths) at DPR creation time.
- **FR-055**: Each scene entry MUST store a **snapshot** of the planned schedule order at DPR creation time.
- **FR-056**: Each scene entry MUST store a **snapshot** of the planned unit assignment at DPR creation time.
- **FR-057**: All variance and analytics computations MUST use snapshot values, NOT live scene/schedule data.
- **FR-053e** *(Rev 4 Gap Fix #1)*: System MUST provide a **"Re-sync with Schedule"** action available only for **Draft** DPRs. This action updates all snapshot values to match the current schedule state while preserving any entered actual data (pages, takes, setups, times, logs, attachments). Scenes removed from the schedule transition to "Added" status (preserving any entered data). Scenes newly added to the schedule create new entries with "Not Shot" status and fresh snapshots. Re-sync is NOT available for Submitted, Approved, or Locked DPRs.

### Functional Requirements — Multi-Unit *(NEW — per AD-1)*

- **FR-058**: System MUST allow productions to define and manage units (e.g., 1st Unit, 2nd Unit, Splinter Unit). Unit configuration is customizable per production.
- **FR-059**: When creating a DPR, the user MUST select which unit the DPR is for.
- **FR-060**: Analytics MUST aggregate data at three levels: per unit, per shooting day (all units combined), and per schedule.
- **FR-060a** *(Gap Fix #2)*: Combined shooting-day aggregation MUST sum planned snapshots and actual pages independently across all units for that day, computing net variance from the combined sums. Cross-unit pickups are resolved at this aggregation level — a scene's planned baseline belongs to the unit originally assigned.
- **FR-061**: Cross-unit pickups MUST be supported: a scene marked "Not Shot" or "Partial" on one unit's DPR can appear as "Pickup" on another unit's DPR.

### Functional Requirements — Day Classification *(NEW — per AD-3)*

- **FR-062**: Each DPR MUST have a **day type** field with values: Shoot, Company Move, Prep, Travel, Holiday, Dark, Strike.
- **FR-063**: DPRs with day type other than "Shoot" MUST allow zero scene entries (times, notes, crew time only).
- **FR-064**: Velocity calculations (average pages/day, projected wrap date) MUST include **only Shoot-type days** by default.

### Functional Requirements — DPR Versioning *(NEW — per AD-5)*

- **FR-065**: When an authorized user (Line Producer or AD) initiates "Unlock for Correction" on a Locked DPR, the system MUST create a **new version** (clone) of the DPR in Draft status.
- **FR-066**: The original Locked version MUST be marked as **superseded** but remain **immutable** and accessible.
- **FR-067**: Each DPR version MUST record: version number, reference to parent version (if any), and locked timestamp.
- **FR-068**: The latest non-superseded version is the **canonical record** for analytics and reporting. *(Rev 3 Gap Fix #3)*: ALL analytics computations — velocity, burndown, delay aggregation, cumulative totals, materialized metrics — MUST use only canonical versions. Superseded versions MUST be excluded from all aggregate calculations. This includes the include_in_velocity flag: only the canonical version's flag value is considered.
- **FR-069**: PDF exports MUST indicate the DPR version number in the header. If superseded, the PDF MUST note which version replaced it.
- **FR-070**: Viewing a superseded version MUST display a clear banner linking to the current canonical version.
- **FR-070a** *(Gap Fix #1)*: When creating a new version, the system MUST **clone as-is**: scene entries (with all snapshot data), department logs (preserving their submission status), time entries, delays, incidents, and attachment references.
- **FR-070b** *(Gap Fix #1)*: When creating a new version, the system MUST **reset**: DPR status to Draft, all sign-offs (cleared), approval timestamps (cleared), locked_at timestamp (null).
- **FR-070c** *(Gap Fix #1)*: When creating a new version, department logs MUST retain their existing submission state (Submitted remains Submitted). Logs are NOT reset to Pending. This preserves department work while requiring re-approval of the overall DPR.

### Functional Requirements — Velocity Logic *(NEW — per AD-7)*

- **FR-071**: Each DPR MUST have an **include in velocity** flag. Defaults to true for Shoot-type days, false for all other day types.
- **FR-072**: The include-in-velocity flag MUST be manually overridable by AD or Line Producer (e.g., to exclude an abnormal shoot day).
- **FR-073**: Average pages/day MUST be calculated as: Sum(actual pages where include_in_velocity = true) / Count(**distinct shooting days** where at least one included DPR exists). *(Gap Fix #3)*: The denominator is distinct shooting days, NOT DPR record count. Multi-unit days with 3 DPRs count as 1 day.
- **FR-073a** *(Rev 4 Gap Fix #6)*: Velocity analytics MUST provide two separate metrics: **Main Unit Velocity** (pages/day for the designated main unit only) and **Combined Velocity** (pages/day across all units). **Projected Wrap Date** MUST default to Main Unit Velocity. Production admin MAY configure the projection to use Combined Velocity instead. This prevents temporary splinter units from distorting long-term projections.

### Functional Requirements — Carryover *(NEW — per AD-4)*

- **FR-074**: System MUST compute **carryover pages** per DPR as: **Max(0, Planned Pages − Actual Pages)**, where Planned = sum of snapshot planned eighths, Actual = sum of actual eighths for Complete + Partial entries. *(Rev 4 Gap Fix #4)*: Negative carryover (over-shooting) MUST NOT be presented to the scheduler. Over-shot pages are tracked separately as **"Page Gain"** for analytics purposes.
- **FR-074a** *(Rev 4 Gap Fix #4)*: When actual pages exceed planned snapshot for a scene (over-shooting), the system MUST track the surplus as **Page Gain** (Actual − Planned). Page Gain is displayed in analytics as a positive indicator but does NOT reduce carryover on other scenes.
- **FR-075**: Scenes with status "Partial" MUST show remaining pages as Max(0, planned snapshot − actual) as carryover candidates.
- **FR-076**: Scenes with status "Not Shot" MUST show full planned snapshot as carryover candidates.
- **FR-077**: Scenes with status "Added" MUST NOT affect carryover calculations (no planned baseline).
- **FR-078**: Carryover candidates MUST be surfaced as flags in the scheduling module but MUST NOT auto-reschedule.

### Functional Requirements — Attachments *(NEW — per AD-8)*

- **FR-079**: System MUST allow uploading file attachments to: DPR (general), Incidents, Department Logs, and Scene Entries.
- **FR-080**: Each attachment MUST record: file URL, file type, file size, uploader, and upload timestamp.
- **FR-081**: Maximum file size per upload MUST be configurable per production.
- **FR-082**: Uploaded images MUST be auto-compressed for storage efficiency.
- **FR-083**: File access MUST use signed URLs with limited expiry for security.
- **FR-084**: In PDF exports, attachments MUST be included as optional thumbnails only.
- **FR-085**: When a DPR is versioned (per AD-5), the new version MUST copy **attachment references** (pointers to the canonical file record), NOT duplicate the binary files. *(Gap Fix #8)*: This prevents storage explosion across version chains.

### Functional Requirements — Approval Configuration *(NEW — per AD-9)*

- **FR-086**: System MUST allow production admins to configure approval mode: **Strict**, **Soft**, or a custom configuration.
- **FR-086a** *(Rev 3 Gap Fix #4)*: The list of required departments MUST be configurable at two levels: **per production** (default required departments) and **per day type** (overrides for specific day types). Non-shoot day types (Company Move, Travel, Prep, etc.) may have reduced or no required departments.
- **FR-087**: In **Strict mode**, the system MUST block DPR submission/approval if required departments **(as determined by the DPR's day type)** have not submitted their logs or been marked as **N/A** (per FR-014a). A department marked N/A satisfies the Strict mode requirement.
- **FR-088**: In **Soft mode**, the system MUST allow DPR submission/approval with pending departments but display a warning listing which departments are still pending.
- **FR-089**: The approval mode configuration MUST be changeable at any time. *(Gap Fix #4)*: Mode changes apply **only to future submissions**. DPRs already in Submitted, Approved, or Locked status retain their current state and are not retroactively invalidated.

### Functional Requirements — Notifications *(NEW)*

- **FR-090**: System MUST send notifications to Line Producer and Producer when a DPR status changes to Submitted.
- **FR-091**: System MUST send notifications to the DPR author when their DPR is Approved or Locked.
- **FR-092**: System MUST notify the AD when the schedule changes after a DPR has been created for that shooting day (per resolved clarification #13).
- **FR-092a** *(Rev 3 Gap Fix #10)*: A **material schedule change** that triggers notification is defined as: scene added to or removed from the day, scene's planned page count changed, scene's unit assignment changed. Non-material changes (e.g., scene reorder within the same day, notes updated) MUST NOT trigger notifications.

### Functional Requirements — Data Validation Rules *(NEW — Gap Fix #10)*

- **FR-093**: Actual pages for a scene with status "Complete" MUST be greater than zero.
- **FR-094**: Actual pages for a scene with status "Partial" MUST be greater than zero AND less than the planned snapshot page count.
- **FR-095**: Actual pages for a scene with status "Not Shot" MUST be zero.
- **FR-096**: A scene with status "Added" MUST allow any actual page count (including zero) since there is no planned baseline.
- **FR-097**: Actual pages for a scene with status "Complete" MAY exceed the planned snapshot (a scene can run longer than scripted). The system MUST display a visual indicator when actual exceeds planned but MUST NOT block the entry.
- **FR-098**: A scene entry with status "Complete" or "Partial" MUST have at least one take recorded. Setups SHOULD be at least 1 but MAY be 0 with a warning (to accommodate VFX-only pickups, archival footage inserts, or montage elements where traditional setups don't apply). *(Rev 3 Gap Fix #9)*
- **FR-099**: A DPR MUST NOT be submitted (transition from Draft to Submitted) if it contains scene entries with inconsistent data (e.g., status "Complete" with zero pages, status "Not Shot" with non-zero pages).

---

## Key Entities

- **Unit** *(NEW — per AD-1)* — A shooting unit within a production (e.g., 1st Unit, 2nd Unit, Splinter Unit). Customizable per production. Sits between Shooting Day and DPR in the hierarchy. A shooting day can have multiple units, each with its own DPR.

- **Daily Production Report** *(Updated)* — The master record for a single shoot day **for a single unit**. Contains general information (call/wrap times, weather, notes), **day type classification** (Shoot, Company Move, Prep, Travel, Holiday, Dark, Strike), computed totals, status (Draft/Submitted/Approved/Locked), sign-offs, **version number**, **include-in-velocity flag**, and **approval mode** reference. Exactly one per shooting day per unit. Belongs to one shooting schedule. Supports an **immutable version chain** for corrections after Locked (per AD-5). **Pre-lock corrections** use Submitted→Draft reversion without versioning *(Rev 3 Gap Fix #1)*. Draft DPRs support **"Re-sync with Schedule"** to update stale snapshots *(Rev 4 Gap Fix #1)*.

- **Scene Entry** *(Updated)* — A record of what happened with a specific scene on a specific shoot day. Contains status (Complete/Partial/Not Shot/Added/Pickup), actual page count (in eighths), setups, takes, circle takes, times, and notes. Belongs to one DPR. References one scene from the script. **Stores snapshot data at creation time** (per AD-2): scene number, **scene heading/slugline, INT/EXT, location name, Day/Night** *(Gap Fix #5)*, planned page count in eighths, planned schedule order, and planned unit assignment. Snapshots can be **re-synced** while DPR is in Draft status *(Rev 4 Gap Fix #1)*. All variance computations use these snapshots. **Subject to data validation rules** (FR-093–FR-099) that enforce consistency between status and page count.

- **Department Log** *(Updated)* — A structured submission from a specific department for a shoot day. The data structure varies by department type. **Camera logs include extended data integrity verification fields** (per AD-6): media ID, checksum, offload status, LTO backup verification. Tracks submission status (Pending, Submitted, or **Not Applicable** *(Rev 4 Gap Fix #3)*) and author. Belongs to one DPR and one department. May have **attachments**. **Follows editability lifecycle** *(Gap Fix #7)*: editable in Draft, frozen at Submitted, immutable at Approved/Locked. AD/LP can mark as N/A with mandatory reason.

- **Time Entry** — A record of a person's working hours for a shoot day. Applies to both cast (with character name) and crew (with department/role). Contains call/set/wrap times (with **date-time or wrap-next-day flag** for overnight shoots *(Rev 3 Gap Fix #5)*), break times, calculated hours, overtime, flags (meal penalty, forced call), and **shared resource flag** *(Rev 4 Gap Fix #2)*. **Meal penalty and forced call thresholds are configurable per production.** Belongs to one DPR. A person MAY have entries on multiple unit DPRs if flagged as shared resource; global totals de-duplicate by person ID. **Time tracking is informational only, NOT payroll-authoritative** *(Gap Fix #6)* — does not store pay rates, union categories, or tier rules.

- **Incident** — A health & safety event recorded during a shoot day. Contains type, severity, description, persons involved, witnesses, action taken, and follow-up information. Belongs to one DPR. May have **attachments** (per AD-8).

- **Delay** — A production delay recorded during a shoot day. Contains type category, duration, description, and impact. Optionally linked to a specific scene. Belongs to one DPR.

- **Attachment** *(NEW — per AD-8)* — A file (photo, document) linked to a DPR, Incident, Department Log, or Scene Entry. Records file URL, file type, file size, uploader, and upload timestamp. Images are auto-compressed. Access via signed URLs. When a DPR is versioned, **attachment references are copied (not binary files)** *(Gap Fix #8)* to prevent storage explosion. Included as optional thumbnails in PDF exports.

- **Variance** (derived) — A computed comparison between planned and actual data for a shoot day, **using snapshot values** (per AD-2). Includes scene count deltas, page count deltas, percentage variance, **carryover pages** (clamped to ≥0 per AD-4 *(Rev 4 Gap Fix #4)*), and **page gain** (actual exceeding planned). Calculated on demand. Available per unit and per combined day.

- **Production Analytics** (derived) — Cumulative metrics across all **canonical** DPRs for a schedule *(Rev 3 Gap Fix #3)*. Includes burndown data (with **schedule-level planned baseline from unique scene pages** *(Rev 3 Gap Fix #2)*), average rates split into **Main Unit Velocity** and **Combined Velocity** *(Rev 4 Gap Fix #6)* (using **velocity inclusion logic** per AD-7 with **distinct-day denominator** *(Gap Fix #3)*, **Shoot days only** per AD-3), projections (defaulting to Main Unit Velocity), delay summaries. **Aggregated at three levels**: per unit, per shooting day (combined units using **combined-sum aggregation** *(Gap Fix #2)*), per schedule. Health score deferred to post-MVP. **MVP uses materialized daily metrics** with **explicit invalidation triggers** *(Rev 3 Gap Fix #7)* for performance.

---

## Assumptions & Dependencies

### Assumptions
- A shooting schedule with shooting days and assigned scenes already exists before DPR can be created.
- Scene page lengths (in eighths) are already computed from the script breakdown.
- The existing department taxonomy (Camera, Sound, Art, etc.) will be reused for department logs.
- The existing team membership model will be extended to support DPR-specific permissions (AD, Line Producer, HOD, Producer, Accounting).
- Productions will configure their units, meal penalty rules, forced call thresholds, and approval mode during production setup.
- Snapshot data is immutable once a DPR leaves Draft status. **Draft DPRs** support a "Re-sync with Schedule" action that updates snapshots while preserving actual data *(Rev 4 Gap Fix #1)*.
- DPR time tracking is informational, not payroll-authoritative. Productions must not rely on DPR time data for payroll compliance without independent verification.

### Dependencies
- **Shooting Schedule module** — Provides the planned baseline (shooting days, scene assignments, planned page counts). Must be extended to support unit assignments.
- **Scene Breakdown module** — Provides scene metadata (setting, INT/EXT, time of day, page length, characters) for snapshot capture.
- **Department system** — Provides department taxonomy and user-department membership.
- **Team system** — Provides script membership and roles for permission checks.
- **Report/PDF engine** — Provides PDF generation capability for DPR export. Must support versioned output and **QR code / verification link generation** *(Rev 4 Gap Fix #5)*.
- **Notification system** — Required for DPR status change notifications (FR-090–FR-092).
- **Object storage** — Required for attachment file storage with signed URL access (FR-079–FR-085).

---

## Scope Boundaries

### In Scope
- DPR creation, editing, and workflow (Draft → Submitted → Approved → Locked)
- **Multi-unit support** — One DPR per shooting day per unit (AD-1)
- Scene-by-scene progress tracking with **snapshot-based** planned vs actual variance (AD-2)
- **Day type classification** (Shoot, Company Move, Prep, Travel, Holiday, Dark, Strike) (AD-3)
- **Carryover pages** computation with user-driven rescheduling (AD-4)
- **Immutable version chain** for locked DPR corrections (AD-5)
- Department log submissions, including **camera data integrity verification** (AD-6)
- **Velocity inclusion logic** with manual override flag (AD-7)
- **File attachments** on DPR, Incidents, Department Logs, Scene Entries (AD-8)
- **Configurable approval mode** (Strict / Soft) per production (AD-9)
- Cast and crew time tracking with **configurable** meal penalty and forced call rules
- Incident and delay logging
- Per-day and cumulative variance computation with **three-level aggregation** (unit, day, schedule)
- Production analytics dashboard (burndown, KPIs, delay analysis)
- Versioned PDF export and printable view
- Digital sign-off
- **Notifications** on DPR status changes and **material** schedule discrepancies
- **Department log editability lifecycle** — Draft (editable), Submitted (frozen), Approved/Locked (immutable)
- **Pre-lock Submitted→Draft reversion** without versioning
- **Data validation rules** for scene entry status/page consistency (FR-093–FR-099)
- **Materialized daily metrics** per DPR with explicit invalidation triggers
- **Overnight wrap support** in time tracking
- **Shared resource time attribution** across multi-unit DPRs with de-duplication
- **Required departments configurable per day type** for approval enforcement
- **Department log N/A status** for Strict mode deadlock resolution
- **Schedule-level burndown** from unique scene planned baseline
- **Sign-off audit trail** preserved across version chain
- **Snapshot re-sync** for Draft DPRs when schedule changes
- **PDF verification link** (QR code / deep link) for version traceability
- **Main Unit vs Combined Velocity** analytics with configurable projection basis
- **Carryover clamped to ≥0** with separate Page Gain tracking
- **Low Bandwidth / Text-Only mode** for remote locations with weak connectivity

### Out of Scope (Future Features)
- **Call Sheet generation** — Inverse of DPR; planning what *will* happen tomorrow
- **Wrap Reports** — End-of-production compilation from all DPRs
- **Budget/cost tracking** — Financial projections from time sheet data (time tracking is informational only)
- **Payroll compliance** — Pay rates, union categories, tier rules
- **Post-production handoff** — Circle takes and continuity notes flowing to editorial
- **Offline support with sync** — Storing data locally when offline and syncing later
- **Real-time multi-user collaboration** — Multiple users editing the same DPR simultaneously
- **Schedule health score formula** — Deferred to post-MVP (placeholder reserved)
- **Full DIT/LTO workflow engine** — MVP captures integrity metadata only
- **Auto-scheduling of carryover scenes** — Carryover flags only; scheduling remains manual
- **Telegram/WhatsApp distribution** — Future conversational integration for DPR sharing

---

## Resolved Decisions Summary

All 14 original clarifications have been resolved. One additional decision (approval requirements) was added during architecture review.

| # | Question | Resolution | Spec Impact |
|---|----------|------------|-------------|
| 1 | Which roles can **create** a DPR? | AD and Line Producer | FR-038, Permission Matrix |
| 2 | Which roles can **approve** a DPR? | Line Producer, AD | FR-039, Permission Matrix |
| 3 | Which roles can **lock** a DPR? | Line Producer, AD | FR-040, Permission Matrix |
| 4 | Can department HODs edit **only their own log**? | Yes — HODs edit only their own department's log | FR-041 |
| 5 | What are the **meal penalty rules**? | Configurable per production (union-dependent) | FR-019 |
| 6 | What constitutes a **forced call**? | Configurable turnaround hours per production | FR-020 |
| 7 | What formula determines the **schedule health score**? | Deferred to post-MVP | FR-029 |
| 8 | Should "Not Shot" scenes **carry forward**? | User decides per scene; no auto-reschedule (AD-4) | FR-049, FR-074–FR-078 |
| 9 | Should status changes **trigger notifications**? | Yes | FR-050, FR-090–FR-092 |
| 10 | Should DPRs support **photo attachments**? | Yes (AD-8) | FR-051, FR-079–FR-085 |
| 11 | Should the system support **multiple units**? | Yes — customizable per production (AD-1) | FR-001, FR-052, FR-058–FR-061 |
| 12 | Can a **locked DPR be unlocked**? | Yes — via immutable version chain (AD-5) | FR-005, FR-065–FR-070 |
| 13 | **Notify on schedule discrepancy** after DPR creation? | Yes | FR-092 |
| 14 | How should DPRs be **shared**? | Existing shareable-link; future: Telegram/WhatsApp | FR-034 |
| 15 | **Approval requirements** with pending departments? | Configurable per production: Strict / Soft (AD-9) | FR-086–FR-089 |

---

## Review & Acceptance Checklist

### Content Quality
- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed
- [x] Architecture Decisions section documents all resolved decisions

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain — **All 15 resolved (Rev 1)**
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified
- [x] Permission matrix defined
- [x] Logic gaps addressed (10 gap fixes applied in Rev 2)
- [x] Operational edge cases resolved (10 gap fixes applied in Rev 3)
- [x] State synchronization & attribution fixes (7 gap fixes applied in Rev 4)
- [x] Data validation rules defined
- [x] Cross-unit aggregation logic specified
- [x] Velocity denominator corrected
- [x] Pre-lock reversion mechanism defined
- [x] Overnight wrap handling specified
- [x] Multi-unit time attribution (shared resource model) defined
- [x] Materialized metrics invalidation triggers defined
- [x] Schedule change notification materiality defined
- [x] Snapshot re-sync mechanism for Draft DPRs defined
- [x] Department log N/A status for Strict mode defined
- [x] PDF verification link for version traceability defined
- [x] Main Unit vs Combined velocity separation defined
- [x] Carryover math corrected (Max 0, Page Gain tracking)
- [x] Low bandwidth mode for remote connectivity defined

---

## Execution Status

- [x] User description parsed
- [x] Key concepts extracted (6 actors, 10 actions, 11 entities, 5 constraints)
- [x] Ambiguities marked (14 original + 1 added = 15 total)
- [x] All ambiguities resolved (Rev 1)
- [x] Architecture decisions documented (AD-1 through AD-9)
- [x] User scenarios defined (37 acceptance scenarios + 11 edge cases)
- [x] Requirements generated (Rev 1: 92 FRs across 17 groups)
- [x] Entities identified (11 entities, including 3 new: Unit, Attachment, and updated Camera Log)
- [x] Logic gap analysis completed (Rev 2: 10 gaps identified and fixed)
- [x] Requirements updated (Rev 2: 99+ FRs across 19 groups, including Data Validation Rules)
- [x] Operational edge case analysis completed (Rev 3: 10 additional gaps fixed)
- [x] Requirements updated (Rev 3: 110+ FRs across 19 groups)
- [x] State synchronization & attribution analysis completed (Rev 4: 7 gaps fixed)
- [x] Requirements updated (Rev 4: 120+ FRs across 19 groups)
- [x] Review checklist passed — **Spec is complete and ready for task decomposition**
