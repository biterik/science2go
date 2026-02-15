# Science2Go 🎙️

**Transform Academic Papers into Engaging Podcasts**

Science2Go is a comprehensive Python application that converts academic papers (PDF metadata + Markdown content) into high-quality podcast episodes using AI-powered text processing and professional text-to-speech technology.

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Cross-Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey.svg)]()

---

## 🚀 Quick Start

### 1. Clone and Setup
```bash
git clone https://github.com/yourusername/science2go.git
cd science2go

# Automated setup (handles everything)
python setup.py

# OR manual setup
conda env create -f environment.yml
conda activate science2go
```

### 2. Configure API Keys

**Option A: Shell Environment Variables (Recommended - Secure)**
```bash
# Add to ~/.zshrc or ~/.bashrc
export GEMINI_API_KEY="your_gemini_api_key_here"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
# OR alternatively:
export GOOGLE_API_KEY="your_google_api_key_here"

source ~/.zshrc  # Reload shell
```

**Option B: Local .env File (Alternative)**
```bash
cp .env.template .env
# Edit .env with your API keys (this file is git-ignored)
```

### 3. Get Your API Keys

- **Gemini API Key**: [Google AI Studio](https://aistudio.google.com/app/apikey)
- **Google Cloud TTS**: [Console Credentials](https://console.cloud.google.com/apis/credentials)

### 4. Run Science2Go
```bash
python main.py
```

---

## 🎯 How It Works

### Input Process
1. **📄 PDF Upload**: Extract paper metadata (title, authors, abstract)
2. **📝 Markdown File**: Load your prepared content (.md/.txt file)
3. **🤖 AI Processing**: Gemini optimizes text for audio consumption
4. **✏️ Review & Edit**: Fine-tune the processed content
5. **🎙️ Generate Podcast**: Custom voice TTS with chapter markers

### Smart Text Processing
- ❌ Removes figure/table references  
- 🔤 Converts equations to spoken form
- 📚 Eliminates citation clutter
- ✂️ Optimizes for audio flow
- ✅ Maintains academic accuracy

---

## 🎛️ Features

### 🎙️ **Professional Audio Quality**
- Custom Google TTS voices (e.g., `en-GB-Chirp3-HD-Algenib`)
- Natural pacing with automatic pauses
- Podcast-optimized encoding (44.1kHz, 128kbps MP3)
- Chapter markers and metadata embedding

### 🤖 **AI-Powered Processing**  
- Google Gemini text optimization
- Template-based prompts (Review Papers, Technical Papers, Custom)
- Editable processed content
- TTS-optimized output

### 🖥️ **Cross-Platform GUI**
- Native look and feel (macOS/Windows/Linux)
- Intuitive tabbed interface
- Real-time progress tracking
- Built-in audio player

### 📊 **Template System**
- YAML-based prompt templates
- Specialized processing for different paper types
- Custom template creation
- Reusable configurations

---

## 🏗️ Project Structure

```
science2go/
├── main.py                     # Application entry point
├── environment.yml             # Conda environment
├── requirements.txt            # Pip alternative  
├── setup.py                   # Cross-platform setup
├── .env.template              # API key template (safe for GitHub)
│
├── src/
│   ├── config/settings.py     # Configuration management
│   ├── gui/                   # Cross-platform interface
│   ├── processors/            # PDF, AI, and audio processing
│   ├── templates/             # YAML prompt templates
│   └── utils/                 # Helper utilities
│
├── output/                    # Generated content (git-ignored)
│   ├── audio/                # Podcast files
│   ├── temp/                 # Processing temp files
│   └── projects/             # Saved configurations
│
└── tests/                    # Unit tests
```

---

## ⚙️ Configuration

Science2Go automatically detects API keys from:
1. **Shell environment** (secure, recommended)
2. **Local .env file** (development)  
3. **System environment variables**

### Voice Configuration
```python
# Use any Google TTS voice name
voice_name = "en-GB-Chirp3-HD-Algenib"
speaking_rate = 0.95  # Slightly slower for comprehension
pitch = 0.0           # Neutral pitch
```

### Audio Output Settings
- **Format**: MP3 with podcast optimization
- **Quality**: 44.1kHz, 128kbps, normalized to -23 LUFS
- **Features**: Chapter markers, metadata, mono encoding

---

## 🔒 Security & Privacy

### GitHub Safety
- ✅ **No API keys in repository** - uses environment variables
- ✅ **User data git-ignored** - output files never committed  
- ✅ **Safe configuration** - template files only
- ✅ **Open source** - transparent and auditable

### Local Security
- API keys stored in shell environment (not in files)
- Temporary files automatically cleaned up
- User content stays local (never transmitted except to AI services)

---

## 🛠️ Development

### Requirements
- Python 3.11+
- Google Cloud TTS API access
- Google Generative AI (Gemini) API access

### Installation Methods
```bash
# Method 1: Conda (recommended)
conda env create -f environment.yml

# Method 2: Pip
pip install -r requirements.txt

# Method 3: Automated
python setup.py
```

### Contributing
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📜 License

This project is licensed under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License**.

- ✅ **Attribution** - Credit the original author
- ❌ **NonCommercial** - No commercial use without permission
- ✅ **ShareAlike** - Derivatives must use same license

**Full License**: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)

For commercial licensing, please contact the author.

---

## 🎯 Roadmap

### v1.0 - Core Features (Current)
- [x] Cross-platform GUI
- [x] PDF metadata extraction
- [x] Markdown processing
- [x] Gemini AI integration
- [x] Custom voice TTS
- [x] Podcast optimization

### v1.1 - Enhancements
- [ ] Batch processing
- [ ] Advanced audio effects
- [ ] RSS feed generation
- [ ] Cloud storage integration

### v2.0 - Advanced Features
- [ ] Multi-language support
- [ ] Custom voice cloning
- [ ] Automated chapter generation
- [ ] Plugin system

---

## 🤝 Support

- 📖 **Documentation**: See inline code comments and docstrings
- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/yourusername/science2go/issues)
- 💡 **Feature Requests**: [GitHub Discussions](https://github.com/yourusername/science2go/discussions)
- 📧 **Contact**: [Your contact information]

---

## 🙏 Acknowledgments

- Google Cloud Text-to-Speech for professional voice synthesis
- Google Generative AI (Gemini) for intelligent text processing
- The academic community for inspiration and feedback

---

*Created with ❤️ for the research community*