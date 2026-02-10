"""
PDF to Markdown Converter for Science2Go
Uses marker-pdf for high-quality PDF-to-markdown conversion with structure preservation.
Handles two-column layouts, removes headers/footers, preserves section hierarchy.
Models are loaded lazily and cached for reuse across conversions.

Conversion modes:
  - Fast Extract: pdftext direct extraction, no ML models (~1-5s)
  - Marker (no OCR): marker-pdf layout pipeline without OCR recognition
  - Full Pipeline: marker-pdf with OCR for scanned/image PDFs
"""

import threading
from pathlib import Path
from typing import Optional, Dict, Any, Callable

import PyPDF2
from pdftext.extraction import plain_text_output

# Graceful import -- marker-pdf is optional and heavy (requires PyTorch)
try:
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    from marker.output import text_from_rendered
    MARKER_AVAILABLE = True
except ImportError:
    MARKER_AVAILABLE = False

# Conversion mode constants
MODE_FAST_EXTRACT = "Fast Extract"
MODE_MARKER_NO_OCR = "Marker (no OCR)"
MODE_FULL_PIPELINE = "Full Pipeline"
CONVERSION_MODES = [MODE_FAST_EXTRACT, MODE_MARKER_NO_OCR, MODE_FULL_PIPELINE]


def detect_pdf_type(pdf_path: str, sample_pages: int = 3,
                    min_chars_per_page: int = 100) -> Dict[str, Any]:
    """
    Detect whether a PDF has native (embedded) text or is scanned/image-based.
    Uses PyPDF2 only -- no ML models, runs in 10-50ms.

    Args:
        pdf_path: Path to the PDF file.
        sample_pages: Number of pages to sample from the start.
        min_chars_per_page: Minimum non-whitespace chars per page to count as native text.

    Returns:
        Dict with keys:
            has_native_text (bool): True if PDF has extractable text
            recommendation (str): recommended conversion mode constant
            avg_chars_per_page (float): Average non-whitespace character count
            pages_sampled (int): Number of pages checked
            detail (str): Human-readable explanation
    """
    try:
        reader = PyPDF2.PdfReader(pdf_path)
        total_pages = len(reader.pages)
        pages_to_check = min(sample_pages, total_pages)

        char_counts = []
        for i in range(pages_to_check):
            text = reader.pages[i].extract_text() or ""
            non_ws = len(text.replace(" ", "").replace("\n", "").replace("\t", ""))
            char_counts.append(non_ws)

        avg_chars = sum(char_counts) / len(char_counts) if char_counts else 0
        has_text = avg_chars >= min_chars_per_page

        if has_text:
            detail = (f"Native text detected ({avg_chars:.0f} chars/page avg "
                      f"across {pages_to_check} pages)")
            recommendation = MODE_FAST_EXTRACT
        else:
            detail = (f"Little/no embedded text ({avg_chars:.0f} chars/page avg "
                      f"across {pages_to_check} pages)")
            recommendation = MODE_FULL_PIPELINE

        return {
            "has_native_text": has_text,
            "recommendation": recommendation,
            "avg_chars_per_page": avg_chars,
            "pages_sampled": pages_to_check,
            "detail": detail,
        }
    except Exception as e:
        return {
            "has_native_text": False,
            "recommendation": MODE_FULL_PIPELINE,
            "avg_chars_per_page": 0,
            "pages_sampled": 0,
            "detail": f"Detection failed: {e}",
        }


def fast_extract_text(pdf_path: str,
                      progress_callback: Optional[Callable[[str], None]] = None
                      ) -> Dict[str, Any]:
    """
    Extract text directly from a native PDF using pdftext.
    No ML models, no OCR -- runs in ~1-5 seconds.

    Args:
        pdf_path: Path to the PDF file.
        progress_callback: Optional callable(str) for status messages.

    Returns:
        Same result dict format as PDFToMarkdownConverter.convert().
    """
    result = {
        'success': False,
        'markdown': '',
        'images': {},
        'error': None,
        'pdf_path': pdf_path,
        'conversion_mode': MODE_FAST_EXTRACT,
    }

    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        result['error'] = f"PDF file not found: {pdf_path}"
        return result

    if not pdf_file.suffix.lower() == '.pdf':
        result['error'] = f"File is not a PDF: {pdf_file.name}"
        return result

    try:
        if progress_callback:
            progress_callback(f"Fast extracting text from {pdf_file.name}...")

        text = plain_text_output(pdf_path, sort=True)

        result['success'] = True
        result['markdown'] = text

        if progress_callback:
            word_count = len(text.split())
            progress_callback(f"Fast extraction complete: {word_count:,} words extracted.")

    except Exception as e:
        result['error'] = str(e)
        if progress_callback:
            progress_callback(f"Fast extraction failed: {e}")

    return result


