# Science2Go - Project Status & TODO

**Last updated:** 2026-02-08

---

## Current Pipeline Status

| Step | Component | Status | Notes |
|------|-----------|--------|-------|
| 1 | PDF loading & metadata extraction | DONE | PyPDF2 + CrossRef API |
| 2 | PDF to Markdown conversion | DONE | marker-pdf, preserves structure, strips headers/footers |
| 3 | AI text cleanup for TTS | DONE | Gemini 2.5 Flash, removes citations/refs, expands symbols |
| 4 | Save/Load processed text | DONE | .md files with JSON metadata header |
| 5 | Text-to-Speech audio generation | NOT STARTED | Google Cloud TTS SDK installed but no code |
| 6 | Audio post-processing | NOT STARTED | pydub + mutagen installed but unused |
| GUI | CustomTkinter migration | DONE | Modern UI with dark/light mode |
| GUI | Paper Setup tab | DONE | PDF browse, analyze, convert to markdown |
| GUI | Markdown Processing tab | DONE | AI processing, save/load |
| GUI | Audio Config tab | PLACEHOLDER | Needs voice selection, rate, pitch controls |
| GUI | Output Generation tab | PLACEHOLDER | Needs generate button, progress, export |

---

## TODO: TTS Audio Generation Pipeline

### 1. Create `src/processors/audio_generator.py` (NEW FILE)
- [ ] Google Cloud TTS client wrapper class
- [ ] Voice selection (Chirp 3 HD, Neural2, WaveNet, Studio)
- [ ] Text chunking for TTS (API has input size limits)
- [ ] Audio synthesis: text chunk -> MP3/WAV
- [ ] Concatenate chunks into single audio file (pydub)
- [ ] Audio normalization
- [ ] MP3 metadata tagging (mutagen) - title, author, description
- [ ] Chapter markers (if supported)
- [ ] Progress callback for GUI updates
- [ ] Graceful error handling and retries

### 2. Implement Audio Config Tab
- [ ] Voice type selector (Chirp 3 HD / Neural2 / Studio / WaveNet)
- [ ] Voice name dropdown (filtered by type + locale)
- [ ] Language/locale selector (en-GB, en-US, etc.)
- [ ] Speaking rate slider (0.25x - 2.0x, default 0.95)
- [ ] Pitch adjustment slider
- [ ] Audio format selector (MP3, WAV, OGG)
- [ ] Output bitrate selector (128k, 192k, 256k, 320k)
- [ ] Preview button (synthesize a short sample)
- [ ] Save voice preferences

### 3. Implement Output Generation Tab
- [ ] "Generate Podcast" button
- [ ] Progress bar with chunk-by-chunk updates
- [ ] Output file path selector
- [ ] Auto-filename from paper title + date
- [ ] Combine description + processed content option
- [ ] Generated audio preview/playback
- [ ] Export in multiple formats
- [ ] Show generation statistics (duration, file size)

### 4. Wire Full Pipeline
- [ ] End-to-end: PDF -> Markdown -> AI cleanup -> TTS -> MP3
- [ ] Error handling at each stage
- [ ] Ability to resume from any stage (e.g., re-generate audio from saved processed text)

---

## Voice Selection Decision (pending)

**Recommended:** Chirp 3: HD (latest generation, most natural)
**Locale:** en-GB (British English)
**Gender:** Male (user preference)

### Top male en-GB Chirp 3 HD candidates to audition:
- en-GB-Chirp3-HD-Achird
- en-GB-Chirp3-HD-Algenib
- en-GB-Chirp3-HD-Algieba
- en-GB-Chirp3-HD-Alnilam
- en-GB-Chirp3-HD-Charon
- en-GB-Chirp3-HD-Enceladus
- en-GB-Chirp3-HD-Fenrir
- en-GB-Chirp3-HD-Iapetus
- en-GB-Chirp3-HD-Orus
- en-GB-Chirp3-HD-Puck
- en-GB-Chirp3-HD-Rasalgethi
- en-GB-Chirp3-HD-Sadachbia
- en-GB-Chirp3-HD-Sadaltager
- en-GB-Chirp3-HD-Schedar
- en-GB-Chirp3-HD-Umbriel
- en-GB-Chirp3-HD-Zubenelgenubi

---

## Recent Changes (2026-02-08)

1. Created `src/processors/pdf_converter.py` - marker-pdf integration
2. Migrated entire GUI from Tkinter/ttk to CustomTkinter
3. Added PDF-to-Markdown workflow in Paper Setup tab
4. Upgraded Gemini model from 1.5-pro to 2.5-flash
5. Increased max_output_tokens from 8192 to 65536
6. Updated google-generativeai SDK requirement to >=0.8.0
7. Simplified `src/gui/platform_utils.py` for CustomTkinter

---

## Technical Notes

- **Gemini model:** gemini-2.5-flash (stable, 1M context, 65K output tokens)
- **marker-pdf:** installed via pip (not on conda-forge), requires PyTorch
- **CustomTkinter:** v5.2.2, installed via pip
- **Conda env:** science2go (Python 3.11, miniforge3)
- **Python path:** /Users/oq50iqeq/miniforge3/envs/science2go/bin/python
