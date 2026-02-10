"""
Science2Go Processors Module
PDF, text, and audio processing components
"""

from .pdf_metadata import PDFMetadataExtractor, extract_pdf_metadata

# PDF-to-Markdown conversion (optional -- requires marker-pdf + PyTorch)
try:
    from .pdf_converter import (
        PDFToMarkdownConverter, pdf_converter, MARKER_AVAILABLE,
        detect_pdf_type, fast_extract_text,
        CONVERSION_MODES, MODE_FAST_EXTRACT, MODE_MARKER_NO_OCR, MODE_FULL_PIPELINE,
    )
except ImportError:
    MARKER_AVAILABLE = False
    pdf_converter = None
    detect_pdf_type = None
    fast_extract_text = None

# Audio generation (optional -- requires google-cloud-texttospeech)
try:
    from .audio_generator import (
        AudioGenerator, audio_generator, TTS_AVAILABLE,
        AUDIO_FORMATS, BITRATE_OPTIONS,
        CHIRP3_HD_MALE_VOICES, CHIRP3_HD_FEMALE_VOICES, ALL_CHIRP3_HD_VOICES,
        voice_display_name, voice_full_name,
        chunk_text_for_tts,
    )
except ImportError:
    TTS_AVAILABLE = False
    audio_generator = None

__all__ = [
    'PDFMetadataExtractor', 'extract_pdf_metadata',
    'PDFToMarkdownConverter', 'pdf_converter', 'MARKER_AVAILABLE',
    'detect_pdf_type', 'fast_extract_text',
    'CONVERSION_MODES', 'MODE_FAST_EXTRACT', 'MODE_MARKER_NO_OCR', 'MODE_FULL_PIPELINE',
    'AudioGenerator', 'audio_generator', 'TTS_AVAILABLE',
    'AUDIO_FORMATS', 'BITRATE_OPTIONS',
    'CHIRP3_HD_MALE_VOICES', 'CHIRP3_HD_FEMALE_VOICES', 'ALL_CHIRP3_HD_VOICES',
    'voice_display_name', 'voice_full_name',
    'chunk_text_for_tts',
]
