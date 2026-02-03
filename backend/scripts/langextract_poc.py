#!/usr/bin/env python3
"""
LangExtract Proof of Concept Script
Extracts screenplay elements from PDF and generates interactive visualization.

Usage:
    python langextract_poc.py <pdf_path> [--output-dir <dir>] [--model <model_id>]

Example:
    python langextract_poc.py ../BIRD_V8.pdf --output-dir ./langextract_results
"""

import os
import sys
import argparse
import time
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import langextract as lx
import PyPDF2
from services.langextract_schema import SCREENPLAY_EXTRACTION_PROMPT
from services.langextract_examples import SCREENPLAY_EXAMPLES


def extract_text_from_pdf(pdf_path: str, max_pages: int = None) -> str:
    """
    Extract text from PDF file.
    
    Args:
        pdf_path: Path to PDF file
        max_pages: Maximum number of pages to extract (None for all)
    
    Returns:
        Extracted text as string
    """
    print(f"📄 Extracting text from PDF: {pdf_path}")
    
    text_content = []
    
    try:
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
            
    except Exception as e:
        print(f"❌ Error extracting PDF: {e}")
        raise


def run_langextract_extraction(
    text: str,
    model_id: str = "gemini-2.5-flash",
    extraction_passes: int = 2,
    max_workers: int = 10,
    max_char_buffer: int = 2000
) -> lx.data.AnnotatedDocument:
    """
    Run LangExtract extraction on screenplay text.
    
    Args:
        text: Screenplay text to extract from
        model_id: LLM model to use
        extraction_passes: Number of extraction passes for recall
        max_workers: Number of parallel workers
        max_char_buffer: Character buffer size for chunking
    
    Returns:
        AnnotatedDocument with extractions
    """
    print(f"\n🤖 Running LangExtract extraction...")
    print(f"   Model: {model_id}")
    print(f"   Extraction passes: {extraction_passes}")
    print(f"   Max workers: {max_workers}")
    print(f"   Chunk size: {max_char_buffer} chars")
    
    start_time = time.time()
    
    try:
        # Check for API key
        api_key = os.environ.get('GOOGLE_API_KEY') or os.environ.get('GEMINI_API_KEY')
        if not api_key:
            print("⚠️  Warning: No GOOGLE_API_KEY or GEMINI_API_KEY found in environment")
            print("   Set one of these environment variables to use Gemini models")
            print("   Example: export GOOGLE_API_KEY='your-key-here'")
            raise ValueError("API key required for LangExtract")
        
        result = lx.extract(
            text_or_documents=text,
            prompt_description=SCREENPLAY_EXTRACTION_PROMPT,
            examples=SCREENPLAY_EXAMPLES,
            model_id=model_id,
            extraction_passes=extraction_passes,
            max_workers=max_workers,
            max_char_buffer=max_char_buffer,
            api_key=api_key
        )
        
        elapsed_time = time.time() - start_time
        
        # Count extractions by class
        extraction_counts = {}
        for extraction in result.extractions:
            class_name = extraction.extraction_class
            extraction_counts[class_name] = extraction_counts.get(class_name, 0) + 1
        
        print(f"\n✅ Extraction complete in {elapsed_time:.2f} seconds")
        print(f"   Total extractions: {len(result.extractions)}")
        print(f"\n   Breakdown by class:")
        for class_name, count in sorted(extraction_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"      {class_name}: {count}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        raise


def save_results(
    result: lx.data.AnnotatedDocument,
    output_dir: str,
    script_name: str
) -> tuple:
    """
    Save extraction results to JSONL and generate HTML visualization.
    
    Args:
        result: AnnotatedDocument from LangExtract
        output_dir: Directory to save outputs
        script_name: Name of the script (for filenames)
    
    Returns:
        Tuple of (jsonl_path, html_path)
    """
    print(f"\n💾 Saving results to: {output_dir}")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate timestamp for filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save JSONL
    jsonl_filename = f"{script_name}_{timestamp}.jsonl"
    jsonl_path = os.path.join(output_dir, jsonl_filename)
    
    print(f"   Saving JSONL: {jsonl_filename}")
    lx.io.save_annotated_documents([result], output_name=jsonl_filename, output_dir=output_dir)
    
    # Generate HTML visualization
    html_filename = f"{script_name}_{timestamp}_visualization.html"
    html_path = os.path.join(output_dir, html_filename)
    
    print(f"   Generating HTML visualization: {html_filename}")
    html_content = lx.visualize(jsonl_path)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        # Handle both string and IPython display objects
        if hasattr(html_content, 'data'):
            f.write(html_content.data)
        else:
            f.write(html_content)
    
    print(f"✅ Results saved successfully")
    print(f"   JSONL: {jsonl_path}")
    print(f"   HTML:  {html_path}")
    
    return jsonl_path, html_path


def generate_summary_report(
    result: lx.data.AnnotatedDocument,
    extraction_time: float,
    output_dir: str,
    script_name: str
) -> str:
    """
    Generate a summary report of the extraction.
    
    Args:
        result: AnnotatedDocument from LangExtract
        extraction_time: Time taken for extraction
        output_dir: Directory to save report
        script_name: Name of the script
    
    Returns:
        Path to summary report
    """
    print(f"\n📊 Generating summary report...")
    
    # Count extractions by class
    extraction_counts = {}
    for extraction in result.extractions:
        class_name = extraction.extraction_class
        extraction_counts[class_name] = extraction_counts.get(class_name, 0) + 1
    
    # Calculate statistics
    total_extractions = len(result.extractions)
    text_length = len(result.text)
    
    # Generate report
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_lines = [
        f"# LangExtract POC Summary Report",
        f"",
        f"**Script:** {script_name}",
        f"**Date:** {timestamp}",
        f"**Extraction Time:** {extraction_time:.2f} seconds",
        f"",
        f"## Statistics",
        f"",
        f"- **Total Extractions:** {total_extractions}",
        f"- **Text Length:** {text_length:,} characters",
        f"- **Extraction Rate:** {total_extractions / (text_length / 1000):.2f} extractions per 1K chars",
        f"- **Processing Speed:** {text_length / extraction_time:.0f} chars/second",
        f"",
        f"## Extraction Breakdown",
        f"",
        f"| Extraction Class | Count | Percentage |",
        f"|-----------------|-------|------------|"
    ]
    
    for class_name, count in sorted(extraction_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_extractions) * 100
        report_lines.append(f"| {class_name} | {count} | {percentage:.1f}% |")
    
    report_lines.extend([
        f"",
        f"## Sample Extractions",
        f"",
        f"### Scene Headers",
        f"```"
    ])
    
    # Add sample extractions
    scene_headers = [e for e in result.extractions if e.extraction_class == "scene_header"][:5]
    for extraction in scene_headers:
        report_lines.append(f"{extraction.extraction_text}")
    
    report_lines.extend([
        f"```",
        f"",
        f"### Characters",
        f"```"
    ])
    
    characters = [e for e in result.extractions if e.extraction_class == "character"][:10]
    for extraction in characters:
        report_lines.append(f"{extraction.extraction_text}")
    
    report_lines.extend([
        f"```",
        f"",
        f"### Props",
        f"```"
    ])
    
    props = [e for e in result.extractions if e.extraction_class == "prop"][:10]
    for extraction in props:
        report_lines.append(f"{extraction.extraction_text}")
    
    report_lines.append(f"```")
    
    # Save report
    report_filename = f"{script_name}_summary.md"
    report_path = os.path.join(output_dir, report_filename)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))
    
    print(f"✅ Summary report saved: {report_path}")
    
    return report_path


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="LangExtract POC for screenplay analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python langextract_poc.py ../BIRD_V8.pdf
  
  # Specify output directory
  python langextract_poc.py ../BIRD_V8.pdf --output-dir ./results
  
  # Use different model
  python langextract_poc.py ../BIRD_V8.pdf --model gemini-2.0-flash-exp
  
  # Process only first 20 pages
  python langextract_poc.py ../BIRD_V8.pdf --max-pages 20
        """
    )
    
    parser.add_argument('pdf_path', help='Path to screenplay PDF file')
    parser.add_argument('--output-dir', default='./langextract_results',
                       help='Output directory for results (default: ./langextract_results)')
    parser.add_argument('--model', default='gemini-2.5-flash',
                       help='LLM model to use (default: gemini-2.5-flash)')
    parser.add_argument('--max-pages', type=int, default=None,
                       help='Maximum number of pages to process (default: all)')
    parser.add_argument('--extraction-passes', type=int, default=2,
                       help='Number of extraction passes (default: 2)')
    parser.add_argument('--max-workers', type=int, default=10,
                       help='Number of parallel workers (default: 10)')
    parser.add_argument('--chunk-size', type=int, default=2000,
                       help='Character buffer size for chunking (default: 2000)')
    
    args = parser.parse_args()
    
    # Validate PDF path
    if not os.path.exists(args.pdf_path):
        print(f"❌ Error: PDF file not found: {args.pdf_path}")
        sys.exit(1)
    
    # Extract script name from filename
    script_name = Path(args.pdf_path).stem
    
    print("=" * 80)
    print("🎬 LangExtract Screenplay Analysis POC")
    print("=" * 80)
    print(f"Script: {script_name}")
    print(f"PDF: {args.pdf_path}")
    print(f"Output: {args.output_dir}")
    print("=" * 80)
    
    try:
        # Step 1: Extract text from PDF
        text = extract_text_from_pdf(args.pdf_path, max_pages=args.max_pages)
        
        # Step 2: Run LangExtract extraction
        start_time = time.time()
        result = run_langextract_extraction(
            text=text,
            model_id=args.model,
            extraction_passes=args.extraction_passes,
            max_workers=args.max_workers,
            max_char_buffer=args.chunk_size
        )
        extraction_time = time.time() - start_time
        
        # Step 3: Save results
        jsonl_path, html_path = save_results(result, args.output_dir, script_name)
        
        # Step 4: Generate summary report
        report_path = generate_summary_report(result, extraction_time, args.output_dir, script_name)
        
        # Final summary
        print("\n" + "=" * 80)
        print("✅ POC COMPLETE")
        print("=" * 80)
        print(f"📁 Output Directory: {args.output_dir}")
        print(f"📄 JSONL Data: {os.path.basename(jsonl_path)}")
        print(f"🌐 HTML Visualization: {os.path.basename(html_path)}")
        print(f"📊 Summary Report: {os.path.basename(report_path)}")
        print("\n💡 Next Steps:")
        print(f"   1. Open the HTML visualization in your browser:")
        print(f"      open {html_path}")
        print(f"   2. Review the summary report:")
        print(f"      cat {report_path}")
        print(f"   3. Compare with baseline extraction results")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ POC failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
