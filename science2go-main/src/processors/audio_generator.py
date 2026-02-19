"""
Science2Go Audio Generator
Google Cloud TTS wrapper with Chirp 3 HD + Neural2 support, SSML-aware chunking,
audio concatenation (pydub), normalization, and MP3/M4B metadata (mutagen).
"""

import os
import re
import time
import logging
import tempfile
import struct
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime

# Google Cloud TTS
try:
    from google.cloud import texttospeech
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("Warning: google-cloud-texttospeech not installed. "
          "Install with: pip install google-cloud-texttospeech")

# Audio processing
try:
    from pydub import AudioSegment
    from pydub.effects import normalize as pydub_normalize
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    print("Warning: pydub not installed. Install with: pip install pydub")

# Metadata tagging
try:
    import mutagen
    from mutagen.mp3 import MP3
    from mutagen.id3 import (
        ID3, TIT2, TPE1, TALB, TDRC, TCON, COMM, TPUB, CTOC, CHAP,
        ID3NoHeaderError,
    )
    from mutagen.mp4 import MP4, MP4Cover
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    print("Warning: mutagen not installed. Install with: pip install mutagen")


# ── Logging setup ──

def _setup_logger() -> logging.Logger:
    """Configure logger with console and file handlers."""
    _logger = logging.getLogger('science2go.audio_generator')

    # Avoid duplicate handlers if module is reloaded
    if _logger.handlers:
        return _logger

    # Try to read log level from config; fall back to INFO
    try:
        from src.config.settings import config
        level_name = config.log_level.upper()
    except Exception:
        level_name = "INFO"

    level = getattr(logging, level_name, logging.INFO)
    _logger.setLevel(level)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_fmt = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_fmt)
    _logger.addHandler(console_handler)

    # File handler
    try:
        from src.config.settings import config as _cfg
        log_dir = _cfg.output_dir / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(
            log_dir / 'audio_generator.log', encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # Always capture everything to file
        file_fmt = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_fmt)
        _logger.addHandler(file_handler)
    except Exception as e:
        _logger.warning(f"Could not create file handler: {e}")

    return _logger

logger = _setup_logger()


# ── Constants ──

# TTS API limit: 5000 bytes per request (for ASCII English ~5000 chars)
MAX_TTS_BYTES = 4800  # Leave margin for safety

# Rate limit: 200 RPM for Chirp3 voices
CHIRP3_RPM_LIMIT = 200
MIN_REQUEST_INTERVAL = 60.0 / CHIRP3_RPM_LIMIT  # 0.3s between requests

# TTS pricing per character
TTS_PRICE_CHIRP3_HD = 30.0 / 1_000_000
TTS_PRICE_NEURAL2 = 16.0 / 1_000_000

# Default voice
DEFAULT_VOICE = "en-GB-Chirp3-HD-Charon"
DEFAULT_LANGUAGE = "en-GB"
DEFAULT_SPEAKING_RATE = 0.95
DEFAULT_ENCODING = "MP3"

# Audio format options
AUDIO_FORMATS = ["MP3", "WAV", "OGG", "M4B"]
BITRATE_OPTIONS = ["64k", "96k", "128k", "192k", "256k", "320k"]

# ── Voice model types ──

VOICE_MODEL_CHIRP3_HD = "Chirp 3 HD"
VOICE_MODEL_NEURAL2 = "Neural2"
VOICE_MODELS = [VOICE_MODEL_CHIRP3_HD, VOICE_MODEL_NEURAL2]

# Available Chirp 3 HD voices for en-GB (male)
CHIRP3_HD_MALE_VOICES = [
    "en-GB-Chirp3-HD-Achird",
    "en-GB-Chirp3-HD-Algenib",
    "en-GB-Chirp3-HD-Algieba",
    "en-GB-Chirp3-HD-Alnilam",
    "en-GB-Chirp3-HD-Charon",
    "en-GB-Chirp3-HD-Enceladus",
    "en-GB-Chirp3-HD-Fenrir",
    "en-GB-Chirp3-HD-Iapetus",
    "en-GB-Chirp3-HD-Orus",
    "en-GB-Chirp3-HD-Puck",
    "en-GB-Chirp3-HD-Rasalgethi",
    "en-GB-Chirp3-HD-Sadachbia",
    "en-GB-Chirp3-HD-Sadaltager",
    "en-GB-Chirp3-HD-Schedar",
    "en-GB-Chirp3-HD-Umbriel",
    "en-GB-Chirp3-HD-Zubenelgenubi",
]

# Available Chirp 3 HD voices for en-GB (female)
CHIRP3_HD_FEMALE_VOICES = [
    "en-GB-Chirp3-HD-Achernar",
    "en-GB-Chirp3-HD-Aoede",
    "en-GB-Chirp3-HD-Autonoe",
    "en-GB-Chirp3-HD-Callirrhoe",
    "en-GB-Chirp3-HD-Despina",
    "en-GB-Chirp3-HD-Erinome",
    "en-GB-Chirp3-HD-Gacrux",
    "en-GB-Chirp3-HD-Kore",
    "en-GB-Chirp3-HD-Laomedeia",
    "en-GB-Chirp3-HD-Leda",
    "en-GB-Chirp3-HD-Pulcherrima",
    "en-GB-Chirp3-HD-Sulafat",
    "en-GB-Chirp3-HD-Vindemiatrix",
    "en-GB-Chirp3-HD-Zephyr",
]

