"""
Advanced Text Processor for Science2Go
Fixed version with proper TTS optimization and chunk merging
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


# Gemini 2.5 Flash pricing (per token)
GEMINI_INPUT_PRICE = 0.30 / 1_000_000
GEMINI_OUTPUT_PRICE = 2.50 / 1_000_000


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
        self.input_tokens = 0
        self.output_tokens = 0

    def start_processing(self, input_text: str, template_name: str):
        """Start processing timer and record initial metrics"""
        self.start_time = time.time()
        self.input_chars = len(input_text)
        self.template_used = template_name
        self.chunks_processed = 0
        self.failed_chunks = 0
        self.retry_count = 0
        self.errors = []
        self.input_tokens = 0
        self.output_tokens = 0

    def record_chunk_completion(self, success: bool = True):
        """Record completion of a chunk"""
        self.chunks_processed += 1
        if not success:
            self.failed_chunks += 1

    def record_token_usage(self, input_tokens: int, output_tokens: int):
        """Accumulate Gemini token usage from a single API call"""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens

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
        gemini_cost = (self.input_tokens * GEMINI_INPUT_PRICE
                       + self.output_tokens * GEMINI_OUTPUT_PRICE)

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
            'errors': self.errors,
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'gemini_cost': gemini_cost,
        }

class TTSOptimizer:
    """Fixed TTS optimization without literal pause insertions"""
    
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
    
    def optimize_for_tts(self, text: str) -> str:
        """Apply TTS optimizations without literal pause insertions"""
        # Apply conversions in order
        text = self.convert_symbols(text)
        text = self.expand_abbreviations(text)
        text = self.convert_units(text)
        text = self.clean_for_speech(text)
        text = self.fix_punctuation_issues(text)
        
        return text
    
    def convert_symbols(self, text: str) -> str:
        """Convert mathematical and special symbols to spoken form"""
        for symbol, spoken in self.symbol_map.items():
            text = text.replace(symbol, spoken)
        return text
    
    def expand_abbreviations(self, text: str) -> str:
        """Expand abbreviations for better speech"""
        for abbrev, expansion in self.abbreviation_map.items():
            # Case-insensitive replacement with word boundaries
            pattern = r'\b' + re.escape(abbrev) + r'\b'
            text = re.sub(pattern, expansion, text, flags=re.IGNORECASE)
        return text
    
    def convert_units(self, text: str) -> str:
        """Convert units to spoken form"""
        for unit, spoken in self.unit_map.items():
            # Match units after numbers
            pattern = r'(\d+(?:\.\d+)?)\s*' + re.escape(unit) + r'\b'
            replacement = r'\1' + spoken
            text = re.sub(pattern, replacement, text)
        return text
    
    def clean_for_speech(self, text: str) -> str:
        """Clean text for speech without literal pause insertions"""
        # Remove excessive punctuation
        text = re.sub(r'[()[\]{}]', '', text)  # Remove brackets
        text = re.sub(r'--+', ' ', text)  # Replace dashes with spaces
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = re.sub(r'\.{2,}', '.', text)  # Normalize ellipses to single periods
        
        # Convert section headers to speech-friendly format
        text = re.sub(r'^#{1,6}\s*(.+)$', r'\1 section.', text, flags=re.MULTILINE)
        
        # Break very long sentences at natural points
        sentences = text.split('. ')
        processed_sentences = []
        
        for sentence in sentences:
            if len(sentence) > 200:  # Very long sentence
                # Try to break at natural points
                parts = re.split(r'(,\s+(?:which|that|who|and|but|or|however|moreover|furthermore))', sentence)
                if len(parts) > 2:
                    # Recombine with period breaks at natural points
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
        """Fix weird punctuation artifacts from AI processing"""
        # Fix common punctuation issues
        text = re.sub(r'\.\s*,', '.', text)  # Fix ". ," combinations
        text = re.sub(r',\s*\.', '.', text)  # Fix ", ." combinations
        text = re.sub(r'\.\s*;', '.', text)  # Fix ". ;" combinations
        text = re.sub(r';\s*\.', '.', text)  # Fix "; ." combinations

        # Fix ". and." / ". or." / ". but." artifacts from sentence splitting
        text = re.sub(r'\.\s+(and|or|but|which|that|who|however|moreover|furthermore)\.\s+',
                       r', \1 ', text, flags=re.IGNORECASE)
        
        # Remove all pause tag variants from Gemini AI processing.
        # Templates no longer ask for pause tags, but Gemini may still
        # hallucinate them.  Remove all variants as a safety net:
        # bracketed, unbracketed, and orphaned fragments.
        text = re.sub(r'\[\s*pause\s*(short|long)?\s*\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\bpause\s+(short|long)\b\.?\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(short|long)\s+pause\b\.?\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\bpause\b\.?\s*', '', text, flags=re.IGNORECASE)
        # Remove orphaned "short"/"long" that Gemini left without "pause" keyword —
        # only when they appear right after a sentence boundary (". long Defects...")
        text = re.sub(r'(?<=\.)\s+(short|long)\s+(?=[A-Z])', ' ', text)

        # Normalize multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

class AdvancedTextProcessor:
    """Fixed text processor with improved chunking and merging"""
    
    def __init__(self):
        self.model = None
        self.analytics = ProcessingAnalytics()
        self.tts_optimizer = TTSOptimizer()
        self.setup_gemini()
        
        # Processing parameters - more conservative
        self.max_chunk_size = 25000  # Smaller chunks for better handling
        self.overlap_size = 500      # Smaller overlap to reduce merging issues
        self.min_chunk_size = 5000
        self.max_retries = 3
        self.base_retry_delay = 2.0
    
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
        """Improved text chunking with better break detection"""
        if len(text) <= self.max_chunk_size:
            return [(text, 0, len(text))]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + self.max_chunk_size, len(text))
            
            if end < len(text):
                # Look for good break points in order of preference
                break_patterns = [
                    r'\n\n#+\s',           # Markdown headers
                    r'\n\n\d+\.?\s+[A-Z]', # Numbered sections
                    r'\n\n[A-Z][A-Z\s]{3,}:?\n',  # Section titles
                    r'\n\n\w',             # Any paragraph break
                    r'\.[\s\n]+[A-Z][a-z]', # Sentence boundaries
                ]
                
                best_break = None
                search_start = max(start + self.min_chunk_size, end - self.overlap_size)
                search_region = text[search_start:end + self.overlap_size]
                
                for pattern in break_patterns:
                    matches = list(re.finditer(pattern, search_region, re.MULTILINE))
                    if matches:
                        match = matches[-1]
                        potential_break = search_start + match.start()
                        if potential_break > start + self.min_chunk_size:
                            best_break = potential_break
                            break
                
                if best_break:
                    end = best_break
            
            # Avoid cutting in the middle of a word at the chunk boundary,
            # which otherwise produces broken fragments like "annu" / "lar
            # dark-field..." at the start of the overlapping next chunk.
            if end < len(text) and not text[end].isspace() and not text[end - 1].isspace():
                snap = max(text.rfind(' ', start, end), text.rfind('\n', start, end))
                if snap > start + self.min_chunk_size:
                    end = snap

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append((chunk_text, start, end))

            if end < len(text):
                next_start = max(end - self.overlap_size, start + self.min_chunk_size)
                # Begin the next chunk on a word boundary so the overlapping
                # text starts cleanly. The overlap itself is removed later when
                # the processed chunks are merged.
                while next_start < end and not text[next_start].isspace():
                    next_start += 1
                while next_start < end and text[next_start].isspace():
                    next_start += 1
                start = next_start
            else:
                start = end

        return chunks
    
    def process_chunk_with_retry(self, chunk_text: str, template_name: str, chunk_info: str,
                                progress_callback: Optional[Callable] = None,
                                context: str = "") -> Optional[str]:
        """Process a chunk with retry logic"""
        for attempt in range(self.max_retries):
            try:
                if progress_callback:
                    progress_callback(f"Processing {chunk_info} (attempt {attempt + 1})")

                result = self.process_single_chunk(
                    chunk_text, template_name, chunk_info, context=context
                )
                if result:
                    return result

            except Exception as e:
                error_str = str(e)
                self.analytics.record_error(f"Attempt {attempt + 1} failed for {chunk_info}: {error_str}")

                if attempt < self.max_retries - 1:
                    delay = self.base_retry_delay * (2 ** attempt)
                    print(f"⚠️ Retry {attempt + 1} for {chunk_info} in {delay}s... ({error_str[:120]})")
                    self.analytics.record_retry()
                    time.sleep(delay)
                else:
                    print(f"⚠️ All retries failed for {chunk_info}: {error_str[:200]}")

        return None
    
    def process_single_chunk(self, chunk_text: str, template_name: str, chunk_info: str,
                            context: str = "",
                            _using_template: bool = False) -> Optional[str]:
        """Process a single chunk with template using proper system instruction.

        Args:
            chunk_text: The text content to process.
            template_name: Which template to use.
            chunk_info: Human-readable description of the chunk.
            context: Optional context from the previous chunk (used by SSML Converter).
            _using_template: Set internally — True when a real template was loaded.
        """
        if not self.model:
            return None

        is_ssml_template = (template_name == "SSML Converter")

        if not TEMPLATE_MANAGER_AVAILABLE or not template_manager:
            # Fallback processing with conservative instructions
            _using_template = False
            system_prompt = (
                "You are an expert at cleaning academic text for text-to-speech. "
                "You ONLY output the cleaned text. You NEVER ask for input or repeat instructions."
            )
            user_prompt = f"""Clean this academic text for text-to-speech. DO NOT summarize or reduce content significantly.

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

