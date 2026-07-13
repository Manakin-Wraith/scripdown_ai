-- One-off backfill (2026-07-13): fold curly quotes to straight in location data.
--
-- Context: normalize_place did NOT fold curly apostrophes while canonicalize_setting
-- did, so location_canonical could diverge from setting (e.g. "TAM'S ROOM" with a
-- curly apostrophe vs a straight one). That split one place into two lanes and made
-- exact-match nesting return "0 scenes updated". The code fix (normalize_place now
-- folds curly quotes) prevents new divergence; this backfill repairs existing rows.
--
-- Applied to production project twzfaizeyqwevmhjyicz via Supabase. Idempotent.
-- Curly chars: U+2019 = chr(8217), U+2018 = chr(8216); straight = chr(39).

update scenes
set location_canonical = replace(replace(location_canonical, chr(8217), chr(39)), chr(8216), chr(39))
where location_canonical like '%'||chr(8217)||'%' or location_canonical like '%'||chr(8216)||'%';

update scenes
set location_hierarchy = replace(replace(location_hierarchy::text, chr(8217), chr(39)), chr(8216), chr(39))::jsonb
where location_hierarchy::text like '%'||chr(8217)||'%' or location_hierarchy::text like '%'||chr(8216)||'%';

update location_aliases
set alias_place     = replace(replace(alias_place,     chr(8217), chr(39)), chr(8216), chr(39)),
    canonical_place = replace(replace(canonical_place, chr(8217), chr(39)), chr(8216), chr(39)),
    set_name        = replace(replace(set_name,        chr(8217), chr(39)), chr(8216), chr(39))
where alias_place     like '%'||chr(8217)||'%' or alias_place     like '%'||chr(8216)||'%'
   or canonical_place like '%'||chr(8217)||'%' or canonical_place like '%'||chr(8216)||'%'
   or set_name        like '%'||chr(8217)||'%' or set_name        like '%'||chr(8216)||'%';

update sub_location_aliases
set parent_place  = replace(replace(parent_place,  chr(8217), chr(39)), chr(8216), chr(39)),
    alias_sub     = replace(replace(alias_sub,     chr(8217), chr(39)), chr(8216), chr(39)),
    canonical_sub = replace(replace(canonical_sub, chr(8217), chr(39)), chr(8216), chr(39))
where parent_place  like '%'||chr(8217)||'%' or parent_place  like '%'||chr(8216)||'%'
   or alias_sub     like '%'||chr(8217)||'%' or alias_sub     like '%'||chr(8216)||'%'
   or canonical_sub like '%'||chr(8217)||'%' or canonical_sub like '%'||chr(8216)||'%';