ALL_CHIRP3_HD_VOICES = CHIRP3_HD_MALE_VOICES + CHIRP3_HD_FEMALE_VOICES

# Available Neural2 voices for en-GB
NEURAL2_MALE_VOICES = [
    "en-GB-Neural2-D",
]

NEURAL2_FEMALE_VOICES = [
    "en-GB-Neural2-A",
    "en-GB-Neural2-C",
    "en-GB-Neural2-F",
]

ALL_NEURAL2_VOICES = NEURAL2_MALE_VOICES + NEURAL2_FEMALE_VOICES

# Voice display names (strip the locale prefix for UI)
def voice_display_name(full_name: str) -> str:
    """Extract display name from full voice name, e.g. 'Charon' from 'en-GB-Chirp3-HD-Charon'."""
    parts = full_name.split("-")
    return parts[-1] if parts else full_name


def voice_full_name(display_name: str, language: str = DEFAULT_LANGUAGE,
                    model: str = VOICE_MODEL_CHIRP3_HD) -> str:
    """Build full voice name from display name and model type.

    Chirp 3 HD: 'Charon' -> 'en-GB-Chirp3-HD-Charon'
    Neural2:    'D'      -> 'en-GB-Neural2-D'
    """
    if model == VOICE_MODEL_NEURAL2:
        return f"{language}-Neural2-{display_name}"
    return f"{language}-Chirp3-HD-{display_name}"


# ── SSML Detection ──

def is_ssml_content(text: str) -> bool:
    """Detect whether the input text is SSML by checking for a <speak> root tag."""
    stripped = text.strip()
    # Skip leading XML comment if present (<!-- metadata ... -->)
    if stripped.startswith('<!--'):
        comment_end = stripped.find('-->')
        if comment_end != -1:
            stripped = stripped[comment_end + 3:].strip()
    return stripped.startswith('<speak>')


# ── Text chunking for TTS (plain text) ──

def chunk_text_for_tts(text: str, max_bytes: int = MAX_TTS_BYTES) -> List[Dict[str, Any]]:
    """
    Split text into chunks that fit within the TTS byte limit.
    Tries to break at sentence boundaries for natural speech flow.
    Returns list of dicts with 'text', 'index', 'is_section_start' keys.
    """
    if not text or not text.strip():
        return []

    # Split into paragraphs first
    paragraphs = re.split(r'\n\s*\n', text.strip())
    chunks = []
    current_chunk = ""
    chunk_index = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # Check if adding this paragraph would exceed the limit
        test_chunk = (current_chunk + "\n\n" + para).strip() if current_chunk else para
        if len(test_chunk.encode('utf-8')) <= max_bytes:
            current_chunk = test_chunk
        else:
            # Save current chunk if it has content
            if current_chunk.strip():
                chunks.append({
                    'text': current_chunk.strip(),
                    'index': chunk_index,
                    'is_section_start': _is_section_start(current_chunk),
                })
                chunk_index += 1

            # Try to fit the paragraph; if it's too long, split by sentences
            if len(para.encode('utf-8')) <= max_bytes:
                current_chunk = para
            else:
                # Split long paragraph by sentences
                sentences = re.split(r'(?<=[.!?])\s+', para)
                current_chunk = ""
                for sentence in sentences:
                    test = (current_chunk + " " + sentence).strip() if current_chunk else sentence
                    if len(test.encode('utf-8')) <= max_bytes:
                        current_chunk = test
                    else:
                        if current_chunk.strip():
                            chunks.append({
                                'text': current_chunk.strip(),
                                'index': chunk_index,
                                'is_section_start': False,
                            })
                            chunk_index += 1
                        # If a single sentence exceeds the limit, force-split it
                        if len(sentence.encode('utf-8')) > max_bytes:
                            for sub in _force_split(sentence, max_bytes):
                                chunks.append({
                                    'text': sub,
                                    'index': chunk_index,
                                    'is_section_start': False,
                                })
                                chunk_index += 1
                            current_chunk = ""
                        else:
                            current_chunk = sentence

    # Don't forget the last chunk
    if current_chunk.strip():
        chunks.append({
            'text': current_chunk.strip(),
            'index': chunk_index,
            'is_section_start': _is_section_start(current_chunk),
        })

    return chunks


def _is_section_start(text: str) -> bool:
    """Check if text starts with a section header pattern."""
    first_line = text.strip().split('\n')[0].strip()
    # Matches patterns like "Abstract.", "New section: Methods.", "Introduction.", etc.
    return bool(re.match(
        r'^(Abstract|New section:|Introduction|Methods|Results|Discussion|Conclusion)',
        first_line, re.IGNORECASE
    ))


def _force_split(text: str, max_bytes: int) -> List[str]:
    """Force-split text at word boundaries when a single sentence exceeds the limit."""
    words = text.split()
    parts = []
    current = ""
    for word in words:
        test = (current + " " + word).strip() if current else word
        if len(test.encode('utf-8')) <= max_bytes:
            current = test
        else:
            if current:
                parts.append(current)
            current = word
    if current:
        parts.append(current)
    return parts


# ── SSML sanitization and chunking for TTS ──

# Tags supported by Google Cloud TTS SSML
_SUPPORTED_SSML_TAGS = {'speak', 'break', 'say-as', 'sub', 'emphasis',
                        'prosody', 'p', 's', 'phoneme', 'mark',
                        'par', 'seq', 'media', 'audio'}