Output ONLY the processed text.

TEXT TO CLEAN:
{chunk_text}"""
        else:
            # Template-based processing
            _using_template = True
            system_prompt = template_manager.get_system_prompt(template_name)
            user_prompt = template_manager.get_user_prompt(
                template_name, chunk_text, context=context
            )

        # Create a model with the system instruction for this call
        model_with_system = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config=self.model._generation_config,
            safety_settings=self.model._safety_settings,
            system_instruction=system_prompt,
        )

        # Generate with Gemini using the user prompt as the message
        response = model_with_system.generate_content(user_prompt)

        # Track token usage for cost estimation
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            um = response.usage_metadata
            self.analytics.record_token_usage(
                getattr(um, 'prompt_token_count', 0) or 0,
                getattr(um, 'candidates_token_count', 0) or 0,
            )

        # --- Extract text, handling blocked / empty responses ----
        result_text = None
        try:
            if response and response.text:
                result_text = response.text.strip()
        except ValueError:
            # response.text raises ValueError when no valid Part is returned
            # (e.g. finish_reason is RECITATION or SAFETY).
            # Try to salvage partial text from candidates.
            finish_reason = "UNKNOWN"
            try:
                candidate = response.candidates[0]
                finish_reason = candidate.finish_reason.name
                # Some blocked responses still contain partial text
                if candidate.content and candidate.content.parts:
                    partial = "".join(
                        p.text for p in candidate.content.parts if hasattr(p, 'text')
                    ).strip()
                    if len(partial) > 200:
                        result_text = partial
                        print(f"   ⚠️ Response blocked ({finish_reason}) but salvaged {len(partial):,} chars of partial text")
            except Exception:
                pass

            if not result_text:
                print(f"   ⚠️ Response blocked by Gemini (finish_reason={finish_reason}) — no usable text")
                return None

        if not result_text:
            return None

        # --- Post-process the result ---
        # Strip markdown code fences that Gemini sometimes wraps SSML in
        if is_ssml_template:
            result_text = re.sub(r'^```(?:xml|ssml)?\s*\n?', '', result_text)
            result_text = re.sub(r'\n?```\s*$', '', result_text)
        elif _using_template:
            # Template already instructed Gemini to clean the text fully.
            # Only apply lightweight punctuation fixes — do NOT run the
            # full optimize_for_tts() which destructively splits sentences,
            # removes brackets, and converts symbols that Gemini has
            # already handled, causing ". and" artifacts and title loss.
            result_text = self.tts_optimizer.fix_punctuation_issues(result_text)
        else:
            # No template — apply full TTS optimizations on raw AI output
            result_text = self.tts_optimizer.optimize_for_tts(result_text)

        return result_text
    
    def merge_chunks_intelligently(self, chunks: List[str]) -> str:
        """Improved chunk merging to prevent cutoffs"""
        if not chunks:
            return ""
        if len(chunks) == 1:
            return chunks[0]
        
        merged_parts = [chunks[0]]
        
        for i in range(1, len(chunks)):
            current_chunk = chunks[i]
            previous_content = merged_parts[-1]
            
            # Remove potential overlaps more conservatively
            cleaned_chunk = self.remove_chunk_overlap(previous_content, current_chunk)
            
            if cleaned_chunk.strip():
                # Add appropriate spacing
                if not previous_content.endswith('.') and not previous_content.endswith('\n'):
                    merged_parts.append(' ')
                merged_parts.append(cleaned_chunk)
        
        result = ''.join(merged_parts)
        
        # Final cleanup to fix any remaining issues
        result = self.tts_optimizer.fix_punctuation_issues(result)
        
        return result
    
    def merge_ssml_chunks(self, chunks: List[str]) -> str:
        """Merge SSML chunks by stripping <speak> wrappers and re-wrapping once.

        Each chunk from the AI is expected to be wrapped in <speak>...</speak>.
        We strip those wrappers, remove the overlapping sentences that the
        chunker duplicated across each boundary, concatenate the inner SSML
        content with breaks between chunks, and wrap the whole thing in a
        single <speak> element.

        Because the chunker overlaps consecutive chunks (overlap_size) to keep
        context for Gemini, the same trailing sentences of one chunk reappear
        at the start of the next. Without removal these are spoken twice in the
        generated audio. We detect and strip them with fuzzy sentence matching,
        which tolerates the small rewording Gemini applies to the overlap.
        """
        if not chunks:
            return ""

        inner_parts = []
        for chunk in chunks:
            text = chunk.strip()
            # Strip opening <speak> tag (with optional attributes/whitespace)
            text = re.sub(r'^\s*<speak[^>]*>\s*', '', text, flags=re.IGNORECASE)
            # Strip closing </speak> tag
            text = re.sub(r'\s*</speak>\s*$', '', text, flags=re.IGNORECASE)
            if text.strip():
                inner_parts.append(text.strip())

        if not inner_parts:
            return ""
        if len(inner_parts) == 1:
            return f'<speak>\n{inner_parts[0]}\n</speak>'

        merged = inner_parts[0]
        removed_total = 0
        for part in inner_parts[1:]:
            part, removed = self._strip_leading_ssml_overlap(merged, part)
            removed_total += removed
            part = part.strip()
            if part:
                merged += '\n<break time="500ms"/>\n' + part

        if removed_total:
            print(f"   🧹 Removed {removed_total} duplicated sentence(s) at chunk boundaries")

        return f'<speak>\n{merged}\n</speak>'

    # --- SSML overlap-removal helpers ------------------------------------

    _SENTENCE_RE = re.compile(r'<s\b[^>]*>(.*?)</s>', re.IGNORECASE | re.DOTALL)

    @staticmethod
    def _normalize_ssml_sentence(text: str) -> str:
        """Normalize a sentence's inner SSML for fuzzy comparison.

        Strips all tags (e.g. <say-as>, <emphasis>), unescapes common
        entities, lowercases, and keeps only alphanumerics and spaces.
        """
        text = re.sub(r'<[^>]+>', ' ', text)
        text = (text.replace('&quot;', '"').replace('&amp;', '&')
                    .replace('&lt;', '<').replace('&gt;', '>').replace('&apos;', "'"))
        text = text.lower()
        text = re.sub(r'[^a-z0-9 ]+', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    @staticmethod
    def _word_jaccard(a: str, b: str) -> float:
        """Jaccard similarity of the word sets of two normalized sentences."""
        wa, wb = set(a.split()), set(b.split())
        if not wa or not wb:
            return 0.0
        return len(wa & wb) / len(wa | wb)

    def _strip_leading_ssml_overlap(self, prev: str, curr: str,
                                    window: int = 12,
                                    threshold: float = 0.6) -> Tuple[str, int]:
        """Remove sentences at the start of ``curr`` that duplicate the tail of
        ``prev`` (the overlap introduced by the chunker).

        Returns (cleaned_curr, num_sentences_removed). Matching is limited to a
        bounded window of sentences at the seam to avoid removing legitimate
        repetition elsewhere in the document.
        """
        prev_sents = [self._normalize_ssml_sentence(m.group(1))
                      for m in self._SENTENCE_RE.finditer(prev)]
        prev_tail = [s for s in prev_sents if s][-window:]
        if not prev_tail:
            return curr, 0

        curr_matches = list(self._SENTENCE_RE.finditer(curr))
        if not curr_matches:
            return curr, 0

        # Find the furthest leading sentence in curr (within the window) that
        # still matches a sentence in prev's tail. Everything up to and
        # including it is overlap and is dropped — this also removes any broken
        # leading fragment that sits before the last matched sentence.
        last_dup = -1
        limit = min(window, len(curr_matches))
        for i in range(limit):
            norm = self._normalize_ssml_sentence(curr_matches[i].group(1))
            if len(norm.split()) < 4:
                continue  # too short to judge reliably; skip as an anchor
            best = max((self._word_jaccard(norm, p) for p in prev_tail), default=0.0)
            if best >= threshold:
                last_dup = i

        if last_dup < 0:
            return curr, 0

        remainder = curr[curr_matches[last_dup].end():]
        remainder = self._rebalance_leading_ssml(remainder)
        return remainder, last_dup + 1

    @staticmethod
    def _rebalance_leading_ssml(text: str) -> str:
        """Tidy the start of a chunk after a leading prefix was removed.

        Drops orphaned closing/structural tags left dangling at the new start
        and re-opens paragraphs if the removed prefix contained the matching
        <p> opener, keeping the SSML reasonably balanced.
        """
        text = text.lstrip()
        while True:
            m = re.match(r'^\s*(</p>|</s>|</prosody>|<break[^>]*/>)\s*', text, re.IGNORECASE)
            if not m:
                break
            text = text[m.end():]
        opens = len(re.findall(r'<p\b[^>]*>', text, re.IGNORECASE))
        closes = len(re.findall(r'</p>', text, re.IGNORECASE))
        if closes > opens:
            text = ('<p>\n' * (closes - opens)) + text
        return text.strip()

    def remove_chunk_overlap(self, previous_text: str, current_text: str) -> str:
        """Conservative overlap removal to prevent content loss"""
        # Split into sentences for overlap detection
        prev_sentences = [s.strip() for s in previous_text.split('.') if s.strip()]
        curr_sentences = [s.strip() for s in current_text.split('.') if s.strip()]
        
        if not prev_sentences or not curr_sentences:
            return current_text
        
        # Look for overlapping sentences (be more conservative)
        max_check = min(2, len(prev_sentences), len(curr_sentences))  # Check fewer sentences
        
        for overlap_size in range(max_check, 0, -1):
            prev_end = prev_sentences[-overlap_size:]
            curr_start = curr_sentences[:overlap_size]
            
            # Check for high similarity (higher threshold)
            similarity = self.calculate_sentence_similarity(prev_end, curr_start)
            if similarity > 0.8:  # Higher threshold - 80% similarity
                # Remove overlapping sentences from current chunk
                remaining_sentences = curr_sentences[overlap_size:]
                return '. '.join(remaining_sentences) + '.' if remaining_sentences else ''
        
        return current_text
    
    def calculate_sentence_similarity(self, sentences1: List[str], sentences2: List[str]) -> float:
        """Calculate similarity between sentence lists"""
        if not sentences1 or not sentences2:
            return 0.0
        
        total_similarity = 0.0
        comparisons = min(len(sentences1), len(sentences2))
        
        for i in range(comparisons):
            words1 = set(sentences1[i].lower().split())
            words2 = set(sentences2[i].lower().split())
            
            if words1 and words2:
                intersection = len(words1.intersection(words2))
                union = len(words1.union(words2))
                similarity = intersection / union if union > 0 else 0
                total_similarity += similarity
        
        return total_similarity / comparisons if comparisons > 0 else 0.0
    
    def process_text_advanced(self, content: str, template_name: str = "Review Papers",
                             progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Advanced text processing with improved analytics"""

        # Start analytics
        self.analytics = ProcessingAnalytics()
        self.analytics.start_processing(content, template_name)

        is_ssml_template = (template_name == "SSML Converter")

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
            if progress_callback:
                progress_callback("Processing as single document...")

            result = self.process_chunk_with_retry(
                content, template_name, "single document", progress_callback,
                context=""
            )
            self.analytics.record_chunk_completion(result is not None)

        else:
            # Chunked processing
            chunks = self.smart_chunk_text(content)
            self.analytics.total_chunks = len(chunks)

            if progress_callback:
                progress_callback(f"Split into {len(chunks)} chunks for processing...")

            print(f"📦 Processing {len(chunks)} chunks")

            processed_chunks = []
            previous_context = ""  # Tail of previous chunk result for SSML continuity

            for i, (chunk_text, start_pos, end_pos) in enumerate(chunks, 1):
                chunk_info = f"chunk {i}/{len(chunks)} (chars {start_pos:,}-{end_pos:,})"

                if progress_callback:
                    progress_callback(f"Processing {chunk_info}...")

                chunk_result = self.process_chunk_with_retry(
                    chunk_text, template_name, chunk_info, progress_callback,
                    context=previous_context
                )

                success = chunk_result is not None
                self.analytics.record_chunk_completion(success)

                if success:
                    processed_chunks.append(chunk_result)
                    print(f"   ✅ Completed {chunk_info}")
                    # For SSML template, pass the last ~500 chars as context
                    # to the next chunk so the AI knows where we left off
                    if is_ssml_template:
                        previous_context = chunk_result[-500:] if len(chunk_result) > 500 else chunk_result
                else:
                    print(f"   ⚠️ Failed {chunk_info}")

                # Progress update
                if progress_callback:
                    progress = (i / len(chunks)) * 100
                    progress_callback(f"Progress: {progress:.1f}% ({i}/{len(chunks)} chunks)")

                # API rate limiting
                if i < len(chunks):
                    time.sleep(1)

            # Merge results
            if processed_chunks:
                if progress_callback:
                    progress_callback("Merging processed chunks...")

                if is_ssml_template:
                    result = self.merge_ssml_chunks(processed_chunks)
                    print(f"🔗 Merged {len(processed_chunks)} SSML chunks successfully")
                else:
                    result = self.merge_chunks_intelligently(processed_chunks)
                    print(f"🔗 Merged {len(processed_chunks)} chunks successfully")
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
            print("✅ Advanced processing completed successfully")
            print(f"   📊 Input: {metrics['input_chars']:,} chars")
            print(f"   📊 Output: {metrics['output_chars']:,} chars")
            print(f"   📊 Reduction: {metrics['reduction_percentage']:.1f}%")
            print(f"   📊 Time: {metrics['processing_time']:.1f}s")
            print(f"   📊 Success Rate: {metrics['success_rate']:.1f}%")
            if metrics['input_tokens'] or metrics['output_tokens']:
                print(f"   📊 Tokens: {metrics['input_tokens']:,} in / {metrics['output_tokens']:,} out")
                print(f"   📊 Est. Gemini cost: ${metrics['gemini_cost']:.4f}")
        
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
    Process markdown content with improved handling
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