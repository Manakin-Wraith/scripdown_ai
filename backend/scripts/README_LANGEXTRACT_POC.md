# LangExtract POC - Execution Guide

## Overview

This directory contains scripts to run the LangExtract proof of concept and compare it with our current extraction system.

## Prerequisites

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Set Up API Keys

LangExtract requires a Google Gemini API key:

```bash
# Get your API key from: https://aistudio.google.com/app/apikey
export GOOGLE_API_KEY='your-gemini-api-key-here'

# Or add to your .env file:
echo "GOOGLE_API_KEY=your-gemini-api-key-here" >> .env
```

## Running the POC

### Option 1: Quick Test (Recommended First)

Test on first 10 pages only to verify setup:

```bash
cd backend/scripts

# Run LangExtract POC
python langextract_poc.py ../../BIRD_V8.pdf \
  --max-pages 10 \
  --output-dir ./langextract_results

# Run baseline extraction
python baseline_extraction.py ../../BIRD_V8.pdf \
  --max-pages 10 \
  --output-dir ./baseline_results
```

### Option 2: Full Extraction

Process entire script (will take longer):

```bash
# LangExtract - Full script
python langextract_poc.py ../../BIRD_V8.pdf \
  --output-dir ./langextract_results

# Baseline - Full script  
python baseline_extraction.py ../../BIRD_V8.pdf \
  --output-dir ./baseline_results
```

### Option 3: Test Both Sample Scripts

```bash
# BIRD_V8.pdf
python langextract_poc.py ../../BIRD_V8.pdf --max-pages 20
python baseline_extraction.py ../../BIRD_V8.pdf --max-pages 20

# Script_Powerlessness.pdf
python langextract_poc.py ../../Script_Powerlessness.pdf --max-pages 20
python baseline_extraction.py ../../Script_Powerlessness.pdf --max-pages 20
```

## Output Files

### LangExtract Output (`./langextract_results/`)

- `{script_name}_{timestamp}.jsonl` - Extraction data in JSONL format
- `{script_name}_{timestamp}_visualization.html` - **Interactive HTML visualization**
- `{script_name}_summary.md` - Summary report with statistics

### Baseline Output (`./baseline_results/`)

- `{script_name}_baseline_{timestamp}.json` - Extraction data in JSON format
- `{script_name}_baseline_summary.md` - Summary report

## Viewing Results

### 1. Open Interactive Visualization

```bash
# macOS
open langextract_results/*_visualization.html

# Linux
xdg-open langextract_results/*_visualization.html

# Windows
start langextract_results/*_visualization.html
```

### 2. Review Summary Reports

```bash
# LangExtract summary
cat langextract_results/*_summary.md

# Baseline summary
cat baseline_results/*_baseline_summary.md
```

### 3. Compare Extraction Counts

```bash
# LangExtract stats
grep "Total extractions:" langextract_results/*_summary.md

# Baseline stats
grep "Total" baseline_results/*_baseline_summary.md
```

## Command-Line Options

### langextract_poc.py

```
usage: langextract_poc.py [-h] [--output-dir OUTPUT_DIR] [--model MODEL]
                          [--max-pages MAX_PAGES]
                          [--extraction-passes EXTRACTION_PASSES]
                          [--max-workers MAX_WORKERS]
                          [--chunk-size CHUNK_SIZE]
                          pdf_path

Options:
  pdf_path              Path to screenplay PDF file
  --output-dir DIR      Output directory (default: ./langextract_results)
  --model MODEL         LLM model (default: gemini-2.0-flash-exp)
  --max-pages N         Max pages to process (default: all)
  --extraction-passes N Number of extraction passes (default: 2)
  --max-workers N       Parallel workers (default: 10)
  --chunk-size N        Character buffer size (default: 2000)
```

### baseline_extraction.py

```
usage: baseline_extraction.py [-h] [--output-dir OUTPUT_DIR]
                              [--max-pages MAX_PAGES]
                              pdf_path

Options:
  pdf_path              Path to screenplay PDF file
  --output-dir DIR      Output directory (default: ./baseline_results)
  --max-pages N         Max pages to process (default: all)
```

## Performance Tuning

### For Faster Extraction

```bash
# Reduce extraction passes (lower recall, faster)
python langextract_poc.py script.pdf --extraction-passes 1

# Increase workers (more parallel processing)
python langextract_poc.py script.pdf --max-workers 20

# Larger chunks (fewer API calls, less accurate)
python langextract_poc.py script.pdf --chunk-size 3000
```

### For Higher Accuracy

```bash
# More extraction passes (higher recall, slower)
python langextract_poc.py script.pdf --extraction-passes 3

# Smaller chunks (more context-aware, more API calls)
python langextract_poc.py script.pdf --chunk-size 1000
```

## Troubleshooting

### "No GOOGLE_API_KEY found"

```bash
# Check if key is set
echo $GOOGLE_API_KEY

# Set it temporarily
export GOOGLE_API_KEY='your-key-here'

# Or add to .env file
echo "GOOGLE_API_KEY=your-key-here" >> ../backend/.env
```

### "ModuleNotFoundError: No module named 'langextract'"

```bash
cd backend
pip install langextract
```

### Dependency Conflicts

The POC may show warnings about httpx/anyio version conflicts with Supabase. This is expected and won't affect the POC. For production, we'll need to resolve these.

### Rate Limiting

If you hit Gemini API rate limits:

```bash
# Reduce workers
python langextract_poc.py script.pdf --max-workers 5

# Or process fewer pages
python langextract_poc.py script.pdf --max-pages 10
```

## Next Steps After Running POC

1. **Review HTML Visualization**
   - Open the interactive HTML file
   - Check source grounding accuracy
   - Evaluate extraction quality

2. **Compare Metrics**
   - Extraction counts (LangExtract vs Baseline)
   - Processing time
   - Accuracy of extractions

3. **Document Findings**
   - Fill out `docs/LANGEXTRACT_POC_RESULTS.md`
   - Note pros/cons of each system
   - Recommend go/no-go for Phase 2

4. **Share Results**
   - Send HTML visualization to stakeholders
   - Present comparison metrics
   - Discuss integration strategy

## Cost Estimation

### Gemini API Pricing (as of 2025)

- **gemini-2.0-flash-exp**: Free tier available, then ~$0.075 per 1M input tokens
- **Average screenplay**: ~50,000 tokens
- **Estimated cost per script**: $0.004 - $0.01 (less than 1 cent)

### Comparison with Current System

- Current OpenAI GPT-4: ~$0.03 per 1K tokens = ~$1.50 per script
- LangExtract with Gemini: ~$0.01 per script
- **Potential savings**: ~99% cost reduction

## Files Created

```
backend/
├── services/
│   ├── langextract_schema.py      # Extraction schema definitions
│   └── langextract_examples.py    # Few-shot examples
├── scripts/
│   ├── langextract_poc.py         # Main POC script
│   ├── baseline_extraction.py     # Baseline comparison script
│   └── README_LANGEXTRACT_POC.md  # This file
└── requirements.txt               # Updated with langextract
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review LangExtract docs: https://github.com/google/langextract
3. Check Gemini API docs: https://ai.google.dev/gemini-api/docs
