# Science2Go

**Turn Academic Papers into Audio Papers**

Science2Go converts scientific PDF papers into high-quality audio files you can listen to on the go. The pipeline extracts text from PDFs, uses Gemini AI to clean it for spoken delivery, converts to SSML for fine-grained speech control, and synthesizes natural-sounding speech with Google Cloud TTS.

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

---

## Pipeline Overview

```
PDF  →  Markdown  →  AI Cleanup  →  SSML  →  TTS  →  MP3 / M4B
        (marker-pdf    (Gemini 2.5    (SSML v1.1   (Google Cloud TTS
         or pdftext)     Flash)        markup)       Chirp 3 HD / Neural2)
```

| Tab | Step | Description |
|-----|------|-------------|
| 1. Paper Information | PDF upload + metadata | Extract title, authors, abstract, DOI via CrossRef API. Save/load paper info as JSON. Generate audio paper description. |
| 2. PDF to Markdown | PDF → MD conversion | Uses marker-pdf for high-quality conversion with three modes (Fast Extract, Marker no-OCR, Full Pipeline). |
| 3. Markdown Processing | AI text cleanup | Gemini 2.5 Flash cleans text using YAML templates. Removes citations, expands abbreviations, optimizes for speech. API cost tracking. |
| 4. MD to SSML | SSML conversion | Converts cleaned text to SSML v1.1 with paragraph/sentence structure, emphasis, prosody, and natural pacing. Built-in SSML editor with save/load. |
| 5. Audio Config | Voice & format setup | Select voice model (Chirp 3 HD or Neural2), choose from 34 voices, adjust rate/pitch, pick output format. |
| 6. Speech Output | TTS generation | Generate audio with progress tracking, TTS cost estimate, auto-detected chapter markers, and export to MP3/WAV/OGG/M4B. |

---

## Prerequisites

Before installing Science2Go, you need accounts and API keys for two Google services:

### 1. Google AI Studio (for Gemini text processing)

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click **Create API Key**
4. Copy the key (starts with `AIza...`)

This is free tier and sufficient for processing papers.

### 2. Google Cloud (for Text-to-Speech)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a Google Cloud account if you don't have one (free tier includes TTS characters/month; check [Cloud TTS pricing](https://cloud.google.com/text-to-speech/pricing) for Chirp 3 HD and Neural2 rates)
3. Create a new project (e.g., "science2go-tts")
4. Enable the **Cloud Text-to-Speech API**:
   - Go to **APIs & Services** > **Library**
   - Search for "Text-to-Speech"
   - Click **Enable**
5. Set up authentication (choose one):
   - **Option A (recommended):** Install the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) and run:
     ```bash
     gcloud auth application-default login
     ```
     This opens a browser to authenticate and stores credentials locally.
   - **Option B:** Create a service account key:
     - Go to **IAM & Admin** > **Service Accounts**
     - Create a service account, grant it the "Cloud Text-to-Speech User" role
     - Create a JSON key and download it
     - Set the path: `export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"`
   - **Option C:** Create an API key:
     - Go to **APIs & Services** > **Credentials**
     - Click **Create Credentials** > **API Key**
     - Set: `export GOOGLE_API_KEY="your_key"`

### 3. System requirements

- **Python 3.11+**
- **Conda** (miniforge or miniconda recommended) or pip
- **ffmpeg** (for audio processing -- install via `brew install ffmpeg` on macOS, or `conda install ffmpeg`)

---

## Installation

```bash
# Clone the repository
git clone https://github.com/biterik/science2go.git
cd science2go

# Create conda environment (installs all dependencies)
conda env create -f environment.yml
conda activate science2go

# Optional: enable PDF-to-Markdown conversion (pulls in PyTorch ~2GB)
pip install marker-pdf pdftext
```

### Configure API keys

Add your keys to your shell profile (`~/.zshrc` on macOS, `~/.bashrc` on Linux):

```bash
# Required: Gemini AI for text processing
export GEMINI_API_KEY="your_gemini_api_key_here"

# For TTS (if not using gcloud auth application-default login):
export GOOGLE_API_KEY="your_google_api_key_here"
```

Then reload: `source ~/.zshrc`

### Run

```bash
./run.sh
# or: python main.py
```

---

## Copyright Notice

**Only use Science2Go with papers you have the right to convert.**

This tool is intended for:
- Open Access papers published under Creative Commons or similar permissive licenses
- Your own manuscripts and pre-prints
- Papers where you have explicit permission from the copyright holder

