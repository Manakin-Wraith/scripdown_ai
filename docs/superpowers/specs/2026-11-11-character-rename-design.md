# Character rename — design

**Status:** shipped 2026-11-11 (commit 3cd9cad, migration 062).

## Intent
A uploaded script is "perfect", but the production wants a different name for
a character (script says MARCUS, the production calls the role DETECTIVE
COLE). The new name must show up in the breakdown, stripboard, schedule,
reports/PDFs and call sheets without editing or re-uploading the script.

## Decision
A rename is a **single-alias merge**: the old name becomes an alias of the new
canonical name in `character_aliases`, and stored names are rewritten. This
reuses the mechanism that already stops re-analysis from reintroducing merged
duplicates. Rejected: a display-name overlay column, because every consumer
(reports, PDFs, schedule, call sheets) would have to learn to read it.

## Behaviour
- `POST /api/scripts/<id>/characters/rename` `{old_name, new_name}`; script
  role `admin`+ (same as Cast edits). Names are upper-cased.
- Rewrites: `scenes.characters`; `character` refs inside `scenes.wardrobe` and
  `scenes.makeup`; `department_items` (type `characters`); the `casting` row
  (call sheets follow `casting_id`); `character_aliases`.
- 409 if the new name is already a character (scenes or casting) — use Merge.
  404 if the old name isn't found. Same name is a 400.
- **"Originally X" note.** `character_aliases.original_name` (migration 062)
  holds the name as it appears in the script on rename rows (NULL on merge
  rows). On a chained rename (A->B->C) existing aliases are repointed to C and
  all keep `original_name = A`. Renaming back to A deletes the A alias and the
  note disappears. `GET /api/scripts/<id>/casting` returns `original_name` on
  each casting row and each breakdown character.
- UI: "Rename character" link in the Cast drawer (`CastingDetailPanel`),
  "originally X" under the scene count in `CastRow` and as the drawer subtitle.

## Non-goals
Editing the script text or page viewer (dialogue cues keep the original name);
rename UI in the Characters/merge view; atomicity (see `docs/BACKLOG.md`).

## Code
`backend/services/character_rename_service.py`, route in
`backend/routes/casting_routes.py`, tests in
`backend/tests/test_character_rename.py` (in-memory fake client covers
rewrite, chained rename, revert, merge-alias repoint, collisions, route auth).