def _sanitize_ssml(ssml: str) -> str:
    """Remove SSML tags not supported by Google Cloud TTS and fix common XML errors.

    1. Strips unsupported tags (keeps their text content).
    2. Escapes bare ``&`` characters that aren't already XML entities.
    3. Escapes stray ``<`` / ``>`` in text content (not part of tags).
    4. Removes any remaining non-XML-safe characters.
    """
    # ── Step 1: strip unsupported tags ──
    def _strip_unsupported(match):
        tag_name = match.group(1).split()[0]  # handle <tag attr="...">
        if tag_name.lower() in _SUPPORTED_SSML_TAGS:
            return match.group(0)  # keep supported tag
        logger.debug(f"Stripping unsupported SSML tag: <{tag_name}>")
        return ''  # remove unsupported tag

    # Strip opening tags: <tagname ...>
    result = re.sub(r'<([a-zA-Z][a-zA-Z0-9_-]*(?:\s[^>]*)?)>', _strip_unsupported, ssml)
    # Strip closing tags: </tagname>
    result = re.sub(r'</([a-zA-Z][a-zA-Z0-9_-]*)>', _strip_unsupported, result)

    # ── Step 2: fix bare & characters ──
    # Match & that is NOT already part of a named or numeric XML entity
    result = re.sub(r'&(?!(?:amp|lt|gt|apos|quot|#\d+|#x[0-9a-fA-F]+);)', '&amp;', result)

    # ── Step 3: remove control characters that XML forbids ──
    # XML 1.0 allows: #x9 | #xA | #xD | [#x20-#xD7FF]
    result = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', result)

    return result


def _validate_ssml_chunk(ssml_chunk: str) -> str:
    """Validate and repair a single SSML chunk before sending to TTS.

    Attempts to parse the chunk as XML. If parsing fails, tries common
    repairs (close unclosed tags, fix entities). Returns the repaired
    chunk, or raises ValueError if unfixable.
    """
    import xml.etree.ElementTree as ET

    # First try parsing as-is
    try:
        ET.fromstring(ssml_chunk)
        return ssml_chunk  # Already valid
    except ET.ParseError as original_error:
        logger.debug(f"SSML validation failed, attempting repair: {original_error}")

    repaired = ssml_chunk

    # Repair 1: fix bare ampersands again (might have been missed)
    repaired = re.sub(r'&(?!(?:amp|lt|gt|apos|quot|#\d+|#x[0-9a-fA-F]+);)', '&amp;', repaired)

    # Repair 2: remove stray < > that aren't part of valid tags
    # A stray < not followed by a valid tag-name-start or / is text content
    repaired = re.sub(r'<(?![a-zA-Z/!])', '&lt;', repaired)
    # A stray > not preceded by a tag close or self-close pattern
    # (This is trickier; we do a simple check: if > appears outside tags)

    # Repair 3: remove empty emphasis/prosody/say-as tags that might trip up TTS
    repaired = re.sub(r'<(emphasis|prosody|say-as)[^>]*/>', '', repaired)

    # Try parsing again
    try:
        ET.fromstring(repaired)
        logger.info("SSML chunk repaired successfully")
        return repaired
    except ET.ParseError as e:
        # Log the problematic content for debugging
        logger.error(f"SSML chunk unfixable: {e}")
        logger.debug(f"Problematic SSML (first 500 chars): {repaired[:500]}")

        # Last resort: strip ALL SSML tags and wrap in minimal valid SSML
        text_only = re.sub(r'<[^>]+>', ' ', repaired)
        text_only = re.sub(r'\s+', ' ', text_only).strip()
        fallback = f"<speak><p><s>{text_only}</s></p></speak>"
        logger.warning("Falling back to plain text in <speak> wrapper")
        return fallback


SSML_WRAPPER_OVERHEAD = len('<speak></speak>') + 2  # 17 bytes with newlines


