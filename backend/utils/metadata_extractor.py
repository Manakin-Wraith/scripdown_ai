"""
Advanced Script Cover Page Metadata Extractor

Multi-strategy extraction system that handles layout variations:
- Positional analysis (top/middle/bottom regions)
- Pattern matching with confidence scoring
- Multiple writer name detection strategies
- Contact validation
- Production company detection
"""

import re
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    print("Warning: pdfplumber not installed. Metadata extraction will be limited.")


@dataclass
class ExtractionResult:
    """Result with confidence score."""
    value: Optional[str]
    confidence: float
    method: str


class AdvancedMetadataExtractor:
    """
    Enhanced metadata extractor with multi-strategy approach.
    Handles various cover page layouts and formats.
    """
    
    # Enhanced regex patterns with multiple variations
    WRITER_PATTERNS = [
        (r'(?:written\s+by|screenplay\s+by)\s*:?\s*([^\n]+)', 0.95),
        (r'^by\s+([^\n]+)', 0.90),
        (r'By\n+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})(?:\n|$)', 0.92),  # "By" on one line, name on next
        (r'([A-Z][a-zöüä]+\s+[A-Z][a-zöüä]+)\s*&\s*([A-Z][a-zöüä]+\s+[A-Z][a-zöüä]+)', 0.85),
        (r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)$', 0.70),  # Proper noun line
    ]
    
    PHONE_PATTERNS = [
        (r'\+\d{2,3}\s*\d{2}\s*\d{3}\s*\d{4,5}', 0.95),  # +27 82 786 96 94
        (r'\+\d{2,3}\s*\d{2}\s*\d{3}\s*\d{4}', 0.95),    # +27 11 447 5193
        (r'\(\d{3}\)\s*\d{3}[-\s]?\d{4}', 0.90),         # (555) 123-4567
        (r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}', 0.85),        # 555-123-4567
    ]
    
    EMAIL_PATTERN = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
    
    DRAFT_PATTERNS = [
        (r'((?:first|second|third|final|shooting|production|revised)\s+draft)', 0.95),
        (r'(draft\s+\d+)', 0.85),
        (r'(revision\s+\d+)', 0.80),
    ]
    
    DATE_PATTERN = r'(\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b)'
    
    COPYRIGHT_PATTERNS = [
        (r'(©\s*\d{4}[^\n]*)', 0.95),
        (r'(copyright\s+©?\s*\d{4}[^\n]*)', 0.90),
    ]
    
    WGA_PATTERN = r'(WGA\s*#?\s*\d+)'
    
    CREDITS_PATTERNS = [
        (r'(based\s+on[^\n]+(?:\n[^\n]+){0,2})', 0.95),
        (r'(story\s+by\s*:?\s*[^\n]+)', 0.90),
        (r'(adapted\s+from[^\n]+)', 0.85),
    ]
    
    PRODUCTION_PATTERNS = [
        (r'([A-Z\s]{3,}PRODUCTIONS?)', 0.90),
        (r'([A-Z\s]{3,}PICTURES?)', 0.90),
        (r'([A-Z\s]{3,}FILMS?)', 0.90),
        (r'([A-Z\s]{3,}ENTERTAINMENT)', 0.85),
    ]
    
    def __init__(self, pdf_path: str):
        """
        Initialize the metadata extractor.
        
        Args:
            pdf_path: Path to the PDF file
        """
        self.pdf_path = pdf_path
        self.full_text = ""
        self.regions = {}
        self.metadata = {}
    
    def extract(self) -> Dict[str, Optional[str]]:
        """
        Extract all metadata from the cover page using multi-strategy approach.
        
        Returns:
            Dictionary containing extracted metadata with confidence scores
        """
        if not PDFPLUMBER_AVAILABLE:
            return self._empty_metadata()
        
        # Extract text with layout information
        self._extract_with_layout()
        
        if not self.full_text:
            return self._empty_metadata()
        
        # Extract individual fields using multi-strategy approach
        writer_result = self._extract_writer_multi_strategy()
        email_result = self._extract_email_validated()
        phone_result = self._extract_phone_multi_pattern()
        draft_result = self._extract_draft_multi_pattern()
        
        self.metadata = {
            'writer_name': writer_result.value,
            'writer_email': email_result.value,
            'writer_phone': phone_result.value,
            'draft_version': draft_result.value,
            'draft_date': self._extract_date(),
            'copyright_info': self._extract_copyright_multi_pattern(),
            'wga_registration': self._extract_wga(),
            'additional_credits': self._extract_credits_multi_pattern(),
        }
        
        # Log confidence scores for debugging
        print(f"Extraction confidence scores:")
        print(f"  Writer: {writer_result.confidence:.2f} ({writer_result.method})")
        print(f"  Email: {email_result.confidence:.2f} ({email_result.method})")
        print(f"  Phone: {phone_result.confidence:.2f} ({phone_result.method})")
        print(f"  Draft: {draft_result.confidence:.2f} ({draft_result.method})")
        
        return self.metadata
    
    def _extract_with_layout(self) -> None:
        """Extract text with layout information (top/middle/bottom regions)."""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                if len(pdf.pages) == 0:
                    return
                
                first_page = pdf.pages[0]
                self.full_text = first_page.extract_text() or ""
                
                # Get page dimensions
                height = first_page.height
                width = first_page.width
                
                # Define regions (top 1/3, middle 1/3, bottom 1/3)
                regions_bbox = {
                    'top': (0, 0, width, height * 0.33),
                    'middle': (0, height * 0.33, width, height * 0.66),
                    'bottom': (0, height * 0.66, width, height),
                }
                
                # Extract text from each region
                for region_name, bbox in regions_bbox.items():
                    try:
                        region_text = first_page.within_bbox(bbox).extract_text() or ""
                        self.regions[region_name] = region_text
                    except Exception as e:
                        print(f"Error extracting {region_name} region: {e}")
                        self.regions[region_name] = ""
                        
        except Exception as e:
            print(f"Error in layout extraction: {e}")
            self.full_text = ""
            self.regions = {}
    
    def _extract_writer_multi_strategy(self) -> ExtractionResult:
        """Extract writer name using multiple strategies with confidence scoring."""
        best_result = ExtractionResult(None, 0.0, "none")
        
        # Strategy 1: Pattern matching in middle region (highest confidence)
        middle_text = self.regions.get('middle', '')
        for pattern, base_confidence in self.WRITER_PATTERNS:
            match = re.search(pattern, middle_text, re.IGNORECASE | re.MULTILINE)
            if match:
                writer_name = match.group(1).strip() if match.lastindex == 1 else f"{match.group(1)} & {match.group(2)}"
                confidence = base_confidence * 1.1  # Boost for middle region
                if confidence > best_result.confidence:
                    best_result = ExtractionResult(writer_name, confidence, f"middle_pattern_{pattern[:20]}")
        
        # Strategy 2: Pattern matching in full text
        if best_result.confidence < 0.8:
            for pattern, base_confidence in self.WRITER_PATTERNS:
                match = re.search(pattern, self.full_text, re.IGNORECASE | re.MULTILINE)
                if match:
                    writer_name = match.group(1).strip() if match.lastindex == 1 else f"{match.group(1)} & {match.group(2)}"
                    if base_confidence > best_result.confidence:
                        best_result = ExtractionResult(writer_name, base_confidence, f"full_pattern_{pattern[:20]}")
        
        # Strategy 3: Look for "By" followed by name on next line
        if best_result.confidence < 0.85:
            lines = [l.strip() for l in self.full_text.split('\n') if l.strip()]
            for i, line in enumerate(lines):
                if line.lower() == 'by' and i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if self._is_likely_name(next_line):
                        if 0.88 > best_result.confidence:
                            best_result = ExtractionResult(next_line, 0.88, "by_next_line")
                        break
        
        # Strategy 4: Heuristic - find proper noun after title
        if best_result.confidence < 0.7:
            lines = [l.strip() for l in middle_text.split('\n') if l.strip()]
            title_found = False
            for line in lines:
                if not title_found and self._is_likely_title(line):
                    title_found = True
                    continue
                if title_found and self._is_likely_name(line):
                    best_result = ExtractionResult(line, 0.65, "heuristic_after_title")
                    break
        
        return best_result
    
    def _is_likely_title(self, line: str) -> bool:
        """Check if line is likely a script title."""
        if len(line) > 50 or len(line) < 2:
            return False
        if line.lower() in ['written by', 'by', 'screenplay by', 'based on']:
            return False
        return line.isupper() or line.istitle()
    
    def _is_likely_name(self, line: str) -> bool:
        """Check if line is likely a person's name."""
        if len(line) > 50 or len(line) < 5:
            return False
        # Check for proper noun pattern (capitalized words)
        words = line.split()
        if len(words) < 2 or len(words) > 4:
            return False
        return all(word[0].isupper() for word in words if word)
    
    def _extract_email_validated(self) -> ExtractionResult:
        """Extract and validate email address."""
        # Emails are usually in bottom region
        bottom_text = self.regions.get('bottom', '')
        
        match = re.search(self.EMAIL_PATTERN, bottom_text)
        if match:
            email = match.group(1).strip()
            # Basic validation
            if '@' in email and '.' in email.split('@')[1]:
                return ExtractionResult(email, 0.95, "bottom_region_validated")
        
        # Fallback to full text
        match = re.search(self.EMAIL_PATTERN, self.full_text)
        if match:
            email = match.group(1).strip()
            if '@' in email and '.' in email.split('@')[1]:
                return ExtractionResult(email, 0.85, "full_text_validated")
        
        return ExtractionResult(None, 0.0, "none")
    
    def _extract_phone_multi_pattern(self) -> ExtractionResult:
        """Extract phone number using multiple patterns."""
        # Phones are usually in bottom region
        bottom_text = self.regions.get('bottom', '')
        
        best_result = ExtractionResult(None, 0.0, "none")
        
        for pattern, confidence in self.PHONE_PATTERNS:
            match = re.search(pattern, bottom_text)
            if match and confidence > best_result.confidence:
                best_result = ExtractionResult(match.group(0).strip(), confidence * 1.1, f"bottom_{pattern[:20]}")
        
        # Fallback to full text
        if best_result.confidence < 0.8:
            for pattern, confidence in self.PHONE_PATTERNS:
                match = re.search(pattern, self.full_text)
                if match and confidence > best_result.confidence:
                    best_result = ExtractionResult(match.group(0).strip(), confidence, f"full_{pattern[:20]}")
        
        return best_result
    
    def _extract_draft_multi_pattern(self) -> ExtractionResult:
        """Extract draft version using multiple patterns."""
        best_result = ExtractionResult(None, 0.0, "none")
        
        for pattern, confidence in self.DRAFT_PATTERNS:
            match = re.search(pattern, self.full_text, re.IGNORECASE)
            if match and confidence > best_result.confidence:
                draft = match.group(1).strip().title()
                best_result = ExtractionResult(draft, confidence, f"pattern_{pattern[:20]}")
        
        return best_result
    
    def _extract_date(self) -> Optional[str]:
        """Extract date from the text."""
        match = re.search(self.DATE_PATTERN, self.full_text)
        if match:
            return match.group(1).strip()
        return None
    
    def _extract_copyright_multi_pattern(self) -> Optional[str]:
        """Extract copyright information using multiple patterns."""
        # Copyright usually in bottom region
        bottom_text = self.regions.get('bottom', '')
        
        for pattern, confidence in self.COPYRIGHT_PATTERNS:
            match = re.search(pattern, bottom_text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Fallback to full text
        for pattern, confidence in self.COPYRIGHT_PATTERNS:
            match = re.search(pattern, self.full_text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_wga(self) -> Optional[str]:
        """Extract WGA registration number from the text."""
        match = re.search(self.WGA_PATTERN, self.full_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None
    
    def _extract_credits_multi_pattern(self) -> Optional[str]:
        """Extract additional credits using multiple patterns."""
        credits = []
        
        # Credits usually in middle region
        middle_text = self.regions.get('middle', '')
        
        for pattern, confidence in self.CREDITS_PATTERNS:
            match = re.search(pattern, middle_text, re.IGNORECASE)
            if match:
                credit_text = match.group(1).strip()
                # Clean up multi-line credits
                credit_text = ' '.join(credit_text.split())
                if credit_text not in credits:
                    credits.append(credit_text)
        
        # Fallback to full text if nothing found
        if not credits:
            for pattern, confidence in self.CREDITS_PATTERNS:
                match = re.search(pattern, self.full_text, re.IGNORECASE)
                if match:
                    credit_text = match.group(1).strip()
                    credit_text = ' '.join(credit_text.split())
                    if credit_text not in credits:
                        credits.append(credit_text)
        
        return ' | '.join(credits) if credits else None
    
    def _empty_metadata(self) -> Dict[str, None]:
        """Return empty metadata dictionary."""
        return {
            'writer_name': None,
            'writer_email': None,
            'writer_phone': None,
            'draft_version': None,
            'draft_date': None,
            'copyright_info': None,
            'wga_registration': None,
            'additional_credits': None,
        }


def extract_metadata(pdf_path: str) -> Dict[str, Optional[str]]:
    """
    Convenience function to extract metadata from a PDF using advanced extraction.
    
    Args:
        pdf_path: Path to the PDF file
    
    Returns:
        Dictionary containing extracted metadata
    """
    extractor = AdvancedMetadataExtractor(pdf_path)
    return extractor.extract()
