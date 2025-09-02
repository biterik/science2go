"""
Science2Go Processors Module
PDF, text, and audio processing components
"""

from .pdf_metadata import PDFMetadataExtractor, extract_pdf_metadata

__all__ = ['PDFMetadataExtractor', 'extract_pdf_metadata']