Many academic papers are protected by publisher copyright. Converting a copyrighted paper to audio without permission may constitute copyright infringement, even for personal use. Always check the paper's license before processing it.

When generating an audio paper, Science2Go automatically includes an attribution note referencing the original paper, authors, DOI, and license information.

---

## Features

### PDF to Markdown Conversion

Three conversion modes with automatic PDF type detection:

| Mode | Speed | Use case |
|------|-------|----------|
| **Fast Extract** | ~1-5s | Native PDFs with selectable text |
| **Marker (no OCR)** | ~30s | Native PDFs needing layout detection |
| **Full Pipeline** | ~2-5min | Scanned PDFs requiring OCR |

When you browse a PDF, the app auto-detects whether it has native text and recommends the appropriate mode. Fast Extract uses `pdftext` for direct text extraction without any ML models.

### AI Text Processing

Gemini 2.5 Flash processes the extracted text through customizable YAML templates:

- **Review Papers** template: optimized for comprehensive review articles
- **Technical Papers** template: preserves technical detail with minimal reduction
- **Custom** template: basic cleanup with maximum content preservation

The AI processing:
- Removes citations, figure/table references, and front/back matter
- Preserves the paper title with proper formatting (period + "Abstract." label)
- Expands abbreviations and symbols for spoken delivery
- Converts section headers to narrator-friendly format
- Preserves all scientific content and accuracy
- Tracks Gemini API token usage and cost per operation

### SSML Conversion

The cleaned text is converted to SSML v1.1 markup for fine-grained speech control:

- Paragraph (`<p>`) and sentence (`<s>`) structure for natural pacing
- Section headers with `<prosody>` adjustments (rate, pitch)
- `<emphasis>` for key scientific terms
- `<say-as>` for dates, ordinals, and numbers
- `<break>` tags for natural pauses between sections
- Automatic SSML validation and repair before TTS
- Built-in SSML editor with save/load/clear

### Audio Generation

**Voice models:**

| Model | Voices | Quality | Pricing |
|-------|--------|---------|---------|
| **Chirp 3 HD** | 30 en-GB (16 male, 14 female) | Most natural, recommended | $30 / 1M chars |
| **Neural2** | 4 en-GB (1 male, 3 female) | Good quality, stricter SSML | $16 / 1M chars |

**Features:**
- Speaking rate control: 0.25x to 2.0x (default 0.95x for comprehension)
- Output formats: MP3, WAV, OGG, M4B (audiobook)
- Automatic SSML chunking at `</p>` boundaries (4800 byte TTS API limit)
- **Chapter markers**: auto-detected from section headers, embedded as ID3 CHAP/CTOC tags (MP3) or text chapters (M4B). Chapter names and timestamps are displayed in the generation summary — no manual setup needed.
- Audio normalization via pydub
- MP3/M4B metadata: title, author, description, genre tags via mutagen
- TTS character count and cost estimate displayed after generation

### GUI

Six-tab CustomTkinter interface:

1. **Paper Information** — PDF upload, metadata extraction (CrossRef API), paper info save/load/clear (JSON), audio description generation (editable)
2. **PDF to Markdown** — PDF path display, conversion mode selection, markdown preview
3. **Markdown Processing** — Template selection, AI processing with progress, cost display
4. **MD to SSML** — SSML conversion, monospace editor, save/load/clear, statistics
5. **Audio Config** — Voice model (Chirp 3 HD / Neural2), voice selector, rate/pitch/format, preview
6. **Speech Output** — Content source selection, generate with progress, chapter count, TTS cost, export

---

## Listening to Audio Papers

### iPhone / iPad

