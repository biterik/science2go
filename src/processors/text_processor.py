"""
Advanced Text Processor for Science2Go
Cleanup pass: remove document artifacts, expand abbreviations/symbols, preserve content.
Uses non-overlapping chunking with context preamble for continuity.
"""

import os
import time
import re
import sys
import threading
from typing import Optional, List, Tuple, Dict, Any, Callable
from pathlib import Path
import json

# Fix import path issues
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️ Google Generative AI not available. Install with: pip install google-generativeai")

# Import template manager with error handling
try:
    from src.templates.template_manager import template_manager
    TEMPLATE_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Template manager import failed: {e}")
    TEMPLATE_MANAGER_AVAILABLE = False
    template_manager = None

# Import chunking configuration
try:
    from src.config.chunking_settings import CHUNKING_CONFIG, CHUNK_BREAK_PATTERNS
except ImportError:
    print("⚠️ Chunking settings import failed, using defaults")
    CHUNKING_CONFIG = {
        "max_chunk_size": 30000,
        "context_preamble_size": 500,
        "min_chunk_size": 5000,
        "chunk_delay_seconds": 1.0,
        "max_retries": 3,
        "retry_delay_seconds": 2.0,
    }
    CHUNK_BREAK_PATTERNS = [
        r'\n\n#+\s',
        r'\n\n\d+\.?\s+[A-Z]',
        r'\n\n[A-Z][A-Za-z\s]+:?\n',
        r'\n\n\d+\.\d+\.?\s',
        r'\n\n[a-z]\)\s',
        r'\n\n[A-Z]',
        r'\n\n\w',
        r'\.[\s\n]+[A-Z]',
    ]


class ProcessingAnalytics:
    """Track processing metrics and statistics"""

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.input_chars = 0
        self.output_chars = 0
        self.chunks_processed = 0
        self.total_chunks = 0
        self.failed_chunks = 0
        self.retry_count = 0
        self.template_used = ""
        self.errors = []

    def start_processing(self, input_text: str, template_name: str):
        """Start processing timer and record initial metrics"""
        self.start_time = time.time()
        self.input_chars = len(input_text)
        self.template_used = template_name
        self.chunks_processed = 0
        self.failed_chunks = 0
        self.retry_count = 0
        self.errors = []

    def record_chunk_completion(self, success: bool = True):
        """Record completion of a chunk"""
        self.chunks_processed += 1
        if not success:
            self.failed_chunks += 1

    def record_retry(self):
        """Record a retry attempt"""
        self.retry_count += 1

    def record_error(self, error_msg: str):
        """Record an error"""
        self.errors.append(error_msg)

    def finish_processing(self, output_text: str):
        """Finish processing and calculate final metrics"""
        self.end_time = time.time()
        self.output_chars = len(output_text) if output_text else 0

    def get_metrics(self) -> Dict[str, Any]:
        """Get all processing metrics"""
        processing_time = (self.end_time - self.start_time) if self.start_time and self.end_time else 0
        reduction_percentage = ((self.input_chars - self.output_chars) / self.input_chars * 100) if self.input_chars > 0 else 0
        success_rate = ((self.chunks_processed - self.failed_chunks) / max(self.chunks_processed, 1)) * 100

        return {
            'processing_time': processing_time,
            'input_chars': self.input_chars,
            'output_chars': self.output_chars,
            'reduction_percentage': reduction_percentage,
            'total_chunks': self.total_chunks,
            'chunks_processed': self.chunks_processed,
            'failed_chunks': self.failed_chunks,
            'retry_count': self.retry_count,
            'success_rate': success_rate,
            'template_used': self.template_used,
            'errors': self.errors
        }


