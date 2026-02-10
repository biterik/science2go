# Science2Go

**Convert Academic Papers into Podcast-Style Audio**

Science2Go transforms scientific PDF papers into high-quality audio files using AI text processing and Google Cloud Text-to-Speech. The pipeline extracts text from PDFs, cleans it for spoken delivery with Gemini AI, and synthesizes natural-sounding speech with Chirp 3 HD voices.

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

---

## Pipeline Overview

```
PDF  -->  Markdown  -->  AI Cleanup  -->  TTS  -->  MP3 / M4B
          (marker-pdf     (Gemini 2.5     (Google Cloud TTS
           or pdftext)      Flash)          Chirp 3 HD)
```

| Step | Component | Status |
|------|-----------|--------|
| 1 | PDF loading & metadata extraction | Done |
| 2 | PDF to Markdown conversion | Done |
| 3 | AI text cleanup for TTS | Done |
| 4 | Save/Load processed text | Done |
| 5 | Text-to-Speech audio generation | Done |
| 6 | Audio post-processing & metadata | Done |
| GUI | CustomTkinter interface (4 tabs) | Done |

---

## Quick Start

### 1. Clone and set up the environment

```bash
git clone https://github.com/biterik/science2go.git
cd science2go

# Create conda environment (recommended)
conda env create -f environment.yml
conda activate science2go

# Optional: enable PDF-to-Markdown (pulls in PyTorch ~2GB)
pip install marker-pdf pdftext
```

### 2. Configure API keys

```bash
# Add to ~/.zshrc or ~/.bashrc:
export GEMINI_API_KEY="your_gemini_api_key"
export GOOGLE_API_KEY="your_google_api_key"

source ~/.zshrc
```

**Get your keys:**
- Gemini API Key: [Google AI Studio](https://aistudio.google.com/app/apikey)
- Google Cloud TTS: [Console](https://console.cloud.google.com/apis/credentials) or run `gcloud auth application-default login`

### 3. Run

```bash
./run.sh
# or: python main.py
```

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
- Expands abbreviations and symbols for spoken delivery
- Converts section headers to narrator-friendly format
- Inserts `[pause short]` and `[pause long]` markup for Chirp 3 HD voice pacing
- Preserves all scientific content and accuracy

### Audio Generation

- **Chirp 3 HD voices**: 30 en-GB voices (16 male, 14 female), the most natural-sounding Google TTS voices
- **Speaking rate control**: 0.25x to 2.0x (default 0.95x for comprehension)
- **Output formats**: MP3, WAV, OGG, M4B (audiobook with chapters)
- **Automatic text chunking**: splits text at sentence boundaries to fit the 5,000 byte API limit
- **Chapter markers**: auto-detected from section headers, embedded as ID3 CHAP frames
- **Audio normalization**: optional volume normalization via pydub
- **MP3/M4B metadata**: title, author, description, genre tags via mutagen

### GUI

Four-tab CustomTkinter interface:

1. **Paper Setup** - PDF browse, metadata extraction (CrossRef API), PDF-to-Markdown conversion
2. **Markdown Processing** - AI processing with template selection, save/load for source and processed text
3. **Audio Config** - Voice selection, speaking rate, output format, bitrate, voice preview
4. **Output Generation** - Generate button with progress tracking, results display, file open/export

---

## Project Structure

```
science2go/
  main.py                          # Entry point
  run.sh                           # Launcher (uses correct Python)
  environment.yml                  # Conda environment
  requirements.txt                 # Pip dependencies
  setup.py                         # Automated setup script
  TODO.md                          # Detailed task tracking

  src/
    config/
      settings.py                  # API keys, paths, audio defaults
    gui/
      main_window.py               # Main 4-tab GUI
      platform_utils.py            # Cross-platform helpers
    processors/
      pdf_metadata.py              # PDF metadata extraction (PyPDF2 + CrossRef)
      pdf_converter.py             # PDF-to-Markdown (marker-pdf + pdftext)
      text_processor.py            # Gemini AI text cleanup
      audio_generator.py           # Google Cloud TTS + pydub + mutagen
    templates/
      review_papers.yaml           # Review paper cleanup template
      technical_papers.yaml        # Technical paper cleanup template
      custom_template.yaml         # Minimal cleanup template
      template_manager.py          # YAML template loader

  output/                          # Generated content (git-ignored)
    audio/                         # Podcast MP3/M4B files
    projects/                      # Saved text files
    temp/                          # Processing temp files
```

---

## Configuration

### Voice Selection

The default voice is `en-GB-Chirp3-HD-Charon` (male, British English). All 30 Chirp 3 HD en-GB voices are available in the Audio Config tab.

Note: Chirp 3 HD does **not** support pitch control or SSML prosody tags. Use `speaking_rate` (0.25-2.0) for pace control and inline `[pause short]` / `[pause long]` tags for pauses.

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

If neither `GOOGLE_API_KEY` nor `GOOGLE_APPLICATION_CREDENTIALS` is set, the app checks for Application Default Credentials (`~/.config/gcloud/application_default_credentials.json` from `gcloud auth application-default login`).

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
| google-cloud-texttospeech | >=2.27.0 | TTS synthesis |
| pydub | >=0.25.1 | Audio concatenation & normalization |
| mutagen | >=1.47.0 | MP3/M4B metadata tagging |
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

- [Google Cloud Text-to-Speech](https://cloud.google.com/text-to-speech) (Chirp 3 HD voices)
- [Google Generative AI](https://ai.google.dev/) (Gemini 2.5 Flash)
- [marker-pdf](https://github.com/VikParuchuri/marker) (PDF-to-Markdown conversion)
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) (Modern GUI)