**Recommended: [BookPlayer](https://apps.apple.com/app/bookplayer/id1138219998)** (free, open source)

1. Export your `.mp3` or `.m4b` file to iCloud Drive (or any cloud storage)
2. On your iPhone, open the **Files** app
3. Navigate to the file and tap it
4. Choose **Open in BookPlayer** (or use the share sheet)

BookPlayer supports chapter navigation (M4B), playback speed control, and remembers your position.

Alternatively, you can use Apple's built-in **Books** app (supports M4B audiobooks) or import MP3 files into the **Music** app via iTunes/Finder sync.

### Android

**Recommended: [Voice Audiobook Player](https://play.google.com/store/apps/details?id=de.ph1b.audiobook)** (free, open source)

1. Transfer your `.mp3` or `.m4b` file to your phone (USB, Google Drive, or any cloud storage)
2. Place it in a folder on your device (e.g., `Audiobooks/`)
3. Open Voice and point it to that folder

Other good options:
- [Smart AudioBook Player](https://play.google.com/store/apps/details?id=ak.alizandro.smartaudiobookplayer) - feature-rich, supports chapters
- Any music player for MP3 files (e.g., VLC, Musicolet)

### Desktop

Any media player works: VLC, IINA (macOS), foobar2000 (Windows), or just double-click the file.

---

## Project Structure

```
science2go/
  main.py                          # Entry point
  run.sh                           # Launcher (uses correct Python)
  environment.yml                  # Conda environment
  requirements.txt                 # Pip dependencies
  setup.py                         # Automated setup script

  src/
    config/
      settings.py                  # API keys, paths, audio defaults
    gui/
      main_window.py               # Main 6-tab GUI (~2900 lines)
      platform_utils.py            # Cross-platform helpers
    processors/
      pdf_metadata.py              # PDF metadata extraction (PyPDF2 + CrossRef)
      pdf_converter.py             # PDF-to-Markdown (marker-pdf + pdftext)
      text_processor.py            # Gemini AI text/SSML cleanup + cost tracking
      audio_generator.py           # Google Cloud TTS + SSML chunking/validation + cost tracking
    templates/
      review_papers.yaml           # Review paper cleanup template
      technical_papers.yaml        # Technical paper cleanup template
      custom_template.yaml         # Minimal cleanup template
      ssml_converter.yaml          # SSML conversion template
      template_manager.py          # YAML template loader

  output/                          # Generated content (git-ignored)
    audio/                         # Audio paper files
    projects/                      # Saved text files
    temp/                          # Processing temp files
```

---

## Configuration

### Voice Selection

Two voice models are available, selectable in the Audio Config tab:

**Chirp 3 HD** (default, recommended) — 30 en-GB voices (16 male, 14 female). Most natural sounding. Default voice: `en-GB-Chirp3-HD-Charon`.

**Neural2** — 4 en-GB voices (1 male: D, 3 female: A, C, F). Stricter SSML requirements. Lower cost.

### Audio Defaults

| Setting | Default | Notes |
|---------|---------|-------|
| Speaking rate | 0.95x | Slightly slower for comprehension |
| Format | MP3 | Also supports WAV, OGG, M4B |
| Bitrate | 128k | Options: 64k-320k |
| Normalize | On | Volume normalization |

### Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `GEMINI_API_KEY` | Yes | Gemini AI text processing |
| `GOOGLE_API_KEY` | For TTS | Google Cloud TTS synthesis |
| `GOOGLE_APPLICATION_CREDENTIALS` | Alt. TTS | Service account JSON path |

If none of the Google TTS variables are set, the app checks for Application Default Credentials (`~/.config/gcloud/application_default_credentials.json` from `gcloud auth application-default login`).

---

## Dependencies

### Required

| Package | Version | Purpose |
|---------|---------|---------|
| customtkinter | >=5.2.0 | Modern GUI framework |
| google-generativeai | >=0.8.0 | Gemini AI text processing |
| PyYAML | >=6.0.1 | Template loading |
| python-dotenv | >=1.0.0 | Environment config |
| PyPDF2 | >=3.0.1 | PDF metadata extraction |

### For Audio Generation

| Package | Version | Purpose |
|---------|---------|---------|
| google-cloud-texttospeech | >=2.27.0 | TTS synthesis (Chirp 3 HD + Neural2) |
| pydub | >=0.25.1 | Audio concatenation & normalization |
| mutagen | >=1.47.0 | MP3/M4B metadata & chapter tagging |
| ffmpeg | (system) | Audio codec support for pydub |

### Optional (PDF-to-Markdown)

| Package | Version | Purpose |
|---------|---------|---------|
| marker-pdf | >=1.10.0 | Full PDF conversion with layout detection |
| pdftext | >=0.6.0 | Fast native text extraction |

marker-pdf pulls in PyTorch (~2GB). If you only work with native PDFs (not scanned), `pdftext` alone is sufficient.

---

## License

**Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International**

- Attribution required
- Non-commercial use only
- Derivatives must use the same license

Full license: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)

---

## Acknowledgments

- [Google Cloud Text-to-Speech](https://cloud.google.com/text-to-speech) (Chirp 3 HD & Neural2 voices)
- [Google Generative AI](https://ai.google.dev/) (Gemini 2.5 Flash)
- [marker-pdf](https://github.com/VikParuchuri/marker) (PDF-to-Markdown conversion)
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) (Modern GUI)