def chunk_ssml_for_tts(ssml: str, max_bytes: int = MAX_TTS_BYTES) -> List[Dict[str, Any]]:
    """
    Split SSML content into chunks that fit within the TTS byte limit.
    Splits at </p> paragraph boundaries, preserving valid XML structure.
    Each chunk is wrapped in <speak>...</speak>.

    Returns list of dicts with 'text' (containing SSML), 'index',
    'is_section_start' keys.
    """
    if not ssml or not ssml.strip():
        return []

    # Sanitize: remove unsupported tags before chunking
    ssml = _sanitize_ssml(ssml)

    stripped = ssml.strip()

    # Remove leading XML comment if present
    if stripped.startswith('<!--'):
        comment_end = stripped.find('-->')
        if comment_end != -1:
            stripped = stripped[comment_end + 3:].strip()

    # Strip outer <speak>...</speak> wrapper
    if stripped.startswith('<speak>'):
        stripped = stripped[len('<speak>'):]
    if stripped.endswith('</speak>'):
        stripped = stripped[:-len('</speak>')]
    stripped = stripped.strip()

    # Split into logical blocks at paragraph boundaries
    blocks = _split_ssml_into_blocks(stripped)
    logger.debug(f"SSML split into {len(blocks)} blocks")

    if not blocks:
        # Fallback: treat entire content as one chunk
        wrapped = f"<speak>{stripped}</speak>"
        if len(wrapped.encode('utf-8')) <= max_bytes:
            return [{'text': wrapped, 'index': 0, 'is_section_start': False}]
        else:
            # Force fallback to sentence splitting
            return _chunk_ssml_by_sentences(stripped, max_bytes)

    effective_limit = max_bytes - SSML_WRAPPER_OVERHEAD
    chunks = []
    current_block_content = ""
    chunk_index = 0

    for block in blocks:
        block_bytes = len(block.encode('utf-8'))
        current_bytes = len(current_block_content.encode('utf-8'))

        # Check if adding this block would exceed the limit
        test_content = (current_block_content + "\n" + block).strip() if current_block_content else block
        if current_block_content and len(test_content.encode('utf-8')) > effective_limit:
            # Flush current accumulator as a chunk
            chunk_ssml = f"<speak>\n{current_block_content.strip()}\n</speak>"
            is_section = _ssml_block_is_section_start(current_block_content)
            chunks.append({
                'text': chunk_ssml,
                'index': chunk_index,
                'is_section_start': is_section,
            })
            logger.debug(f"SSML chunk {chunk_index}: {len(chunk_ssml.encode('utf-8'))} bytes")
            chunk_index += 1
            current_block_content = ""

        # Check if a single block exceeds the limit
        if block_bytes > effective_limit:
            # Flush any accumulated content first
            if current_block_content.strip():
                chunk_ssml = f"<speak>\n{current_block_content.strip()}\n</speak>"
                chunks.append({
                    'text': chunk_ssml,
                    'index': chunk_index,
                    'is_section_start': _ssml_block_is_section_start(current_block_content),
                })
                logger.debug(f"SSML chunk {chunk_index}: {len(chunk_ssml.encode('utf-8'))} bytes")
                chunk_index += 1
                current_block_content = ""

            # Split this oversized block at </s> boundaries
            logger.debug(f"Oversized block ({block_bytes} bytes), splitting by sentences")
            sub_chunks = _chunk_ssml_paragraph_by_sentences(block, effective_limit)
            for sub in sub_chunks:
                chunk_ssml = f"<speak>\n{sub.strip()}\n</speak>"
                chunks.append({
                    'text': chunk_ssml,
                    'index': chunk_index,
                    'is_section_start': False,
                })
                logger.debug(f"SSML chunk {chunk_index} (sub-split): {len(chunk_ssml.encode('utf-8'))} bytes")
                chunk_index += 1
        else:
            current_block_content = test_content if current_block_content else block

    # Flush remaining content
    if current_block_content.strip():
        chunk_ssml = f"<speak>\n{current_block_content.strip()}\n</speak>"
        chunks.append({
            'text': chunk_ssml,
            'index': chunk_index,
            'is_section_start': _ssml_block_is_section_start(current_block_content),
        })
        logger.debug(f"SSML chunk {chunk_index} (final): {len(chunk_ssml.encode('utf-8'))} bytes")

    logger.info(f"SSML chunked into {len(chunks)} chunks")
    return chunks


def _split_ssml_into_blocks(content: str) -> List[str]:
    """Split SSML content into logical blocks at paragraph boundaries.

    Each block contains one <p>...</p> paragraph, along with any preceding
    inter-paragraph material (<break> elements, <prosody> section headers).
    """
    # Find all <p> start positions
    p_starts = [m.start() for m in re.finditer(r'<p\b', content)]

    if not p_starts:
        # No <p> tags; return content as single block
        return [content] if content.strip() else []

    blocks = []
    for i, start in enumerate(p_starts):
        # Block starts either at previous </p> end or at content start
        if i == 0:
            block_start = 0
        else:
            # Find the </p> that closed the previous paragraph
            prev_p_close = content.rfind('</p>', 0, start)
            if prev_p_close != -1:
                block_start = prev_p_close + len('</p>')
            else:
                block_start = start

        # Find the closing </p> for this <p>
        p_end = content.find('</p>', start)
        if p_end == -1:
            block_end = len(content)
        else:
            block_end = p_end + len('</p>')

        block = content[block_start:block_end].strip()
        if block:
            blocks.append(block)

    return blocks


def _chunk_ssml_paragraph_by_sentences(paragraph_block: str, max_bytes: int) -> List[str]:
    """Split an oversized SSML paragraph block at </s> sentence boundaries."""
    # Extract the <p>...</p> content
    p_match = re.search(r'<p\b[^>]*>(.*?)</p>', paragraph_block, re.DOTALL)
    if not p_match:
        return [paragraph_block] if paragraph_block.strip() else []

    pre_content = paragraph_block[:p_match.start()].strip()  # breaks, headers before <p>
    inner = p_match.group(1)

    # Split at </s> boundaries, keeping the closing tag with its sentence
    sentence_parts = re.split(r'(</s>)', inner)
    sentence_blocks = []
    i = 0
    while i < len(sentence_parts):
        if i + 1 < len(sentence_parts) and sentence_parts[i + 1] == '</s>':
            sentence_blocks.append(sentence_parts[i] + sentence_parts[i + 1])
            i += 2
        else:
            if sentence_parts[i].strip():
                sentence_blocks.append(sentence_parts[i])
            i += 1

    # Accumulate sentences into sub-chunks
    sub_chunks = []
    current = ""
    prefix = (pre_content + "\n") if pre_content else ""

    for sent in sentence_blocks:
        test_content = current + sent if current else sent
        # Account for <p></p> wrapper and prefix
        if not sub_chunks and prefix:
            full_test = f"{prefix}<p>{test_content}</p>"
        else:
            full_test = f"<p>{test_content}</p>"

        if current and len(full_test.encode('utf-8')) > max_bytes:
            # Flush current
            if not sub_chunks and prefix:
                chunk = f"{prefix}<p>{current}</p>"
            else:
                chunk = f"<p>{current}</p>"
            sub_chunks.append(chunk)
            current = sent
        else:
            current = test_content

    if current.strip():
        if not sub_chunks and prefix:
            chunk = f"{prefix}<p>{current}</p>"
        else:
            chunk = f"<p>{current}</p>"
        sub_chunks.append(chunk)

    return sub_chunks


