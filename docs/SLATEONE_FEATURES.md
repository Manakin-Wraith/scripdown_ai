# 🎬 SlateOne Capabilities & Roadmap

## 🚀 Currently Available Features

### 1. AI-Powered Script Breakdown & Ingestion
- **Instant Scene Detection:** Upload a PDF script and get instant, accurate scene parsing preserving original scene numbers and formatting.
- **Deep AI Extraction:** On-demand AI analysis (per-scene or bulk) extracts Cast, Props, Wardrobe, Vehicles, Makeup & Hair, SFX, Sound, and Atmosphere.
- **Smart Entity Resolution:** Automatically detects and lets you merge misspelled or duplicate character names (e.g., "JOHN" vs "JON") across the entire script.
- **Cover Page Metadata:** Advanced extraction of script title, writer(s), draft versions, and contact information.

### 2. Scene & Story Management
- **Master-Detail Scene Viewer:** Navigate the script from multiple perspectives—by Scene order, by Character appearances, or by Location.
- **Story Days Intelligence:** AI automatically detects time transitions and assigns sequential story days. Manually lock days, bulk assign, or set specific timeline codes (Present, Flashback, Dream, Montage, etc.).
- **Script Editing:** Full suite of tools to split, merge, omit/restore, reorder, or manually add scenes.
- **Revision Tracking:** Lock scripts for production and track changes using standard industry revision colors (White, Blue, Pink, etc.). 

### 3. Narrative & Scene Intelligence
- **Narrative Dashboard:** A full-script story map that auto-detects the plot structure (e.g., Hero's Journey, Save the Cat, Three-Act), tracks character arcs, pacing, emotional flow, and relationship webs.
- **Scene Deep Dive:** Drill into individual scenes to analyze underlying dialogue subtext, character emotions, action beat intensity, and transition logic.

### 4. Interactive Scheduling
- **Zoomable Stripboard:** A highly responsive, drag-and-drop stripboard with three semantic zoom levels (Micro, Normal, Detailed). 
- **Grouping & Filtering:** Filter the stripboard by INT/EXT, Time of Day, or group strips by Location or Story Day.

### 5. Team Collaboration & Workspaces
- **Department Silos:** Invite crew members to specific departments (Camera, Wardrobe, Locations, etc.) with dedicated workspaces.
- **Cross-Department Communication:** Start discussion threads linked to specific scenes or items.
- **Item Tracking:** Tag breakdown items with statuses, assign priorities, and leave department-specific notes via a slide-out drawer.
- **Access Control:** Script owners can manage team invites, revoke access, and assign view/edit permissions.

### 6. Series & Multi-Episode Management
- **Series → Season → Episode Grouping:** Organize related episode scripts under a Series and Season, either inline at upload via a Series/Season picker or by reassigning an existing script from My Scripts.
- **Grouped My-Scripts View:** My Scripts nests episodes under collapsible Series → Season rows alongside the regular flat/sortable list, with quick links to view the series or add another episode.
- **Series Pages:** Dedicated Series list (accordion) and Season pages show episode order and a combined cast view — one row per distinct character name across the season's visible episodes.
- **Zero Impact on Billing or Parsing:** Series/season membership is purely organizational — each episode is uploaded, parsed, and billed exactly as a standalone script.

### 7. Cast & Casting
- **Per-Character Casting Record:** Capture actor name, engagement status (wishlist, offer, booked, declined, released), contact details (phone, email, agent), and production notes for every named character in the script.
- **Cast Tiers & Role Organization:** Organize cast by role weight — leads, supporting, featured, and background — with collapsible tier grouping on the Cast tab, persistence per script, and tier-aware conflict detection.
- **Multi-Photo Gallery:** Upload and manage multiple reference photos per cast member (headshots, full-body shots, continuity references) with kind-tagging, primary-selection, and 1-hour signed URLs for secure Supabase storage.
- **Background Talent as Groups:** Track background artists by headcount and scene assignment rather than one row per individual (12 pedestrians, 4 restaurant patrons, etc.), with status, day rates, and multi-scene targeting.
- **Availability Blackout Dates:** Define date ranges when a cast member is unavailable (location shoots, other projects, unavailable dates), automatically flagged against the production schedule.
- **Schedule Conflict Detection & In-App Resolution:** Automatically detect when a booked or offer-status cast member's unavailability overlaps a dated shoot day containing their scene. Resolve conflicts directly in the app by moving the scene to a suggested conflict-free day, unassigning it, or acknowledging with a reason.

### 8. Productions
- **Production Entity:** Group the scripts you shoot together (a TV block, a feature and its reshoot) under a single Production with its own status and shoot dates — an axis independent of Series/Season.
- **Script Association:** Attach and detach scripts from a production; each script belongs to at most one production, kept in sync with My Scripts.
- **Units:** Every production starts with a "Main Unit"; multi-unit support underpins later Daily Production Reporting.

### 9. Exporting & Reporting
- **Customizable Reports:** Generate 7+ standard production reports (Scene Breakdown, Day Out of Days (DOOD), Location, Props, Wardrobe, One-Liner, Full Binder).
- **Advanced Filtering:** Filter reports across 9 dimensions (location, character, timeline code, etc.) and save custom filter presets.
- **Highlighted Script PDF:** Export a script PDF with color-coded, industry-standard text highlights for every extracted breakdown item.
- **Shooting Script Export:** Export a clean, printable shooting script reflecting any edits or omissions.
- **Public Share Links:** Generate secure, expiring web links to share reports with external stakeholders without requiring a login.

---

## 🔮 Upcoming Features (Roadmap)

### 1. Daily Production Reporting (DPR)
- **Digital DPR Generation:** Capture what actually happened on set each day, compared automatically against the planned schedule baseline.
- **Multi-Unit Support:** Manage separate daily reports for Main Unit, 2nd Unit, Splinter, etc.
- **Department Logs & Integrity:** Structured daily submissions for Camera, Sound, and Script Supervisors.
- **Time Tracking & Overtime:** Track cast and crew Call/Set/Wrap times, meal penalties, and forced calls.
- **Incident & Delay Logging:** Track delays, weather impact, and safety incidents.
- **Verifiable PDFs:** Generate industry-standard, locked DPR PDFs with QR code deep-links for insurance and legal traceability.

### 2. Production Analytics Dashboard
- **Schedule Burndown:** Visual charts tracking cumulative pages shot vs. planned.
- **Velocity Metrics:** Track average pages/day and project the wrap date based on actual shooting velocity.
- **Delay Analysis:** Pie charts and trend lines categorizing the root causes of production delays.

### 3. Call Sheet Generation
- Generate detailed daily Call Sheets (the "Plan") that seamlessly sync with the schedule and feed directly into the next day's DPR (the "Reality").

### 4. On-Set Offline Mode
- Service worker and local database support allowing crew to log department notes and DPR data in remote locations with zero cellular service, auto-syncing when a connection is restored.

### 5. Wrap Reports & Post-Production Handoff
- Auto-compile end-of-production wrap reports from all DPRs.
- Export continuity notes, camera logs, and circle takes directly into formats suitable for editorial.