class TTSOptimizer:
    """Text optimization for symbol/unit/abbreviation expansion.

    Provides two modes:
    - optimize_for_cleanup(): symbol/unit/abbreviation conversion + punctuation fixes.
      Used by the cleanup pass. Does NOT modify structure (no bracket removal,
      no sentence splitting, no header conversion).
    - optimize_for_tts(): full TTS formatting including speech cleanup.
      Preserved for future Pass 2 (TTS optimization).
    """

    def __init__(self):
        # Symbol conversions for speech
        self.symbol_map = {
            '%': ' percent',
            '&': ' and',
            '±': ' plus or minus',
            '°': ' degrees',
            '×': ' times',
            '÷': ' divided by',
            '≈': ' approximately equals',
            '≤': ' less than or equal to',
            '≥': ' greater than or equal to',
            '→': ' leads to',
            '←': ' comes from',
            '↔': ' is equivalent to',
            'α': ' alpha',
            'β': ' beta',
            'γ': ' gamma',
            'δ': ' delta',
            'ε': ' epsilon',
            'λ': ' lambda',
            'μ': ' mu',
            'π': ' pi',
            'σ': ' sigma',
            'τ': ' tau',
            'φ': ' phi',
            'χ': ' chi',
            'ψ': ' psi',
            'ω': ' omega',
        }

        # Abbreviation expansions
        self.abbreviation_map = {
            'e.g.': 'for example',
            'i.e.': 'that is',
            'etc.': 'etcetera',
            'vs.': 'versus',
            'cf.': 'compare',
            'ca.': 'approximately',
            'et al.': 'and others',
            'w.r.t.': 'with respect to',
            'PhD': 'Doctor of Philosophy',
            'MSc': 'Master of Science',
            'BSc': 'Bachelor of Science',
        }

        # Unit conversions
        self.unit_map = {
            'μm': ' micrometers',
            'nm': ' nanometers',
            'mm': ' millimeters',
            'cm': ' centimeters',
            'km': ' kilometers',
            'μg': ' micrograms',
            'mg': ' milligrams',
            'kg': ' kilograms',
            'GPa': ' gigapascals',
            'MPa': ' megapascals',
            'kPa': ' kilopascals',
            'Pa': ' pascals',
            '°C': ' degrees Celsius',
            '°F': ' degrees Fahrenheit',
            'K': ' Kelvin',
            'Hz': ' hertz',
            'kHz': ' kilohertz',
            'MHz': ' megahertz',
            'GHz': ' gigahertz',
        }

    # ── Cleanup-only mode (Pass 1) ─────────────────────────────────

    def optimize_for_cleanup(self, text: str) -> str:
        """Apply cleanup-only optimizations (no TTS-specific formatting).

        Keeps: symbol conversion, abbreviation expansion, unit conversion,
               punctuation artifact fixes.
        Omits: bracket removal, sentence splitting, header conversion,
               'pause' word stripping.
        """
        text = self.convert_symbols(text)
        text = self.expand_abbreviations(text)
        text = self.convert_units(text)
        text = self._fix_punctuation_for_cleanup(text)
        return text

    def _fix_punctuation_for_cleanup(self, text: str) -> str:
        """Fix punctuation artifacts from AI processing (cleanup mode).

        Does NOT strip 'pause' words or modify document structure.
        """
        text = re.sub(r'\.\s*,', '.', text)   # Fix ". ,"
        text = re.sub(r',\s*\.', '.', text)   # Fix ", ."
        text = re.sub(r'\.\s*;', '.', text)   # Fix ". ;"
        text = re.sub(r';\s*\.', '.', text)   # Fix "; ."
        # Normalize runs of 3+ spaces but preserve single newlines and paragraph breaks
        text = re.sub(r'[ \t]{2,}', ' ', text)
        return text.strip()

    # ── Full TTS mode (future Pass 2) ──────────────────────────────

    def optimize_for_tts(self, text: str) -> str:
        """Apply full TTS optimizations including speech cleanup.

        Reserved for future Pass 2 (TTS formatting).
        """
        text = self.convert_symbols(text)
        text = self.expand_abbreviations(text)
        text = self.convert_units(text)
        text = self.clean_for_speech(text)
        text = self.fix_punctuation_issues(text)
        return text

    # ── Shared helpers ──────────────────────────────────────────────

    def convert_symbols(self, text: str) -> str:
        """Convert mathematical and special symbols to spoken form"""
        for symbol, spoken in self.symbol_map.items():
            text = text.replace(symbol, spoken)
        return text

    def expand_abbreviations(self, text: str) -> str:
        """Expand abbreviations for better speech"""
        for abbrev, expansion in self.abbreviation_map.items():
            pattern = r'\b' + re.escape(abbrev) + r'\b'
            text = re.sub(pattern, expansion, text, flags=re.IGNORECASE)
        return text

    def convert_units(self, text: str) -> str:
        """Convert units to spoken form"""
        for unit, spoken in self.unit_map.items():
            pattern = r'(\d+(?:\.\d+)?)\s*' + re.escape(unit) + r'\b'
            replacement = r'\1' + spoken
            text = re.sub(pattern, replacement, text)
        return text

    # ── TTS-only helpers (not used in cleanup mode) ─────────────────

    def clean_for_speech(self, text: str) -> str:
        """Clean text for speech — TTS pass only, not used in cleanup."""
        text = re.sub(r'[()[\]{}]', '', text)
        text = re.sub(r'--+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\.{2,}', '.', text)
        text = re.sub(r'^#{1,6}\s*(.+)$', r'\1 section.', text, flags=re.MULTILINE)

        sentences = text.split('. ')
        processed_sentences = []
        for sentence in sentences:
            if len(sentence) > 200:
                parts = re.split(r'(,\s+(?:which|that|who|and|but|or|however|moreover|furthermore))', sentence)
                if len(parts) > 2:
                    current_part = ""
                    for part in parts:
                        if len(current_part + part) > 100 and current_part:
                            processed_sentences.append(current_part.strip())
                            current_part = part
                        else:
                            current_part += part
                    if current_part:
                        processed_sentences.append(current_part.strip())
                else:
                    processed_sentences.append(sentence)
            else:
                processed_sentences.append(sentence)
        return '. '.join(processed_sentences)

    def fix_punctuation_issues(self, text: str) -> str:
        """Fix punctuation artifacts — TTS pass only."""
        text = re.sub(r'\.\s*,', '.', text)
        text = re.sub(r',\s*\.', '.', text)
        text = re.sub(r'\.\s*;', '.', text)
        text = re.sub(r';\s*\.', '.', text)
        text = re.sub(r'\bpause\b\.?\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()


class AdvancedTextProcessor:
    """Text processor with non-overlapping chunking and context preamble.

    Chunks are split at natural break points with NO overlap.
    Continuity between chunks is maintained by passing the tail of the
    previous chunk's OUTPUT as a read-only context preamble in the prompt.
    Merging is trivial concatenation — no Jaccard similarity needed.
    """

    def __init__(self):
        self.model = None
        self.analytics = ProcessingAnalytics()
        self.tts_optimizer = TTSOptimizer()
        self.setup_gemini()

        # Processing parameters from config
        self.max_chunk_size = CHUNKING_CONFIG["max_chunk_size"]
        self.min_chunk_size = CHUNKING_CONFIG["min_chunk_size"]
        self.context_preamble_size = CHUNKING_CONFIG["context_preamble_size"]
        self.max_retries = CHUNKING_CONFIG["max_retries"]
        self.base_retry_delay = CHUNKING_CONFIG["retry_delay_seconds"]

    def setup_gemini(self):
        """Initialize Gemini AI model"""
        if not GEMINI_AVAILABLE:
            print("⚠️ Gemini AI not available")
            return

        try:
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                print("⚠️ GEMINI_API_KEY not found in environment variables")
                return

            genai.configure(api_key=api_key)

            generation_config = {
                "temperature": 0.1,  # Very conservative
                "top_p": 0.9,
                "top_k": 40,
                "max_output_tokens": 65536,
                "response_mime_type": "text/plain",
            }

            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]

            self.model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                generation_config=generation_config,
                safety_settings=safety_settings
            )

            print("✅ Gemini AI configured successfully")

        except Exception as e:
            print(f"⚠️ Failed to initialize Gemini: {e}")
            self.model = None

    def smart_chunk_text(self, text: str) -> List[Tuple[str, int, int]]:
        """Split text into non-overlapping chunks at natural break points.

        Returns list of (chunk_text, start_pos, end_pos) tuples.
        Chunks do NOT overlap — continuity is handled via context preamble
        passed to the AI prompt, not via text duplication.
        """
        if len(text) <= self.max_chunk_size:
            return [(text, 0, len(text))]

        chunks = []
        start = 0

        while start < len(text):
            end = min(start + self.max_chunk_size, len(text))

            if end < len(text):
                # Search for a good break point in the tail region of this chunk.
                # Only search from (start + min_chunk_size) onwards to avoid tiny chunks.
                search_start = start + self.min_chunk_size
                if search_start >= end:
                    search_start = start + (end - start) // 2  # fallback: midpoint
                search_region = text[search_start:end]

                best_break = None
                for pattern in CHUNK_BREAK_PATTERNS:
                    matches = list(re.finditer(pattern, search_region, re.MULTILINE))
                    if matches:
                        # Use the LAST match in the search region (maximize chunk size)
                        match = matches[-1]
                        potential_break = search_start + match.start()
                        if potential_break > start:
                            best_break = potential_break
                            break  # Use highest-priority pattern that matched

                if best_break:
                    end = best_break

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append((chunk_text, start, end))

            # Move to immediately after this chunk — NO overlap
            start = end

        return chunks

    def process_chunk_with_retry(self, chunk_text: str, template_name: str, chunk_info: str,
                                progress_callback: Optional[Callable] = None,
                                context: str = "") -> Optional[str]:
        """Process a chunk with retry logic and context preamble."""
        for attempt in range(self.max_retries):
            try:
                if progress_callback:
                    progress_callback(f"Processing {chunk_info} (attempt {attempt + 1})")

                result = self.process_single_chunk(chunk_text, template_name, chunk_info, context=context)
                if result:
                    return result

            except Exception as e:
                self.analytics.record_error(f"Attempt {attempt + 1} failed for {chunk_info}: {str(e)}")

                if attempt < self.max_retries - 1:
                    delay = self.base_retry_delay * (2 ** attempt)
                    print(f"⚠️ Retry {attempt + 1} for {chunk_info} in {delay}s...")
                    self.analytics.record_retry()
                    time.sleep(delay)
                else:
                    print(f"⚠️ All retries failed for {chunk_info}")

        return None

    def process_single_chunk(self, chunk_text: str, template_name: str, chunk_info: str,
                             context: str = "") -> Optional[str]:
        """Process a single chunk with template and context preamble."""
        if not self.model:
            return None

        if not TEMPLATE_MANAGER_AVAILABLE or not template_manager:
            # Fallback processing with conservative instructions
            context_text = context if context else "None — this is the first section."
            system_prompt = (
                "You are an expert at cleaning academic text. "
                "You ONLY output the cleaned text. You NEVER ask for input or repeat instructions."
            )
            user_prompt = f"""CONTEXT FROM PREVIOUS SECTION (for continuity only — do NOT include in your output):
---
{context_text}
---

Clean this academic text. DO NOT summarize or reduce content significantly.

ONLY make these minimal changes:
- Remove figure/table references like "Figure 1", "Table 2"
- Remove citation brackets like "[1,2,3]" but keep author names
- Convert symbols: "%" to "percent", "&" to "and"
- Fix any weird punctuation

PRESERVE ALL:
- Scientific content and data
- Technical details and methodology
- Results and conclusions
- Academic precision
- Markdown headers and document structure

Output ONLY the processed text.

TEXT TO CLEAN:
{chunk_text}"""
        else:
            # Template-based processing with context preamble
            system_prompt = template_manager.get_system_prompt(template_name)
            user_prompt = template_manager.get_user_prompt(template_name, chunk_text, context=context)

        # Create a model with the system instruction for this call
        model_with_system = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config=self.model._generation_config,
            safety_settings=self.model._safety_settings,
            system_instruction=system_prompt,
        )

        # Generate with Gemini using the user prompt as the message
        response = model_with_system.generate_content(user_prompt)

        if response and response.text:
            # Apply cleanup-only post-processing (symbol/unit/abbreviation conversion)
            result = self.tts_optimizer.optimize_for_cleanup(response.text.strip())
            return result

        return None

    def process_text_advanced(self, content: str, template_name: str = "Review Papers",
                             progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Process text with non-overlapping chunking and context preamble."""

        # Start analytics
        self.analytics = ProcessingAnalytics()
        self.analytics.start_processing(content, template_name)

        if progress_callback:
            progress_callback("Initializing AI processing...")

        if not self.model:
            return {
                'success': False,
                'error': 'Gemini model not available',
                'processed_content': '',
                'template_used': template_name,
                **self.analytics.get_metrics()
            }

        if not content.strip():
            return {
                'success': False,
                'error': 'Empty content provided',
                'processed_content': '',
                'template_used': template_name,
                **self.analytics.get_metrics()
            }

        input_chars = len(content)
        print(f"📄 Processing {input_chars:,} characters with template: {template_name}")

        # Determine processing approach
        if input_chars <= self.max_chunk_size:
            # Single document — no chunking needed
            if progress_callback:
                progress_callback("Processing as single document...")

            result = self.process_chunk_with_retry(
                content, template_name, "single document", progress_callback,
                context=""
            )
            self.analytics.record_chunk_completion(result is not None)

        else:
            # Chunked processing with context preamble
            chunks = self.smart_chunk_text(content)
            self.analytics.total_chunks = len(chunks)

            if progress_callback:
                progress_callback(f"Split into {len(chunks)} chunks for processing...")

            print(f"📦 Processing {len(chunks)} chunks (non-overlapping with context preamble)")

            processed_chunks = []
            previous_chunk_output = ""  # No context for the first chunk

            for i, (chunk_text, start_pos, end_pos) in enumerate(chunks, 1):
                chunk_info = f"chunk {i}/{len(chunks)} (chars {start_pos:,}-{end_pos:,})"

                if progress_callback:
                    progress_callback(f"Processing {chunk_info}...")

                # Build context preamble from the tail of the previous chunk's OUTPUT
                context = ""
                if previous_chunk_output:
                    context = previous_chunk_output[-self.context_preamble_size:]

                chunk_result = self.process_chunk_with_retry(
                    chunk_text, template_name, chunk_info, progress_callback,
                    context=context
                )

                success = chunk_result is not None
                self.analytics.record_chunk_completion(success)

                if success:
                    processed_chunks.append(chunk_result)
                    previous_chunk_output = chunk_result  # Store for next chunk's context
                    print(f"   ✅ Completed {chunk_info}")
                else:
                    print(f"   ⚠️ Failed {chunk_info}")
                    # On failure, keep previous_chunk_output unchanged so next
                    # chunk still gets context from the last successful chunk

                # Progress update
                if progress_callback:
                    progress = (i / len(chunks)) * 100
                    progress_callback(f"Progress: {progress:.1f}% ({i}/{len(chunks)} chunks)")

                # API rate limiting
                if i < len(chunks):
                    time.sleep(CHUNKING_CONFIG["chunk_delay_seconds"])

            # Simple concatenation — no Jaccard merge needed
            if processed_chunks:
                if progress_callback:
                    progress_callback("Joining processed chunks...")
                result = "\n\n".join(processed_chunks)
                print(f"🔗 Joined {len(processed_chunks)} chunks successfully")
            else:
                result = None
                print("⚠️ All chunks failed to process")

        # Finalize analytics
        self.analytics.finish_processing(result or "")
        metrics = self.analytics.get_metrics()

        # Final processing feedback
        if progress_callback:
            if result:
                reduction = metrics['reduction_percentage']
                time_taken = metrics['processing_time']
                progress_callback(f"✅ Complete! {reduction:.1f}% reduction in {time_taken:.1f}s")
            else:
                progress_callback("⚠️ Processing failed")

        # Print summary
        if result:
            print("✅ Processing completed successfully")
            print(f"   📊 Input: {metrics['input_chars']:,} chars")
            print(f"   📊 Output: {metrics['output_chars']:,} chars")
            print(f"   📊 Reduction: {metrics['reduction_percentage']:.1f}%")
            print(f"   📊 Time: {metrics['processing_time']:.1f}s")
            print(f"   📊 Success Rate: {metrics['success_rate']:.1f}%")

        return {
            'success': result is not None,
            'processed_content': result or '',
            'error': 'Processing failed' if not result else None,
            'template_used': template_name,
            **metrics
        }

# Global processor instance
advanced_text_processor = AdvancedTextProcessor()

# Compatibility function for GUI
def process_markdown_content(content: str, template_name: str = "Review Papers",
                           progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
    """
    Process markdown content — cleanup pass.

    API contract (unchanged):
        Returns dict with keys: success, processed_content, input_chars,
        output_chars, reduction_percentage, processing_time, template_used,
        total_chunks, chunks_processed, failed_chunks, retry_count,
        success_rate, errors, error.
    """
    try:
        result = advanced_text_processor.process_text_advanced(content, template_name, progress_callback)

        # Ensure all expected fields are present
        return {
            'success': result.get('success', False),
            'processed_content': result.get('processed_content', ''),
            'input_chars': result.get('input_chars', len(content)),
            'output_chars': result.get('output_chars', 0),
            'reduction_percentage': result.get('reduction_percentage', 0),
            'processing_time': result.get('processing_time', 0),
            'template_used': result.get('template_used', template_name),
            'total_chunks': result.get('total_chunks', 1),
            'chunks_processed': result.get('chunks_processed', 0),
            'failed_chunks': result.get('failed_chunks', 0),
            'retry_count': result.get('retry_count', 0),
            'success_rate': result.get('success_rate', 0),
            'errors': result.get('errors', []),
            'error': result.get('error', None)
        }

    except Exception as e:
        return {
            'success': False,
            'processed_content': '',
            'input_chars': len(content),
            'output_chars': 0,
            'reduction_percentage': 0,
            'processing_time': 0,
            'template_used': template_name,
            'total_chunks': 0,
            'chunks_processed': 0,
            'failed_chunks': 0,
            'retry_count': 0,
            'success_rate': 0,
            'errors': [str(e)],
            'error': str(e)
        }