def _chunk_ssml_by_sentences(content: str, max_bytes: int) -> List[Dict[str, Any]]:
    """Fallback: chunk raw SSML content by </s> boundaries when no <p> structure exists."""
    effective_limit = max_bytes - SSML_WRAPPER_OVERHEAD
    sentence_parts = re.split(r'(</s>)', content)
    sentence_blocks = []
    i = 0
    while i < len(sentence_parts):
        if i + 1 < len(sentence_parts) and sentence_parts[i + 1] == '</s>':
            sentence_blocks.append(sentence_parts[i] + sentence_parts[i + 1])
            i += 2
        else:
            if sentence_parts[i].strip():
                sentence_blocks.append(sentence_parts[i])
            i += 1

    chunks = []
    current = ""
    chunk_index = 0

    for sent in sentence_blocks:
        test = current + sent if current else sent
        if current and len(test.encode('utf-8')) > effective_limit:
            chunk_ssml = f"<speak>\n{current.strip()}\n</speak>"
            chunks.append({
                'text': chunk_ssml,
                'index': chunk_index,
                'is_section_start': False,
            })
            chunk_index += 1
            current = sent
        else:
            current = test

    if current.strip():
        chunk_ssml = f"<speak>\n{current.strip()}\n</speak>"
        chunks.append({
            'text': chunk_ssml,
            'index': chunk_index,
            'is_section_start': False,
        })

    return chunks


def _ssml_block_is_section_start(content: str) -> bool:
    """Check if an SSML block contains a section header (prosody tag)."""
    return bool(re.search(r'<prosody[^>]*>', content))


# ── Audio Generator Class ──

