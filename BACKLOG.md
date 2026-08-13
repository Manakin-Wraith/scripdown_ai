# Backlog

## To brainstorm

- **Edit source script after upload**: figure out how users can make changes to their original PDF/FDX script upload (e.g. fix a scene, typo, or revision) without re-uploading and re-running the full extraction pipeline from scratch.
- **Separate Location (production element) from Sets (creative element)**: brainstorm how to distinguish these two breakdown concepts, which are currently conflated.
- **CSV export for reports**: add a CSV export option for production reports, alongside the existing PDF (WeasyPrint) output.
- **Breakdown UI/UX drill-down (CRUD)**: brainstorm how to enhance the breakdown view so users can drill into more detail and create/edit/delete individual elements (characters, props, etc.) rather than just viewing extracted results.
- **Failed-renewal downgrade gap**: nothing currently writes `status = 'expired'` on a subscription renewal failure, so `can_use_teams` doesn't get revoked and seat counting (`account_seats.term_expires_at`) silently stops once the term lapses, even before any explicit downgrade logic runs. Coupled with renewal-automation work; see `docs/superpowers/specs/2026-07-18-seat-purchase-flow-design.md` and `docs/superpowers/specs/2026-07-21-billing-page-redesign-design.md`.
