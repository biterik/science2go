# src/processors/text_processor.py
from __future__ import annotations

import os
import re
import time
import json
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional, List

import requests

__all__ = [
    "GeminiRESTConfig",
    "ProcessorConfig",
    "AdvancedTextProcessor",
    "process_markdown_content",   # legacy shim expected by main.py
    "process_plain_text",         # optional convenience
]

# ---------------- Template Manager (optional) ----------------
_TEMPLATE_MANAGER = None
try:
    from templates.template_manager import TemplateManager  # type: ignore
    _TEMPLATE_MANAGER = TemplateManager()
except Exception as _e:
    logging.debug(f"TemplateManager not available: {_e}")
    _TEMPLATE_MANAGER = None

# ---------------- TTS optimizer (optional) ----------------
class _NoOpTTSOptimizer:
    def optimize_for_tts(self, text: str) -> str:
        text = re.sub(r"\s+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

class _NoOpAnalytics:
    def record_chunk_completion(self, success: bool) -> None: ...
    def record_retry(self) -> None: ...
    def record_error(self, msg: str) -> None: ...

# ---------------- REST client ----------------
_GEM_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

@dataclass
class GeminiRESTConfig:
    model: str = os.getenv("SCI2GO_GEM_MODEL", "gemini-1.5-flash")
    temperature: float = 0.1
    max_output_tokens: int = 1024
    timeout_s: int = 45
    honor_proxies: bool = True

def _gemini_rest_call(prompt_text: str, cfg: GeminiRESTConfig) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in environment.")
    url = _GEM_ENDPOINT.format(model=cfg.model)
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {
            "temperature": cfg.temperature,
            "maxOutputTokens": cfg.max_output_tokens,
        },
    }
    with requests.Session() as s:
        s.trust_env = cfg.honor_proxies
        resp = s.post(url, headers=headers, data=json.dumps(payload), timeout=cfg.timeout_s)
    resp.raise_for_status()
    data = resp.json()
    try:
        parts = data["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts).strip()
    except Exception as e:
        raise RuntimeError(f"Unexpected Gemini response: {str(e)} | {str(data)[:800]}")

# ---------------- Chunking ----------------
def _soft_split_points(text: str) -> List[int]:
    pts = []
    for m in re.finditer(r"(?<=\.)\s|\n{2,}", text):
        pts.append(m.start())
    return pts

def _chunk_text(text: str, max_chunk_size: int = 6000, overlap: int = 200) -> List[str]:
    if not text:
        return []
    if max_chunk_size <= overlap + 100:
        overlap = max(0, max_chunk_size // 5)
    soft = set(_soft_split_points(text))
    chunks: List[str] = []
    i, n = 0, len(text)
    while i < n:
        end = min(i + max_chunk_size, n)
        best = None
        for back in range(0, min(600, end - i)):
            pos = end - back
            if pos in soft and pos - i > 1000:
                best = pos
                break
        if best:
            end = best
        chunks.append(text[i:end])
        if end == n:
            break
        i = max(0, end - overlap)
    return chunks

# ---------------- Prompt assembly ----------------
def _build_prompt(raw_text: str, template_name: Optional[str] = None) -> str:
    if _TEMPLATE_MANAGER and template_name:
        try:
            sp = _TEMPLATE_MANAGER.get_system_prompt(template_name)
            up = _TEMPLATE_MANAGER.get_user_prompt(template_name, raw_text)
            return f"{sp}\n\n{up}"
        except Exception as e:
            logging.warning(f"TemplateManager failed ({e}); using fallback prompt.")
    return (
        "You are a careful text cleaner for TTS of scientific documents.\n"
        "Rules:\n"
        " - Keep all content and ordering. Do NOT summarize or omit information.\n"
        " - Remove inline citation brackets like [1], [12,13], (Ref. 5).\n"
        " - Remove figure/table callouts ('see Fig. 3', 'Table 2') unless essential.\n"
        " - Expand symbols for speech (e.g., '%' -> 'percent').\n"
        " - Normalize whitespace/punctuation; preserve math verbatim.\n"
        " - Output ONLY the cleaned text, no commentary.\n\n"
        f"TEXT:\n{raw_text}"
    )

# ---------------- Processor ----------------
@dataclass
class ProcessorConfig:
    max_chunk_size: int = 6000
    overlap_size: int = 200
    max_retries: int = 3
    base_retry_delay: float = 2.0
    gemini: GeminiRESTConfig = field(default_factory=GeminiRESTConfig)

class AdvancedTextProcessor:
    def __init__(
        self,
        cfg: Optional[ProcessorConfig] = None,
        tts_optimizer: Optional[object] = None,
        analytics: Optional[object] = None,
    ):
        self.cfg = cfg or ProcessorConfig()
        self.tts_optimizer = tts_optimizer or _NoOpTTSOptimizer()
        self.analytics = analytics or _NoOpAnalytics()

        # Ensure any other modules importing genai default to REST
        os.environ.setdefault("GOOGLE_API_TRANSPORT", "rest")
        os.environ.setdefault("GENAI_USE_GRPC", "false")

        logging.info(
            f"AdvancedTextProcessor: chunk={self.cfg.max_chunk_size}, "
            f"overlap={self.cfg.overlap_size}, retries={self.cfg.max_retries}, "
            f"model={self.cfg.gemini.model}"
        )

    def process_text(
        self,
        full_text: str,
        template_name: Optional[str] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        if not full_text:
            return ""
        chunks = _chunk_text(full_text, self.cfg.max_chunk_size, self.cfg.overlap_size)
        total = len(chunks)
        logging.info(f"📦 Processing {total} chunks")

        cleaned_parts: List[str] = []
        pos = 0
        for idx, ch in enumerate(chunks, start=1):
            cfrom = pos
            cto = pos + len(ch)
            pos = cto - self.cfg.overlap_size if idx < total else cto
            label = f"chunk {idx}/{total} (chars {cfrom}-{cto})"
            if progress_callback:
                try:
                    progress_callback(f"⚙️ Processing {label}...")
                except Exception as e:
                    logging.debug(f"Progress callback error ignored: {e}")

            cleaned = self._process_chunk_with_retry(ch, template_name, label)
            if cleaned is None:
                logging.error(f"❌ Failed to process {label}; inserting original text.")
                cleaned = ch
            cleaned_parts.append(cleaned)

        out = "\n".join(p.strip() for p in cleaned_parts if p is not None)
        out = re.sub(r"\n{3,}", "\n\n", out).strip()
        return out

    def _process_chunk_with_retry(
        self,
        chunk_text_: str,
        template_name: Optional[str],
        chunk_info: str,
    ) -> Optional[str]:
        for attempt in range(self.cfg.max_retries):
            try:
                logging.info(f"⚙️ Attempting API call for {chunk_info} (attempt {attempt+1})...")
                prompt = _build_prompt(chunk_text_, template_name)
                response_text = _gemini_rest_call(prompt, self.cfg.gemini)
                if not response_text:
                    raise RuntimeError("Empty response from Gemini REST")
                result = self.tts_optimizer.optimize_for_tts(response_text)
                self.analytics.record_chunk_completion(success=True)
                logging.info(f"✅ Successfully processed {chunk_info}.")
                return result

            except requests.Timeout:
                msg = f"Timeout on {chunk_info} (attempt {attempt+1})."
                logging.error(f"⏱️ {msg}")
                self.analytics.record_error(msg)
            except requests.HTTPError as e:
                status = e.response.status_code if e.response is not None else "?"
                body = ""
                try:
                    body = e.response.text[:500] if e.response is not None else ""
                except Exception:
                    pass
                msg = f"HTTP {status} on {chunk_info}: {body}"
                logging.error(f"❌ {msg}")
                self.analytics.record_error(msg)
            except Exception as e:
                msg = f"General Error on {chunk_info} (attempt {attempt+1}): {e}"
                logging.error(f"❌ {msg}")
                self.analytics.record_error(msg)

            if attempt < self.cfg.max_retries - 1:
                delay = self.cfg.base_retry_delay * (2 ** attempt)
                logging.warning(f"🔄 Retrying {chunk_info} in {delay:.1f}s...")
                self.analytics.record_retry()
                time.sleep(delay)
            else:
                logging.error(f"❌ All retries failed for {chunk_info}.")
                self.analytics.record_chunk_completion(success=False)
                return None
        return None

# ---------------- Legacy shims (so main.py keeps working) ----------------
def process_markdown_content(
    markdown_text: str,
    template_name: Optional[str] = None,
    *,
    progress_callback: Optional[Callable[[str], None]] = None,
    processor_config: Optional[ProcessorConfig] = None,
    tts_optimizer: Optional[object] = None,
    analytics: Optional[object] = None,
) -> str:
    """
    Backwards-compatible entrypoint expected by main.py.
    Creates an AdvancedTextProcessor and runs process_text().
    """
    proc = AdvancedTextProcessor(
        cfg=processor_config or ProcessorConfig(),
        tts_optimizer=tts_optimizer,
        analytics=analytics,
    )
    return proc.process_text(markdown_text, template_name=template_name, progress_callback=progress_callback)

def process_plain_text(
    raw_text: str,
    *,
    progress_callback: Optional[Callable[[str], None]] = None,
    processor_config: Optional[ProcessorConfig] = None,
) -> str:
    proc = AdvancedTextProcessor(cfg=processor_config or ProcessorConfig())
    return proc.process_text(raw_text, template_name=None, progress_callback=progress_callback)