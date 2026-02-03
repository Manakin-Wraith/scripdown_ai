#!/usr/bin/env python3
"""
Simplified Baseline Extraction - OpenAI Comparison

Extracts screenplay elements using OpenAI for comparison with LangExtract POC.
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
import time

try:
    import PyPDF2
    from openai import OpenAI
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("   Run: pip install PyPDF2 openai")
    sys.exit(1)


def extract_text_from_pdf(pdf_path: str, max_pages: int = None) -> str:
    """Extract text from PDF file."""
    print(f"📄 Extracting text from PDF: {pdf_path}")
    
    text_content = []
    
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        total_pages = len(pdf_reader.pages)
        pages_to_process = min(max_pages, total_pages) if max_pages else total_pages
        
        print(f"   Total pages: {total_pages}")
        print(f"   Processing: {pages_to_process} pages")
        
        for page_num in range(pages_to_process):
            page = pdf_reader.pages[page_num]
            text_content.append(page.extract_text())
    
    full_text = '\n'.join(text_content)
    print(f"✅ Extracted {len(full_text)} characters")
    
    return full_text


def extract_with_openai(text: str, api_key: str) -> dict:
    """Extract screenplay elements using OpenAI."""
    print(f"\n🤖 Running OpenAI extraction...")
    
    client = OpenAI(api_key=api_key)
    
    prompt = f"""Extract screenplay elements from this text. Return a JSON object with these arrays:

- scene_headers: Array of scene headings (INT/EXT location - time)
- characters: Array of character names
- props: Array of props mentioned
- wardrobe: Array of wardrobe/costume items
- actions: Array of significant actions
- dialogue: Array of dialogue lines

Text:
{text[:8000]}

Return ONLY valid JSON."""

    start_time = time.time()
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a screenplay analysis assistant. Extract elements and return valid JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    
    elapsed = time.time() - start_time
    
    result_text = response.choices[0].message.content.strip()
    
    # Remove markdown code blocks if present
    if result_text.startswith("```"):
        result_text = result_text.split("```")[1]
        if result_text.startswith("json"):
            result_text = result_text[4:]
        result_text = result_text.strip()
    
    try:
        result = json.loads(result_text)
    except json.JSONDecodeError:
        print("⚠️  Failed to parse JSON, returning empty result")
        result = {
            "scene_headers": [],
            "characters": [],
            "props": [],
            "wardrobe": [],
            "actions": [],
            "dialogue": []
        }
    
    print(f"✅ Extraction complete in {elapsed:.2f} seconds")
    
    return result, elapsed


def save_results(result: dict, elapsed: float, output_dir: Path, script_name: str):
    """Save baseline extraction results."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save JSON
    json_path = output_dir / f"{script_name}_{timestamp}_baseline.json"
    with open(json_path, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"   JSON: {json_path}")
    
    # Generate summary
    total_extractions = sum(len(v) for v in result.values())
    
    summary = f"""# Baseline Extraction Summary (OpenAI)

**Script:** {script_name}
**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Extraction Time:** {elapsed:.2f} seconds

## Statistics

- **Total Extractions:** {total_extractions}
- **Model:** gpt-4o-mini

## Extraction Breakdown

| Category | Count | Percentage |
|----------|-------|------------|
"""
    
    for category, items in sorted(result.items(), key=lambda x: len(x[1]), reverse=True):
        count = len(items)
        pct = (count / total_extractions * 100) if total_extractions > 0 else 0
        summary += f"| {category} | {count} | {pct:.1f}% |\n"
    
    summary += "\n## Sample Extractions\n\n"
    
    for category, items in result.items():
        if items:
            summary += f"### {category.replace('_', ' ').title()}\n```\n"
            for item in items[:10]:
                summary += f"{item}\n"
            summary += "```\n\n"
    
    summary_path = output_dir / f"{script_name}_baseline_summary.md"
    with open(summary_path, 'w') as f:
        f.write(summary)
    print(f"   Summary: {summary_path}")
    
    return json_path, summary_path


def main():
    parser = argparse.ArgumentParser(
        description="Run baseline OpenAI extraction for comparison",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('pdf_path', help='Path to screenplay PDF file')
    parser.add_argument('--output-dir', default='./baseline_results',
                       help='Output directory (default: ./baseline_results)')
    parser.add_argument('--max-pages', type=int, default=None,
                       help='Maximum pages to process (default: all)')
    
    args = parser.parse_args()
    
    # Check API key
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY environment variable not set")
        print("   Set it with: export OPENAI_API_KEY='your-key-here'")
        sys.exit(1)
    
    # Check PDF exists
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        sys.exit(1)
    
    script_name = pdf_path.stem
    output_dir = Path(args.output_dir)
    
    print("=" * 80)
    print("BASELINE EXTRACTION (OpenAI)")
    print("=" * 80)
    print(f"Script: {script_name}")
    print(f"Output: {output_dir}")
    print("=" * 80)
    
    try:
        # Extract text
        text = extract_text_from_pdf(str(pdf_path), args.max_pages)
        
        # Run extraction
        result, elapsed = extract_with_openai(text, api_key)
        
        # Save results
        print(f"\n💾 Saving results to: {output_dir}")
        json_path, summary_path = save_results(result, elapsed, output_dir, script_name)
        
        print("\n" + "=" * 80)
        print("✅ BASELINE EXTRACTION COMPLETE")
        print("=" * 80)
        print(f"📁 Output Directory: {output_dir}")
        print(f"📄 JSON Data: {json_path.name}")
        print(f"📊 Summary Report: {summary_path.name}")
        print("\n💡 Next Steps:")
        print(f"   1. Review summary: cat {summary_path}")
        print(f"   2. Compare with LangExtract results")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Baseline extraction failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
