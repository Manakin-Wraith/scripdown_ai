#!/usr/bin/env python3
"""
Phase 0.5 Check #6: Compare vendored ScreenPy grammar vs regex header counts.

Runs both the existing regex-based scene detection AND the vendored ScreenPy
parser on pdfplumber layout=True text for each test PDF. Compares counts
and reports per-script results.

Also tests speaker/character extraction (Check #8).
"""

import sys
import os
import re
import time
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pdfplumber

from lib.screenpy.parser import ScreenplayParser


# ---------------------------------------------------------------------------
# Regex scene header detection (same patterns as extraction_pipeline.py)
# ---------------------------------------------------------------------------
TIME_OF_DAY = (
    r"(DAY|NIGHT|DUSK|DAWN|MORNING|EVENING|AFTERNOON|CONTINUOUS|LATER|SAME|"
    r"MOMENT'?S?\s*LATER|MOMENTS?\s*LATER)"
)

SCENE_PATTERNS = [
    rf"^(\d+[A-Z]?)\.\s*(INT|EXT|INT\.?/EXT|EXT\.?/INT|I/E|E/I)[.\s]+(.+?)\s*[-–—]\s*{TIME_OF_DAY}",
    rf"^(\d+[A-Z]?)\s+(INT|EXT|INT\.?/EXT|EXT\.?/INT)[.\s]+(.+?)\s*[-–—]\s*{TIME_OF_DAY}",
    rf"^()(INT|EXT|INT\.?/EXT|EXT\.?/INT)[.\s]+(.+?)\s*[-–—]\s*{TIME_OF_DAY}",
]