class PDFToMarkdownConverter:
    """
    Converts PDF files to structured Markdown using marker-pdf.

    Models are loaded lazily on first use and cached as a singleton.
    All public methods are safe to call from background threads.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern -- ensures only one model dict exists in memory."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._artifact_dict = None
                cls._instance._models_loaded = False
        return cls._instance

    @property
    def is_available(self) -> bool:
        """Check if marker-pdf is installed and available."""
        return MARKER_AVAILABLE

    @property
    def models_loaded(self) -> bool:
        """Check if models have been loaded into memory."""
        return self._models_loaded

    def load_models(self, progress_callback: Optional[Callable[[str], None]] = None):
        """
        Load marker-pdf models. This is slow (~5-10s first time).
        Safe to call from a background thread.

        Args:
            progress_callback: Optional callable(str) for status messages.
        """
        if not MARKER_AVAILABLE:
            raise RuntimeError("marker-pdf is not installed. Install with: pip install marker-pdf")

        if self._models_loaded:
            return

        with self._lock:
            if self._models_loaded:
                return  # double-check after acquiring lock

            if progress_callback:
                progress_callback("Loading PDF conversion models (first time may take a moment)...")

            self._artifact_dict = create_model_dict()
            self._models_loaded = True

            if progress_callback:
                progress_callback("PDF conversion models loaded successfully.")

    def convert(self, pdf_path: str,
                disable_ocr: Optional[bool] = None,
                progress_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """
        Convert a PDF file to Markdown text.

        Args:
            pdf_path: Absolute path to the PDF file.
            disable_ocr: If True, skip OCR (faster for native PDFs).
                         If False or None, use marker-pdf defaults.
            progress_callback: Optional callable(str) for status messages.

        Returns:
            Dict with keys:
                success (bool): Whether conversion succeeded
                markdown (str): The converted markdown text
                images (dict): Extracted images from the PDF
                error (str or None): Error message if conversion failed
                pdf_path (str): The original PDF path
                conversion_mode (str): The mode used for conversion
        """
        result = {
            'success': False,
            'markdown': '',
            'images': {},
            'error': None,
            'pdf_path': pdf_path,
            'conversion_mode': MODE_MARKER_NO_OCR if disable_ocr else MODE_FULL_PIPELINE,
        }

        if not MARKER_AVAILABLE:
            result['error'] = (
                "marker-pdf is not installed.\n"
                "Install with: pip install marker-pdf"
            )
            return result

        # Validate input
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            result['error'] = f"PDF file not found: {pdf_path}"
            return result

        if not pdf_file.suffix.lower() == '.pdf':
            result['error'] = f"File is not a PDF: {pdf_file.name}"
            return result

        try:
            # Ensure models are loaded (lazy init)
            if not self._models_loaded:
                self.load_models(progress_callback)

            if progress_callback:
                ocr_note = " (OCR skipped)" if disable_ocr else ""
                progress_callback(f"Converting {pdf_file.name} to Markdown{ocr_note}...")

            # Build config and create converter for this run
            converter_config = {}
            if disable_ocr:
                converter_config["disable_ocr"] = True

            converter = PdfConverter(
                artifact_dict=self._artifact_dict, config=converter_config
            )

            # Run marker-pdf conversion
            rendered = converter(pdf_path)
            text, _, images = text_from_rendered(rendered)

            result['success'] = True
            result['markdown'] = text
            result['images'] = images if images else {}

            if progress_callback:
                word_count = len(text.split())
                progress_callback(f"Conversion complete: {word_count:,} words extracted.")

        except Exception as e:
            result['error'] = str(e)
            if progress_callback:
                progress_callback(f"Conversion failed: {e}")

        return result


# Module-level convenience singleton
pdf_converter = PDFToMarkdownConverter()