class AudioGenerator:
    """Google Cloud TTS audio generator with chunking and concatenation."""

    def __init__(self):
        self.client = None
        self.is_ready = False
        self._last_request_time = 0.0

        # Default settings
        self.voice_name = DEFAULT_VOICE
        self.language_code = DEFAULT_LANGUAGE
        self.speaking_rate = DEFAULT_SPEAKING_RATE
        self.audio_format = DEFAULT_ENCODING
        self.bitrate = "128k"
        self.volume_gain_db = 0.0
        self.pitch_semitones = 0.0  # Only effective for Neural2; ignored by Chirp3 HD
        self.normalize_audio = True

        # Initialize client
        self._init_client()

    def _init_client(self):
        """Initialize the Google Cloud TTS client."""
        if not TTS_AVAILABLE:
            print("Google Cloud TTS SDK not available")
            logger.warning("Google Cloud TTS SDK not available")
            return

        # If GOOGLE_APPLICATION_CREDENTIALS points to a missing file,
        # unset it so the SDK falls back to Application Default Credentials
        gac = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '')
        if gac and not os.path.exists(gac):
            print(f"Note: GOOGLE_APPLICATION_CREDENTIALS file not found: {gac}")
            print("  Unsetting it to use Application Default Credentials instead.")
            logger.info(f"GOOGLE_APPLICATION_CREDENTIALS not found: {gac}, unsetting to use ADC")
            del os.environ['GOOGLE_APPLICATION_CREDENTIALS']

        try:
            self.client = texttospeech.TextToSpeechClient()
            self.is_ready = True
            print("Google Cloud TTS client initialized")
            logger.info("Google Cloud TTS client initialized")
        except Exception as e:
            print(f"Failed to initialize TTS client: {e}")
            print("Make sure Google Cloud credentials are configured:")
            print("  gcloud auth application-default login")
            print("  or: export GOOGLE_APPLICATION_CREDENTIALS='/path/to/key.json'")
            logger.error(f"Failed to initialize TTS client: {e}", exc_info=True)
            self.is_ready = False

    def _get_audio_encoding(self) -> 'texttospeech.AudioEncoding':
        """Get the TTS audio encoding enum for the current format."""
        fmt = self.audio_format.upper()
        if fmt in ("MP3", "M4B"):
            # M4B: we synthesize as MP3 then convert via pydub to M4A/M4B
            return texttospeech.AudioEncoding.MP3
        elif fmt == "WAV":
            return texttospeech.AudioEncoding.LINEAR16
        elif fmt == "OGG":
            return texttospeech.AudioEncoding.OGG_OPUS
        else:
            return texttospeech.AudioEncoding.MP3

    def _rate_limit(self):
        """Enforce rate limiting between API calls."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < MIN_REQUEST_INTERVAL:
            time.sleep(MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.time()

    def synthesize_chunk(self, text: str, is_ssml: bool = False) -> Optional[bytes]:
        """
        Synthesize a single text or SSML chunk to audio bytes.

        Args:
            text: The text or SSML content to synthesize.
            is_ssml: If True, treat input as SSML (use SynthesisInput(ssml=...)).

        Returns raw audio bytes (MP3/WAV/OGG) or None on failure.
        """
        if not self.is_ready or not self.client:
            logger.error("synthesize_chunk called but TTS client not ready")
            return None

        # Validate & repair SSML before sending to the API
        if is_ssml:
            try:
                text = _validate_ssml_chunk(text)
            except Exception as e:
                logger.error(f"SSML validation/repair failed: {e}")
                return None

        input_bytes = len(text.encode('utf-8'))
        logger.debug(f"synthesize_chunk: {input_bytes} bytes, "
                     f"mode={'ssml' if is_ssml else 'text'}, "
                     f"voice={self.voice_name}")

        try:
            self._rate_limit()

            if is_ssml:
                synthesis_input = texttospeech.SynthesisInput(ssml=text)
            else:
                synthesis_input = texttospeech.SynthesisInput(text=text)

            voice_params = texttospeech.VoiceSelectionParams(
                language_code=self.language_code,
                name=self.voice_name,
            )

            audio_config_params = {
                'audio_encoding': self._get_audio_encoding(),
                'speaking_rate': self.speaking_rate,
                'volume_gain_db': self.volume_gain_db,
            }
            if self.pitch_semitones != 0.0:
                audio_config_params['pitch'] = self.pitch_semitones

            audio_config = texttospeech.AudioConfig(**audio_config_params)

            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice_params,
                audio_config=audio_config,
            )

            logger.debug(f"synthesize_chunk: received {len(response.audio_content)} audio bytes")
            return response.audio_content

        except Exception as e:
            print(f"TTS synthesis error: {e}")
            logger.error(f"TTS synthesis error: {e}", exc_info=True)
            return None

    def generate_audio(
        self,
        text: str,
        output_path: str,
        title: str = "",
        author: str = "",
        description: str = "",
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a complete audio file from text or SSML.

        Args:
            text: The full text or SSML to convert to speech.
            output_path: Output file path (.mp3, .wav, .ogg, or .m4b).
            title: Paper title for metadata.
            author: Author name for metadata.
            description: Description text for metadata.
            progress_callback: Callback(message, progress_fraction).

        Returns:
            Dict with success, output_path, duration_seconds, file_size_bytes, etc.
        """
        start_time = time.time()

        if not self.is_ready:
            logger.error("generate_audio called but TTS client not ready")
            return {
                'success': False,
                'error': 'TTS client not initialized. Check Google Cloud credentials.',
                'output_path': '',
            }

        if not text or not text.strip():
            return {
                'success': False,
                'error': 'No text provided.',
                'output_path': '',
            }

        # Detect input type (SSML vs plain text)
        ssml_mode = is_ssml_content(text)
        logger.info(f"Starting audio generation: input_type={'SSML' if ssml_mode else 'plain text'}, "
                    f"voice={self.voice_name}, rate={self.speaking_rate}, format={self.audio_format}")
        logger.debug(f"Input: {len(text)} chars, {len(text.encode('utf-8'))} bytes")

        # Determine output format from path extension
        out_path = Path(output_path)
        ext = out_path.suffix.lower()
        if ext == '.m4b':
            self.audio_format = 'M4B'
        elif ext == '.wav':
            self.audio_format = 'WAV'
        elif ext == '.ogg':
            self.audio_format = 'OGG'
        else:
            self.audio_format = 'MP3'

        # Step 1: Chunk the text
        if progress_callback:
            progress_callback("Splitting text into chunks...", 0.0)

        if ssml_mode:
            chunks = chunk_ssml_for_tts(text)
        else:
            chunks = chunk_text_for_tts(text)
        total_chunks = len(chunks)

        if total_chunks == 0:
            logger.error("Text produced no valid chunks")
            return {
                'success': False,
                'error': 'Text produced no valid chunks.',
                'output_path': '',
            }

        print(f"Audio generation: {total_chunks} chunks to synthesize")
        logger.info(f"Audio generation: {total_chunks} chunks to synthesize")

        # Step 2: Synthesize each chunk
        audio_segments = []
        chapter_markers = []  # (title, start_ms) for M4B chapters
        failed_chunks = 0
        current_ms = 0
        total_billable_chars = 0

        for i, chunk_info in enumerate(chunks):
            chunk_text = chunk_info['text']
            chunk_idx = chunk_info['index']
            is_section = chunk_info.get('is_section_start', False)

            if progress_callback:
                pct = (i / total_chunks) * 0.8  # 80% for synthesis
                progress_callback(
                    f"Synthesizing chunk {i + 1}/{total_chunks}...", pct
                )

            # Retry logic
            chunk_start_time = time.time()
            audio_bytes = None
            for attempt in range(3):
                audio_bytes = self.synthesize_chunk(chunk_text, is_ssml=ssml_mode)
                if audio_bytes:
                    break
                print(f"  Retry {attempt + 1} for chunk {i + 1}")
                logger.warning(f"Retry {attempt + 1}/3 for chunk {i + 1}/{total_chunks}")
                if attempt == 0 and ssml_mode:
                    # Log the problematic SSML on first failure for debugging
                    logger.error(f"Failing SSML chunk {i + 1} content "
                                 f"(first 300 chars):\n{chunk_text[:300]}")
                time.sleep(1.0 * (attempt + 1))

            chunk_elapsed = time.time() - chunk_start_time

            if audio_bytes:
                total_billable_chars += _count_billable_chars(chunk_text)
                logger.debug(f"Chunk {i + 1}/{total_chunks}: "
                            f"{len(audio_bytes)} audio bytes, {chunk_elapsed:.2f}s")
                try:
                    # Load into pydub
                    fmt_for_pydub = "mp3" if self.audio_format in ("MP3", "M4B") else (
                        "wav" if self.audio_format == "WAV" else "ogg"
                    )
                    segment = AudioSegment.from_file(
                        _bytes_to_tempfile(audio_bytes, f".{fmt_for_pydub}"),
                        format=fmt_for_pydub,
                    )

                    # Track chapter marker if this is a section start
                    if is_section:
                        if ssml_mode:
                            # Extract section title from <prosody> tag
                            prosody_match = re.search(
                                r'<prosody[^>]*>(.*?)</prosody>', chunk_text
                            )
                            if prosody_match:
                                section_title = prosody_match.group(1).strip()
                            else:
                                section_title = f"Section {len(chapter_markers) + 1}"
                        else:
                            section_title = chunk_text.strip().split('\n')[0].strip()
                            section_title = section_title.rstrip('.')
                        chapter_markers.append((section_title, current_ms))

                    current_ms += len(segment)
                    audio_segments.append(segment)

                except Exception as e:
                    print(f"  Error loading audio for chunk {i + 1}: {e}")
                    logger.error(f"Error loading audio for chunk {i + 1}: {e}", exc_info=True)
                    failed_chunks += 1
            else:
                failed_chunks += 1
                print(f"  Failed to synthesize chunk {i + 1}")
                logger.error(f"Failed to synthesize chunk {i + 1}/{total_chunks} after 3 retries")

        if not audio_segments:
            logger.error("All chunks failed to synthesize")
            return {
                'success': False,
                'error': 'All chunks failed to synthesize.',
                'output_path': '',
            }

        logger.info(f"Synthesis complete: {len(audio_segments)}/{total_chunks} chunks succeeded, "
                    f"{failed_chunks} failed")

        # Step 3: Concatenate audio segments
        if progress_callback:
            progress_callback("Concatenating audio segments...", 0.82)

        combined = audio_segments[0]
        for seg in audio_segments[1:]:
            combined += seg

        # Step 4: Normalize audio
        if self.normalize_audio and PYDUB_AVAILABLE:
            if progress_callback:
                progress_callback("Normalizing audio...", 0.88)
            combined = pydub_normalize(combined)

        # Step 5: Export to file
        if progress_callback:
            progress_callback("Exporting audio file...", 0.90)

        out_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if self.audio_format == "M4B":
                # Export as M4A first (AAC codec), then rename to .m4b
                # pydub exports m4a via ffmpeg
                temp_m4a = str(out_path.with_suffix('.m4a'))
                bitrate_val = self.bitrate if self.bitrate else "128k"
                combined.export(
                    temp_m4a,
                    format="ipod",  # pydub format name for m4a/aac
                    bitrate=bitrate_val,
                    parameters=["-movflags", "+faststart"],
                )
                # Rename .m4a to .m4b (they are the same container format)
                import shutil
                shutil.move(temp_m4a, str(out_path))

            elif self.audio_format == "MP3":
                bitrate_val = self.bitrate if self.bitrate else "128k"
                combined.export(
                    str(out_path), format="mp3", bitrate=bitrate_val
                )

            elif self.audio_format == "WAV":
                combined.export(str(out_path), format="wav")

            elif self.audio_format == "OGG":
                combined.export(str(out_path), format="ogg")

        except Exception as e:
            logger.error(f"Failed to export audio: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Failed to export audio: {e}',
                'output_path': '',
            }

        # Step 6: Add metadata
        if progress_callback:
            progress_callback("Adding metadata...", 0.95)

        try:
            if self.audio_format == "MP3" and MUTAGEN_AVAILABLE:
                self._add_mp3_metadata(
                    str(out_path), title, author, description, chapter_markers
                )
            elif self.audio_format == "M4B" and MUTAGEN_AVAILABLE:
                self._add_m4b_metadata(
                    str(out_path), title, author, description, chapter_markers,
                    combined,
                )
        except Exception as e:
            print(f"Warning: failed to add metadata: {e}")
            logger.warning(f"Failed to add metadata: {e}", exc_info=True)

        # Step 7: Calculate statistics
        elapsed = time.time() - start_time
        file_size = out_path.stat().st_size
        duration_seconds = len(combined) / 1000.0

        if progress_callback:
            progress_callback("Done!", 1.0)

        # Calculate TTS cost based on voice model
        if 'Neural2' in self.voice_name:
            tts_price_per_char = TTS_PRICE_NEURAL2
        else:
            tts_price_per_char = TTS_PRICE_CHIRP3_HD
        tts_cost = total_billable_chars * tts_price_per_char

        result = {
            'success': True,
            'output_path': str(out_path),
            'duration_seconds': duration_seconds,
            'duration_formatted': _format_duration(duration_seconds),
            'file_size_bytes': file_size,
            'file_size_formatted': _format_file_size(file_size),
            'total_chunks': total_chunks,
            'failed_chunks': failed_chunks,
            'generation_time_seconds': elapsed,
            'voice_used': self.voice_name,
            'speaking_rate': self.speaking_rate,
            'audio_format': self.audio_format,
            'chapter_count': len(chapter_markers),
            'tts_characters': total_billable_chars,
            'tts_cost': tts_cost,
        }

        print(f"Audio generated: {result['duration_formatted']}, "
              f"{result['file_size_formatted']}, {elapsed:.1f}s, "
              f"{total_billable_chars:,} chars, est. TTS cost: ${tts_cost:.4f}")
        logger.info(f"Audio generated: {result['duration_formatted']}, "
                   f"{result['file_size_formatted']}, {elapsed:.1f}s, "
                   f"{total_chunks - failed_chunks}/{total_chunks} chunks OK")

        return result

    def preview_voice(
        self,
        sample_text: str = "This is a preview of the selected voice for Science2Go.",
    ) -> Optional[bytes]:
        """
        Generate a short audio preview of the current voice settings.
        Returns MP3 bytes or None.
        """
        if not self.is_ready:
            return None

        # Force MP3 for preview
        original_format = self.audio_format
        self.audio_format = "MP3"
        audio_bytes = self.synthesize_chunk(sample_text, is_ssml=False)
        self.audio_format = original_format
        return audio_bytes

    # ── Metadata helpers ──

    def _add_mp3_metadata(
        self,
        file_path: str,
        title: str,
        author: str,
        description: str,
        chapters: List[tuple],
    ):
        """Add ID3 tags and chapter markers to MP3 file."""
        try:
            audio = MP3(file_path)
        except ID3NoHeaderError:
            audio = MP3(file_path)
            audio.add_tags()

        if audio.tags is None:
            audio.add_tags()

        audio.tags.add(TIT2(encoding=3, text=title or "Science2Go Audio Paper"))
        audio.tags.add(TPE1(encoding=3, text=author or "Science2Go"))
        audio.tags.add(TALB(encoding=3, text="Science2Go"))
        audio.tags.add(TDRC(encoding=3, text=str(datetime.now().year)))
        audio.tags.add(TCON(encoding=3, text="Science"))
        audio.tags.add(TPUB(encoding=3, text="Science2Go"))

        if description:
            audio.tags.add(COMM(
                encoding=3, lang='eng', desc='Description', text=description
            ))

        # Add chapter markers if available
        if chapters:
            total_ms = int(audio.info.length * 1000)
            child_ids = []
            for i, (ch_title, start_ms) in enumerate(chapters):
                end_ms = chapters[i + 1][1] if i + 1 < len(chapters) else total_ms
                element_id = f"chp{i}"
                child_ids.append(element_id)

                audio.tags.add(CHAP(
                    element_id=element_id,
                    start_time=int(start_ms),
                    end_time=int(end_ms),
                    sub_frames=[TIT2(encoding=3, text=ch_title)],
                ))

            audio.tags.add(CTOC(
                element_id="toc",
                flags=3,  # Top-level, ordered
                child_element_ids=child_ids,
                sub_frames=[TIT2(encoding=3, text="Table of Contents")],
            ))

        audio.save()

    def _add_m4b_metadata(
        self,
        file_path: str,
        title: str,
        author: str,
        description: str,
        chapters: List[tuple],
        combined_segment: 'AudioSegment',
    ):
        """Add MP4/M4B metadata tags. Chapter markers via ffmpeg if available."""
        try:
            audio = MP4(file_path)
            audio["\xa9nam"] = title or "Science2Go Audio Paper"
            audio["\xa9ART"] = author or "Science2Go"
            audio["\xa9alb"] = "Science2Go"
            audio["\xa9day"] = str(datetime.now().year)
            audio["\xa9gen"] = "Science"
            if description:
                audio["\xa9cmt"] = description

            audio.save()

            # M4B chapter embedding requires ffmpeg + chapter metadata file
            # For now, chapters are stored in the description as text
            if chapters:
                chapter_text = "Chapters:\n"
                for ch_title, start_ms in chapters:
                    t = _format_duration(start_ms / 1000.0)
                    chapter_text += f"  {t} - {ch_title}\n"
                audio = MP4(file_path)
                audio["\xa9cmt"] = (description or "") + "\n\n" + chapter_text
                audio.save()

        except Exception as e:
            print(f"Warning: M4B metadata error: {e}")
            logger.warning(f"M4B metadata error: {e}", exc_info=True)

    def list_available_voices(self) -> Dict[str, List[str]]:
        """
        List available Chirp 3 HD voices from the API, or fall back to hardcoded list.
        Returns dict with 'male' and 'female' keys.
        """
        # Try API listing first
        if self.is_ready and self.client:
            try:
                response = self.client.list_voices(language_code=self.language_code)
                male = []
                female = []
                for voice in response.voices:
                    if "Chirp3-HD" in voice.name:
                        # Determine gender from known lists
                        if voice.name in CHIRP3_HD_MALE_VOICES:
                            male.append(voice.name)
                        elif voice.name in CHIRP3_HD_FEMALE_VOICES:
                            female.append(voice.name)
                        else:
                            male.append(voice.name)  # Default to male list
                if male or female:
                    return {'male': sorted(male), 'female': sorted(female)}
            except Exception:
                pass

        # Fallback to hardcoded
        return {
            'male': CHIRP3_HD_MALE_VOICES,
            'female': CHIRP3_HD_FEMALE_VOICES,
        }


# ── Helper functions ──

def _count_billable_chars(text: str) -> int:
    """Count TTS billable characters (text only, not SSML markup tags)."""
    text_only = re.sub(r'<[^>]+>', '', text)
    return len(text_only.strip())


def _bytes_to_tempfile(audio_bytes: bytes, suffix: str = ".mp3") -> str:
    """Write audio bytes to a temp file and return the path."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(audio_bytes)
    tmp.close()
    return tmp.name


def _format_duration(seconds: float) -> str:
    """Format seconds into HH:MM:SS or MM:SS."""
    total = int(seconds)
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _format_file_size(size_bytes: int) -> str:
    """Format file size into human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


# ── Module-level instance ──

audio_generator = AudioGenerator()
