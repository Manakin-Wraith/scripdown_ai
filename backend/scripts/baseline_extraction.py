#!/usr/bin/env python3
"""
Baseline Extraction Script - Current OpenAI System

This script runs OpenAI-based extraction for comparison with LangExtract POC.
Uses the same extraction approach as the current system.

Usage:
    python baseline_extraction.py <pdf_path> [--max-pages N] [--output-dir DIR]

Example:
    python baseline_extraction.py ../BIRD_V8.pdf --max-pages 10
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

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
        
        print(f"   Processing {pages_to_process} of {total_pages} pages...")
        
        for page_num in range(pages_to_process):
            page = pdf_reader.pages[page_num]
            text = page.extract_text()
            text_content.append(text)
            
            if (page_num + 1) % 10 == 0:
                print(f"   Processed {page_num + 1}/{pages_to_process} pages...")
        
        full_text = "\n\n".join(text_content)
        print(f"✅ Extracted {len(full_text)} characters from {pages_to_process} pages")
        
        return full_text


def run_baseline_extraction(text: str, script_id: str = "baseline_test") -> dict:
    """
    Run baseline extraction using current system.
    
    Args:
        text: Screenplay text
        script_id: Script identifier
    
    Returns:
        Dictionary with extraction results
    """
    print(f"\n🤖 Running baseline extraction (current system)...")
    
    start_time = time.time()
    
    # Step 1: Extract scene candidates using regex
    print("   Step 1: Extracting scene candidates...")
    scene_candidates = extract_scenes_from_text(text, script_id)
    print(f"   Found {len(scene_candidates)} scene candidates")
    
    # Step 2: Enhance scenes with AI (sample first 5 for POC)
    print(f"   Step 2: Enhancing scenes with AI (processing first 5 scenes)...")
    enhanced_scenes = []
    
    for i, candidate in enumerate(scene_candidates[:5]):
        print(f"      Enhancing scene {i+1}/5...")
        try:
            enhanced = enhance_scene(candidate, script_id)
            enhanced_scenes.append(enhanced)
        except Exception as e:
            print(f"      ⚠️  Failed to enhance scene {i+1}: {e}")
            enhanced_scenes.append(candidate)
    
    elapsed_time = time.time() - start_time
    
    # Count extractions
    total_characters = sum(len(s.get('characters', [])) for s in enhanced_scenes)
    total_props = sum(len(s.get('props', [])) for s in enhanced_scenes)
    total_wardrobe = sum(len(s.get('wardrobe', [])) for s in enhanced_scenes)
    
    print(f"\n✅ Baseline extraction complete in {elapsed_time:.2f} seconds")
    print(f"   Scenes processed: {len(enhanced_scenes)}")
    print(f"   Characters: {total_characters}")
    print(f"   Props: {total_props}")
    print(f"   Wardrobe: {total_wardrobe}")
    
    return {
        'scene_candidates': scene_candidates,
        'enhanced_scenes': enhanced_scenes,
        'extraction_time': elapsed_time,
        'stats': {
            'total_scenes': len(enhanced_scenes),
            'total_characters': total_characters,
            'total_props': total_props,
            'total_wardrobe': total_wardrobe
        }
    }


def save_baseline_results(results: dict, output_dir: str, script_name: str) -> str:
    """Save baseline extraction results to JSON."""
    print(f"\n💾 Saving baseline results to: {output_dir}")
    
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{script_name}_baseline_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"✅ Baseline results saved: {filepath}")
    
    return filepath


def generate_baseline_report(results: dict, output_dir: str, script_name: str) -> str:
    """Generate baseline extraction summary report."""
    print(f"\n📊 Generating baseline summary report...")
    
    stats = results['stats']
    extraction_time = results['extraction_time']
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_lines = [
        f"# Baseline Extraction Summary Report",
        f"",
        f"**Script:** {script_name}",
        f"**Date:** {timestamp}",
        f"**Extraction Time:** {extraction_time:.2f} seconds",
        f"**System:** Current OpenAI-based extraction",
        f"",
        f"## Statistics",
        f"",
        f"- **Total Scenes:** {stats['total_scenes']}",
        f"- **Total Characters:** {stats['total_characters']}",
        f"- **Total Props:** {stats['total_props']}",
        f"- **Total Wardrobe:** {stats['total_wardrobe']}",
        f"- **Processing Speed:** {stats['total_scenes'] / extraction_time:.2f} scenes/second",
        f"",
        f"## Sample Scenes",
        f""
    ]
    
    # Add sample scenes
    for i, scene in enumerate(results['enhanced_scenes'][:3], 1):
        report_lines.extend([
            f"### Scene {i}",
            f"",
            f"**Header:** {scene.get('scene_header', 'N/A')}",
            f"**Setting:** {scene.get('setting', 'N/A')}",
            f"**Time:** {scene.get('time_of_day', 'N/A')}",
            f"",
            f"**Characters:** {', '.join(scene.get('characters', []))}",
            f"**Props:** {', '.join(scene.get('props', []))}",
            f"**Wardrobe:** {', '.join(scene.get('wardrobe', []))}",
            f""
        ])
    
    # Save report
    report_filename = f"{script_name}_baseline_summary.md"
    report_path = os.path.join(output_dir, report_filename)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))
    
    print(f"✅ Baseline summary saved: {report_path}")
    
    return report_path


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Baseline extraction for comparison with LangExtract"
    )
    
    parser.add_argument('pdf_path', help='Path to screenplay PDF file')
    parser.add_argument('--output-dir', default='./baseline_results',
                       help='Output directory (default: ./baseline_results)')
    parser.add_argument('--max-pages', type=int, default=None,
                       help='Maximum pages to process')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.pdf_path):
        print(f"❌ Error: PDF not found: {args.pdf_path}")
        sys.exit(1)
    
    script_name = Path(args.pdf_path).stem
    
    print("=" * 80)
    print("📊 Baseline Extraction (Current System)")
    print("=" * 80)
    print(f"Script: {script_name}")
    print(f"PDF: {args.pdf_path}")
    print(f"Output: {args.output_dir}")
    print("=" * 80)
    
    try:
        # Extract text
        text = extract_text_from_pdf(args.pdf_path, max_pages=args.max_pages)
        
        # Run baseline extraction
        results = run_baseline_extraction(text, script_name)
        
        # Save results
        json_path = save_baseline_results(results, args.output_dir, script_name)
        report_path = generate_baseline_report(results, args.output_dir, script_name)
        
        print("\n" + "=" * 80)
        print("✅ BASELINE EXTRACTION COMPLETE")
        print("=" * 80)
        print(f"📁 Output Directory: {args.output_dir}")
        print(f"📄 JSON Data: {os.path.basename(json_path)}")
        print(f"📊 Summary Report: {os.path.basename(report_path)}")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Baseline extraction failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
