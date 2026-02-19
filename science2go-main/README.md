# Science2Go 🎙️

**Transform Academic Papers into Professional Audio**

Science2Go converts scientific PDFs into high-quality audio papers using AI-powered text processing and Google Cloud Text-to-Speech. The full pipeline runs through a 6-tab GUI: PDF → Markdown → AI cleanup → SSML → TTS → MP3.

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Cross-Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey.svg)]()

---

## 🚀 Quick Start

### 1. Clone and Setup
```bash
git clone https://github.com/biterik/science2go.git
cd science2go/science2go-main

# Conda (recommended)
conda env create -f environment.yml
conda activate science2go

# OR pip
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
# Add to ~/.zshrc or ~/.bashrc
export GEMINI_API_KEY="your_gemini_api_key_here"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"

source ~/.zshrc  # Reload shell
```

- **Gemini API Key**: [Google AI Studio](https://aistudio.google.com/app/apikey)
- **Google Cloud TTS**: [Console Credentials](https://console.cloud.google.com/apis/credentials)

### 3. Run
```bash
python main.py
```

---

## 🎯 Pipeline

The application processes papers through six steps, each with its own GUI tab:

| Tab | Step | Description |
|-----|------|-------------|
| 1. Paper Information | PDF upload + metadata | Extract title, authors, abstract, DOI via CrossRef API. Save/load paper info as JSON. Generate audio paper description. |
| 2. PDF to Markdown | PDF → MD conversion | Uses marker-pdf for high-quality conversion. Supports Fast Extract, Marker (no OCR), and Full Pipeline modes. |
| 3. Markdown Processing | AI text cleanup | Gemini 2.5 Flash cleans the text using YAML templates (Review Papers, Technical Papers, Custom). Removes citations, expands abbreviations, optimizes for speech. |
| 4. MD to SSML | SSML markup | Converts cleaned text to SSML v1.1 with paragraph/sentence structure, emphasis, prosody, and natural pacing. Built-in SSML editor with save/load. |
| 5. Audio Config | Voice & format setup | Select voice model (Chirp 3 HD or Neural2), choose from 30+ voices, adjust rate/pitch, pick output format. |
| 6. Speech Output | TTS generation | Generate audio with progress tracking, TTS cost estimate, and export to MP3/WAV/OGG/M4B. |

---

## 🎛️ Features

### 🎙️ Voice Models

**Chirp 3 HD** — Most natural-sounding, recommended for audio papers
- 16 male voices (e.g., Charon, Fenrir, Puck, Schedar)
- 14 female voices (e.g., Achernar, Despina, Leda, Zephyr)
- Locale: en-GB (British English)
- Pricing: $30 per 1M characters

**Neural2** — Stricter SSML requirements, lighter weight
- 1 male voice (en-GB-Neural2-D)
- 3 female voices (en-GB-Neural2-A, C, F)
- Locale: en-GB (British English)
- Pricing: $16 per 1M characters

### 🤖 AI Processing
- **Google Gemini 2.5 Flash** (1M context, 65K output tokens)
- Template-based prompts (YAML) for different paper types
- Automatic chunking for large papers with overlap and intelligent merging
- Blocked-response handling (RECITATION/SAFETY) with partial text salvage
- API cost tracking displayed after each operation

### 📝 SSML Pipeline
- Paragraph (`<p>`) and sentence (`<s>`) structure
- Section headers with prosody adjustments
- `<emphasis>` for key terms, `<say-as>` for dates/numbers
- `<break>` tags for natural pacing
- Automatic SSML validation and repair
- Chunking at `</p>` boundaries for TTS byte limits (4800 bytes/chunk)

### 🖥️ GUI
- CustomTkinter with 6 tabs (one per pipeline step)
- Scrollable content areas, real-time progress tracking
- Paper info save/load/clear (JSON format)
- Editable text at every stage
- Cost estimates for Gemini tokens and TTS characters

### 📊 Cost Tracking
- **Gemini**: Input/output token counts with per-operation cost ($0.30/1M input, $2.50/1M output)
- **TTS**: Billable character count with per-operation cost (model-dependent)
- Displayed in status bar and summary dialogs

---

## 🏗️ Project Structure

```
science2go-main/
├── main.py                              # Application entry point
├── environment.yml                      # Conda environment
├── requirements.txt                     # Pip dependencies
├── setup.py                             # Cross-platform setup
├── README.md
│
├── src/
│   ├── config/settings.py               # App configuration
│   ├── gui/
│   │   ├── main_window.py               # 6-tab GUI (~2900 lines)
│   │   └── platform_utils.py            # Platform-specific styling
│   ├── processors/
│   │   ├── pdf_converter.py             # marker-pdf PDF→MD conversion
│   │   ├── pdf_metadata.py              # PDF metadata extraction (CrossRef API)
│   │   ├── text_processor.py            # Gemini AI text/SSML processing + cost tracking
│   │   └── audio_generator.py           # Google Cloud TTS + SSML chunking/validation
│   └── templates/
│       ├── template_manager.py          # YAML template loading
│       ├── review_papers.yaml           # Review paper cleanup template
│       ├── technical_papers.yaml        # Technical paper template
│       ├── custom_template.yaml         # Customizable template
│       └── ssml_converter.yaml          # SSML conversion template
│
└── output/                              # Generated content (git-ignored)
    ├── audio/                           # Audio files
    └── logs/                            # Processing logs
```

---

## ⚙️ Configuration

### Voice Settings
```
Model:          Chirp 3 HD (default) or Neural2
Default voice:  en-GB-Chirp3-HD-Charon (male)
Speaking rate:  0.95 (slightly slower for comprehension)
Pitch:          0.0 (neutral)
```

### Audio Output
- **Formats**: MP3, WAV, OGG, M4B
- **Bitrate options**: 64k – 320k
- **Processing**: Normalized, mono encoding
- **Metadata**: Title, author, chapter markers (MP3/M4B)

### Template System
Templates are YAML files with `system_prompt` and `user_prompt` fields. The `{content}` placeholder is replaced with the text chunk to process. The SSML converter template also uses `{context}` for cross-chunk continuity.

---

## 🔒 Security & Privacy

- ✅ No API keys in repository — uses environment variables
- ✅ User data git-ignored — output files never committed
- ✅ Content stays local (only transmitted to Google AI services)
- ✅ Open source — transparent and auditable

---

## 🛠️ Dependencies

- **Python 3.11+**
- **google-generativeai** — Gemini AI API
- **google-cloud-texttospeech** — Google Cloud TTS
- **marker-pdf** — PDF to Markdown conversion (requires PyTorch)
- **customtkinter** — Modern GUI framework
- **pydub** + **ffmpeg** — Audio processing
- **mutagen** — MP3/M4B metadata tagging

---

## 📜 License

This project is licensed under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License**.

- ✅ **Attribution** — Credit the original author
- ❌ **NonCommercial** — No commercial use without permission
- ✅ **ShareAlike** — Derivatives must use same license

**Full License**: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)

For commercial licensing, please contact the author.

---

## 🤝 Support

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/biterik/science2go/issues)
- 💡 **Feature Requests**: [GitHub Discussions](https://github.com/biterik/science2go/discussions)

---

*Created with ❤️ for the research community*