def regex_detect_headers(text: str) -> list:
    """Detect scene headers using regex (production logic)."""
    headers = []
    for i, line in enumerate(text.split("\n")):
        stripped = line.strip()
        if not stripped:
            continue
        for pattern in SCENE_PATTERNS:
            m = re.match(pattern, stripped, re.IGNORECASE)
            if m:
                headers.append({
                    "line_number": i,
                    "line": stripped,
                })
                break
    return headers


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text using pdfplumber layout=True."""
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text(layout=True) or ""
            pages.append(text)
    return "\n".join(pages)


def run_comparison(pdf_paths: list) -> dict:
    """Run grammar vs regex comparison on all PDFs."""
    results = {
        "scripts": [],
        "summary": {},
    }

    total_regex = 0
    total_grammar = 0
    total_chars_found = 0

    for pdf_path in pdf_paths:
        name = os.path.basename(pdf_path)
        print(f"\n{'='*60}")
        print(f"  {name}")
        print(f"{'='*60}")

        # Extract text
        t0 = time.time()
        text = extract_text_from_pdf(pdf_path)
        extract_time = time.time() - t0

        # --- Regex detection ---
        t0 = time.time()
        regex_headers = regex_detect_headers(text)
        regex_time = time.time() - t0
        regex_count = len(regex_headers)

        # --- Grammar parser ---
        t0 = time.time()
        parser = ScreenplayParser(locale_codes=["en", "af"])
        screenplay = parser.parse(text)
        grammar_time = time.time() - t0

        # Count master segments (= scene headers with INT/EXT)
        master_segments = screenplay.master_segments
        grammar_count = len(master_segments)

        # Character extraction
        characters = screenplay.characters
        dialogue_segments = screenplay.dialogue_segments

        # Determine pass/fail
        passed = grammar_count >= regex_count
        status = "PASS" if passed else "FAIL"

        total_regex += regex_count
        total_grammar += grammar_count
        total_chars_found += len(characters)

        print(f"\n  [Check #6] Grammar vs Regex Header Count")
        print(f"  {'─'*50}")
        print(f"      Regex headers:    {regex_count:>5}")
        print(f"      Grammar masters:  {grammar_count:>5}")
        print(f"      {'✅' if passed else '❌'} {status} (grammar {'≥' if passed else '<'} regex)")
        print(f"      Extract time:     {extract_time:.2f}s")
        print(f"      Regex time:       {regex_time:.4f}s")
        print(f"      Grammar time:     {grammar_time:.2f}s")

        # Show first few grammar-detected headers
        if master_segments:
            print(f"\n      Grammar headers (first 5):")
            for seg in master_segments[:5]:
                h = seg.heading
                locs = " > ".join(h.locations) if h.locations else "?"
                tod = h.time_of_day or "?"
                lt = h.location_type if isinstance(h.location_type, str) else h.location_type
                print(f"        L{seg.start_pos}: {lt} {locs} - {tod}")

        # Show headers found by regex but missed by grammar (and vice versa)
        regex_lines = {h["line_number"] for h in regex_headers}
        grammar_lines = {seg.start_pos for seg in master_segments}

        only_regex = regex_lines - grammar_lines
        only_grammar = grammar_lines - regex_lines

        if only_regex:
            print(f"\n      ⚠️  Regex-only ({len(only_regex)} headers):")
            for ln in sorted(list(only_regex))[:5]:
                for h in regex_headers:
                    if h["line_number"] == ln:
                        print(f"        L{ln}: {h['line'][:60]}")

        if only_grammar:
            print(f"\n      ℹ️  Grammar-only ({len(only_grammar)} headers):")
            for ln in sorted(list(only_grammar))[:5]:
                for seg in master_segments:
                    if seg.start_pos == ln:
                        print(f"        L{ln}: {seg.heading.raw_text[:60]}")

        # Check #8: Speaker extraction
        print(f"\n  [Check #8] Speaker/Character Extraction")
        print(f"  {'─'*50}")
        print(f"      Unique characters: {len(characters)}")
        print(f"      Dialogue blocks:   {len(dialogue_segments)}")
        if characters:
            sorted_chars = sorted(characters.items(), key=lambda x: -x[1])
            print(f"      Top speakers:")
            for char_name, count in sorted_chars[:8]:
                print(f"        {char_name:<30} {count:>3} lines")

        results["scripts"].append({
            "name": name,
            "regex_headers": regex_count,
            "grammar_masters": grammar_count,
            "grammar_ge_regex": passed,
            "unique_characters": len(characters),
            "dialogue_blocks": len(dialogue_segments),
            "top_characters": dict(sorted(characters.items(), key=lambda x: -x[1])[:10]),
            "extract_time": round(extract_time, 3),
            "regex_time": round(regex_time, 4),
            "grammar_time": round(grammar_time, 3),
        })

    # Summary
    all_passed = all(r["grammar_ge_regex"] for r in results["scripts"])
    results["summary"] = {
        "total_scripts": len(pdf_paths),
        "total_regex_headers": total_regex,
        "total_grammar_masters": total_grammar,
        "total_characters_found": total_chars_found,
        "check_6_passed": all_passed,
        "check_8_has_characters": total_chars_found > 0,
    }

    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    print(f"  Check #6 (Grammar ≥ Regex): {'✅ PASS' if all_passed else '❌ FAIL'}")
    print(f"    Total regex:   {total_regex}")
    print(f"    Total grammar: {total_grammar}")
    print(f"  Check #8 (Speaker Extraction): {'✅ PASS' if total_chars_found > 0 else '❌ FAIL'}")
    print(f"    Total characters found: {total_chars_found}")

    if all_passed and total_chars_found > 0:
        print(f"\n  🟢 ALL DEFERRED CHECKS PASSED — FULL GO FOR SPRINT")
    else:
        print(f"\n  🔴 DEFERRED CHECKS INCOMPLETE")

    return results


if __name__ == "__main__":
    upload_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
    pdfs = [
        os.path.join(upload_dir, f)
        for f in [
            "Ep_1.pdf",
            "LASGIDI_-EPISODE_14_-YANK_HOOKUP.pdf",
            "LASGIDI_-EPISODE_4_-_EDIT.pdf",
            "Script_Powerlessness.pdf",
            "BIRD_V8.pdf",  # Afrikaans — now should work with en+af locale
        ]
        if os.path.exists(os.path.join(upload_dir, f))
    ]

    print(f"╔{'═'*58}╗")
    print(f"║  ScreenPy Grammar vs Regex — Check #6 & #8{' '*14}║")
    print(f"║  Testing {len(pdfs)} script(s) with en+af locale{' '*17}║")
    print(f"╚{'═'*58}╝")

    results = run_comparison(pdfs)

    # Save results
    out_path = os.path.join(os.path.dirname(__file__), "grammar_vs_regex_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  📁 Results saved to: {out_path}")
