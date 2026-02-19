"""
Science2Go Main Window - CustomTkinter GUI
Modern cross-platform interface with PDF-to-Markdown conversion, AI processing,
SSML conversion, and audio generation.

Tab layout (6 tabs):
  1. Paper Information    — metadata form + audio description
  2. PDF to Markdown      — PDF upload, conversion, markdown preview
  3. Markdown Processing   — AI processing with templates
  4. MD to SSML           — SSML conversion, editing, save/load
  5. Audio Config         — voice, rate, pitch, format, preview
  6. Speech Output        — generate audio, progress, results
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import os
import re
import platform
import sys
import threading
import json
from pathlib import Path
from datetime import datetime

# Import configuration and utilities
current_dir = Path(__file__).parent
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.config.settings import config
from src.gui.platform_utils import PlatformStyle

# Import processors with error handling
try:
    from src.processors.pdf_metadata import PDFMetadataExtractor
    PDF_METADATA_AVAILABLE = True
except ImportError as e:
    print(f"Warning: PDF metadata extraction not available: {e}")
    PDF_METADATA_AVAILABLE = False

try:
    from src.processors.text_processor import process_markdown_content
    TEXT_PROCESSOR_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Text processor not available: {e}")
    TEXT_PROCESSOR_AVAILABLE = False

# Import PDF-to-Markdown converter (optional -- requires marker-pdf)
try:
    from src.processors.pdf_converter import (
        pdf_converter, MARKER_AVAILABLE, detect_pdf_type, fast_extract_text,
        CONVERSION_MODES, MODE_FAST_EXTRACT, MODE_MARKER_NO_OCR, MODE_FULL_PIPELINE,
    )
except ImportError:
    MARKER_AVAILABLE = False
    pdf_converter = None
    detect_pdf_type = None
    fast_extract_text = None
    CONVERSION_MODES = []
    MODE_FAST_EXTRACT = "Fast Extract"
    MODE_MARKER_NO_OCR = "Marker (no OCR)"
    MODE_FULL_PIPELINE = "Full Pipeline"

# Import Audio generator (optional -- requires google-cloud-texttospeech)
try:
    from src.processors.audio_generator import (
        audio_generator, TTS_AVAILABLE,
        AUDIO_FORMATS, BITRATE_OPTIONS,
        CHIRP3_HD_MALE_VOICES, CHIRP3_HD_FEMALE_VOICES,
        NEURAL2_MALE_VOICES, NEURAL2_FEMALE_VOICES,
        VOICE_MODELS, VOICE_MODEL_CHIRP3_HD, VOICE_MODEL_NEURAL2,
        voice_display_name, voice_full_name,
        is_ssml_content,
        DEFAULT_VOICE, DEFAULT_SPEAKING_RATE,
    )
except ImportError:
    TTS_AVAILABLE = False
    audio_generator = None
    AUDIO_FORMATS = ["MP3", "WAV", "OGG", "M4B"]
    BITRATE_OPTIONS = ["64k", "96k", "128k", "192k", "256k", "320k"]
    CHIRP3_HD_MALE_VOICES = []
    CHIRP3_HD_FEMALE_VOICES = []
    NEURAL2_MALE_VOICES = []
    NEURAL2_FEMALE_VOICES = []
    VOICE_MODELS = ["Chirp 3 HD", "Neural2"]
    VOICE_MODEL_CHIRP3_HD = "Chirp 3 HD"
    VOICE_MODEL_NEURAL2 = "Neural2"
    voice_display_name = lambda x: x
    voice_full_name = lambda x, y="en-GB", z="Chirp 3 HD": x
    is_ssml_content = lambda x: x.strip().startswith('<speak>')
    DEFAULT_VOICE = "en-GB-Chirp3-HD-Charon"
    DEFAULT_SPEAKING_RATE = 0.95


class Science2GoApp:
    """Main Science2Go application with modern CustomTkinter GUI"""

    def __init__(self, root):
        self.root = root
        self.platform_style = PlatformStyle()
        self.setup_window()
        self.setup_menu()
        self.setup_main_interface()
        self.setup_status_bar()

        # Application state
        self.current_project = None
        self.pdf_metadata = {}
        self.markdown_content = ""
        self.processed_content = ""
        self.converted_markdown = ""  # Stores PDF-to-Markdown result
        self.current_processed_file = None  # Track loaded processed file
        self.current_source_file = None  # Track loaded/saved source markdown file
        self.current_ssml_file = None  # Track loaded/saved SSML file

        # PDF extractor
        if PDF_METADATA_AVAILABLE:
            self.pdf_extractor = PDFMetadataExtractor()
        else:
            self.pdf_extractor = None

        # Ensure output directories exist
        config.ensure_directories()

        print("Science2Go GUI initialized successfully")

    def setup_window(self):
        """Configure main window"""
        self.root.title("Science2Go - Turn Academic Papers into Audio Papers")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 600)

        # Center window on screen
        self.center_window()

        # Apply platform-specific tweaks
        if hasattr(self.platform_style, 'apply_to_window'):
            self.platform_style.apply_to_window(self.root)

        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def center_window(self):
        """Center the window on the screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def setup_menu(self):
        """Create the application menu (uses standard tk.Menu -- no CTk equivalent)"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        accel_key = "Cmd" if platform.system() == "Darwin" else "Ctrl"
        file_menu.add_command(label="New Project", command=self.new_project,
                              accelerator=f"{accel_key}+N")
        file_menu.add_command(label="Open Project", command=self.open_project,
                              accelerator=f"{accel_key}+O")
        file_menu.add_command(label="Save Project", command=self.save_project,
                              accelerator=f"{accel_key}+S")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)

        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Preferences", command=self.show_preferences)

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Test Configuration", command=self.test_configuration)
        tools_menu.add_command(label="Clear Cache", command=self.clear_cache)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="Documentation", command=self.open_documentation)

    def setup_main_interface(self):
        """Create the main tabbed interface with 6 pipeline tabs"""
        # Main container
        main_frame = ctk.CTkFrame(self.root)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Configure grid weights
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        # Create tabview
        self.tabview = ctk.CTkTabview(main_frame)
        self.tabview.grid(row=0, column=0, sticky="nsew")

        # Add 6 tabs (one per pipeline step)
        self.tabview.add("Paper Information")
        self.tabview.add("PDF to Markdown")
        self.tabview.add("Markdown Processing")
        self.tabview.add("MD to SSML")
        self.tabview.add("Audio Config")
        self.tabview.add("Speech Output")

        # Build each tab's content
        self.create_paper_info_tab(self.tabview.tab("Paper Information"))
        self.create_pdf_to_markdown_tab(self.tabview.tab("PDF to Markdown"))
        self.create_markdown_processing_tab(self.tabview.tab("Markdown Processing"))
        self.create_md_to_ssml_tab(self.tabview.tab("MD to SSML"))
        self.create_audio_config_tab(self.tabview.tab("Audio Config"))
        self.create_speech_output_tab(self.tabview.tab("Speech Output"))

    # ──────────────────────────────────────────────
    #  Tab 1: Paper Information
    # ──────────────────────────────────────────────

    def create_paper_info_tab(self, parent_frame):
        """Create the Paper Information tab with metadata form and description"""
        container = ctk.CTkScrollableFrame(parent_frame)
        container.pack(fill="both", expand=True, padx=5, pady=5)

        # Title
        ctk.CTkLabel(
            container, text="Paper Information",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", padx=15, pady=(10, 15))

        # ── PDF Upload Section ──
        upload_section = ctk.CTkFrame(container)
        upload_section.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkLabel(
            upload_section, text="PDF Upload",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            upload_section,
            text="Select your academic paper (PDF) to extract metadata:"
        ).pack(anchor="w", padx=10, pady=(0, 5))

        pdf_button_frame = ctk.CTkFrame(upload_section, fg_color="transparent")
        pdf_button_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.pdf_path_var = tk.StringVar()
        pdf_entry = ctk.CTkEntry(pdf_button_frame, textvariable=self.pdf_path_var,
                                 state="readonly")
        pdf_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(
            pdf_button_frame, text="Browse PDF", width=120,
            command=self.browse_pdf
        ).pack(side="right", padx=(0, 5))

        self.analyze_btn = ctk.CTkButton(
            pdf_button_frame, text="Analyze PDF", width=120,
            command=self.analyze_pdf, state="disabled"
        )
        self.analyze_btn.pack(side="right")

        # ── Paper Information Section (form) ──
        info_section = ctk.CTkFrame(container)
        info_section.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkLabel(
            info_section, text="Paper Metadata",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        form_frame = ctk.CTkFrame(info_section, fg_color="transparent")
        form_frame.pack(fill="x", padx=10, pady=(0, 10))
        form_frame.grid_columnconfigure(1, weight=1)

        # Title field
        ctk.CTkLabel(form_frame, text="Title:").grid(
            row=0, column=0, sticky="nw", padx=(0, 10), pady=5)
        self.title_text = ctk.CTkTextbox(form_frame, height=70, wrap="word")
        self.title_text.grid(row=0, column=1, sticky="ew", pady=5)

        # Authors field
        ctk.CTkLabel(form_frame, text="Authors:").grid(
            row=1, column=0, sticky="nw", padx=(0, 10), pady=5)
        self.authors_var = tk.StringVar()
        ctk.CTkEntry(form_frame, textvariable=self.authors_var).grid(
            row=1, column=1, sticky="ew", pady=5)

        # Journal field
        ctk.CTkLabel(form_frame, text="Journal:").grid(
            row=2, column=0, sticky="nw", padx=(0, 10), pady=5)
        self.journal_var = tk.StringVar()
        ctk.CTkEntry(form_frame, textvariable=self.journal_var).grid(
            row=2, column=1, sticky="ew", pady=5)

        # Year field
        ctk.CTkLabel(form_frame, text="Year:").grid(
            row=3, column=0, sticky="nw", padx=(0, 10), pady=5)
        self.year_var = tk.StringVar()
        ctk.CTkEntry(form_frame, textvariable=self.year_var, width=150).grid(
            row=3, column=1, sticky="w", pady=5)

        # DOI field
        ctk.CTkLabel(form_frame, text="DOI:").grid(
            row=4, column=0, sticky="nw", padx=(0, 10), pady=5)
        self.doi_var = tk.StringVar()
        ctk.CTkEntry(form_frame, textvariable=self.doi_var).grid(
            row=4, column=1, sticky="ew", pady=5)

        # Abstract field
        ctk.CTkLabel(form_frame, text="Abstract:").grid(
            row=5, column=0, sticky="nw", padx=(0, 10), pady=5)
        self.abstract_text = ctk.CTkTextbox(form_frame, height=120, wrap="word")
        self.abstract_text.grid(row=5, column=1, sticky="ew", pady=5)

        # ── Save / Load / Clear Paper Info Buttons ──
        info_btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        info_btn_frame.pack(fill="x", padx=15, pady=(5, 10))

        ctk.CTkButton(
            info_btn_frame, text="Save Paper Info", width=120,
            command=self.save_paper_info,
        ).pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            info_btn_frame, text="Load Paper Info", width=120,
            command=self.load_paper_info,
        ).pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            info_btn_frame, text="Clear", width=80,
            command=self.clear_paper_info,
        ).pack(side="left")

        # ── Generate Description Button ──
        description_frame = ctk.CTkFrame(container, fg_color="transparent")
        description_frame.pack(fill="x", padx=15, pady=(0, 10))

        ctk.CTkButton(
            description_frame, text="Generate Audio Paper Description",
            command=self.generate_description
        ).pack(side="right")

        # ── Description Preview ──
        desc_section = ctk.CTkFrame(container)
        desc_section.pack(fill="x", padx=15)

        ctk.CTkLabel(
            desc_section, text="Generated Audio Paper Description",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self.description_text = ctk.CTkTextbox(desc_section, height=120,
                                               wrap="word")
        self.description_text.pack(fill="x", padx=10, pady=(0, 10))

    # ──────────────────────────────────────────────
    #  Tab 2: PDF to Markdown
    # ──────────────────────────────────────────────

    def create_pdf_to_markdown_tab(self, parent_frame):
        """Create the PDF to Markdown tab with upload, conversion, and markdown preview"""
        container = ctk.CTkScrollableFrame(parent_frame)
        container.pack(fill="both", expand=True, padx=5, pady=5)

        # Title
        ctk.CTkLabel(
            container, text="PDF to Markdown Conversion",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", padx=15, pady=(10, 15))

        # ── Selected PDF (from Tab 1) ──
        pdf_ref_section = ctk.CTkFrame(container)
        pdf_ref_section.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkLabel(
            pdf_ref_section, text="Selected PDF",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        pdf_ref_frame = ctk.CTkFrame(pdf_ref_section, fg_color="transparent")
        pdf_ref_frame.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkEntry(
            pdf_ref_frame, textvariable=self.pdf_path_var,
            state="readonly",
        ).pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkLabel(
            pdf_ref_frame,
            text="(Select PDF in the Paper Information tab)",
            font=ctk.CTkFont(size=10, slant="italic"), text_color="gray",
        ).pack(side="right")

        # ── PDF to Markdown Conversion Section ──
        convert_section = ctk.CTkFrame(container)
        convert_section.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkLabel(
            convert_section, text="Convert to Markdown",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        if MARKER_AVAILABLE:
            convert_btn_frame = ctk.CTkFrame(convert_section, fg_color="transparent")
            convert_btn_frame.pack(fill="x", padx=10, pady=(0, 5))

            self.convert_btn = ctk.CTkButton(
                convert_btn_frame, text="Convert PDF to Markdown", width=200,
                command=self.convert_pdf_to_markdown, state="disabled"
            )
            self.convert_btn.pack(side="left")

            self.convert_status_label = ctk.CTkLabel(
                convert_btn_frame, text="",
                font=ctk.CTkFont(size=11, slant="italic")
            )
            self.convert_status_label.pack(side="left", padx=(15, 0))

            # Conversion mode selector
            mode_frame = ctk.CTkFrame(convert_section, fg_color="transparent")
            mode_frame.pack(fill="x", padx=10, pady=(5, 0))

            ctk.CTkLabel(
                mode_frame, text="Mode:",
                font=ctk.CTkFont(size=12),
            ).pack(side="left", padx=(0, 5))

            self.conversion_mode_var = tk.StringVar(value=MODE_FAST_EXTRACT)
            self.conversion_mode_combo = ctk.CTkComboBox(
                mode_frame,
                variable=self.conversion_mode_var,
                values=CONVERSION_MODES,
                state="readonly", width=180,
                font=ctk.CTkFont(size=12),
            )
            self.conversion_mode_combo.pack(side="left")

            self.mode_detection_label = ctk.CTkLabel(
                mode_frame, text="",
                font=ctk.CTkFont(size=11, slant="italic"),
                text_color="gray",
            )
            self.mode_detection_label.pack(side="left", padx=(15, 0))

            self.convert_progress = ctk.CTkProgressBar(convert_section)
            self.convert_progress.pack(fill="x", padx=10, pady=(0, 10))
            self.convert_progress.set(0)
        else:
            self.convert_btn = None
            ctk.CTkLabel(
                convert_section,
                text="PDF-to-Markdown conversion unavailable. "
                     "Install with: pip install marker-pdf",
                font=ctk.CTkFont(size=11, slant="italic"),
                text_color="gray"
            ).pack(padx=10, pady=10)

        # ── Markdown File Operations ──
        md_file_section = ctk.CTkFrame(container)
        md_file_section.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkLabel(
            md_file_section, text="Markdown File",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            md_file_section,
            text="Load an existing markdown file or save the converted result:"
        ).pack(anchor="w", padx=10, pady=(0, 5))

        md_btn_frame = ctk.CTkFrame(md_file_section, fg_color="transparent")
        md_btn_frame.pack(fill="x", padx=10, pady=(0, 5))

        self.markdown_path_var = tk.StringVar()
        ctk.CTkEntry(
            md_btn_frame, textvariable=self.markdown_path_var,
            state="readonly"
        ).pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(
            md_btn_frame, text="Browse", width=100,
            command=self.browse_markdown_file
        ).pack(side="right", padx=(5, 0))

        md_action_frame = ctk.CTkFrame(md_file_section, fg_color="transparent")
        md_action_frame.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkButton(
            md_action_frame, text="Save Markdown", width=120,
            command=self.save_source_markdown
        ).pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            md_action_frame, text="Load Markdown", width=120,
            command=self.load_source_markdown
        ).pack(side="left")

        # ── Markdown Preview ──
        preview_section = ctk.CTkFrame(container)
        preview_section.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkLabel(
            preview_section, text="Markdown Preview",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self.md_preview_text = ctk.CTkTextbox(
            preview_section,
            font=ctk.CTkFont(family="Consolas", size=11),
            state="disabled", wrap="word", height=300,
        )
        self.md_preview_text.pack(fill="both", expand=True, padx=10, pady=(0, 5))

        self.md_preview_stats_var = tk.StringVar(value="No markdown loaded")
        ctk.CTkLabel(
            preview_section, textvariable=self.md_preview_stats_var,
            font=ctk.CTkFont(size=10, slant="italic"),
        ).pack(anchor="w", padx=10, pady=(0, 10))

    # ──────────────────────────────────────────────
    #  Tab 3: Markdown Processing
    # ──────────────────────────────────────────────

    def create_markdown_processing_tab(self, parent_frame):
        """Create the Markdown Processing tab with AI integration and Save/Load"""
        container = ctk.CTkFrame(parent_frame, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=5, pady=5)

        # Title and Action buttons at the TOP
        title_and_buttons_frame = ctk.CTkFrame(container, fg_color="transparent")
        title_and_buttons_frame.pack(fill="x", padx=15, pady=(10, 10))

        # Title on the left
        ctk.CTkLabel(
            title_and_buttons_frame, text="AI Content Processing",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(side="left", anchor="w")

        # Buttons on the right
        button_frame = ctk.CTkFrame(title_and_buttons_frame, fg_color="transparent")
        button_frame.pack(side="right")

        # File operations
        ctk.CTkButton(
            button_frame, text="Load Processed", width=120,
            command=self.load_processed_text
        ).pack(side="right", padx=(5, 0))

        ctk.CTkButton(
            button_frame, text="Save Processed", width=120,
            command=self.save_processed_text
        ).pack(side="right", padx=(5, 0))

        # Thin separator
        ctk.CTkFrame(button_frame, width=2, height=28).pack(
            side="right", padx=8)

        # Processing operations
        ctk.CTkButton(
            button_frame, text="Process with AI", width=120,
            command=self.process_markdown_ai
        ).pack(side="right", padx=(5, 0))

        ctk.CTkButton(
            button_frame, text="Clear Content", width=120,
            command=self.clear_markdown_content
        ).pack(side="right")

        # ── Template Selection Section ──
        template_section = ctk.CTkFrame(container)
        template_section.pack(fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(
            template_section, text="Processing Template",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            template_section,
            text="Choose processing template for AI optimization:"
        ).pack(anchor="w", padx=10, pady=(0, 5))

        template_button_frame = ctk.CTkFrame(template_section, fg_color="transparent")
        template_button_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.template_var = tk.StringVar(value="Review Papers")
        template_combo = ctk.CTkComboBox(
            template_button_frame,
            variable=self.template_var,
            values=["Review Papers", "Technical Papers", "Custom Template"],
            state="readonly", width=250,
            command=self.on_template_changed
        )
        template_combo.pack(side="left")

        self.template_desc_var = tk.StringVar()
        ctk.CTkLabel(
            template_button_frame, textvariable=self.template_desc_var,
            font=ctk.CTkFont(size=11, slant="italic")
        ).pack(side="left", padx=(15, 0))

        # ── Content Processing Area (inner tabview) ──
        content_section = ctk.CTkFrame(container)
        content_section.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        content_header_frame = ctk.CTkFrame(content_section, fg_color="transparent")
        content_header_frame.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            content_header_frame, text="Content",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")

        self.content_tabview = ctk.CTkTabview(content_section, height=300)
        self.content_tabview.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.content_tabview.add("Source Content")
        self.content_tabview.add("AI Processed")

        # Source Content tab
        source_frame = self.content_tabview.tab("Source Content")
        self.source_text = ctk.CTkTextbox(
            source_frame,
            font=ctk.CTkFont(family="Consolas", size=11),
            state="disabled", wrap="word"
        )
        self.source_text.pack(fill="both", expand=True, padx=5, pady=5)

        # AI Processed tab
        processed_frame = self.content_tabview.tab("AI Processed")
        self.processed_text = ctk.CTkTextbox(
            processed_frame,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word"
        )
        self.processed_text.pack(fill="both", expand=True, padx=5, pady=5)

        # ── Statistics and File Info Section ──
        stats_section = ctk.CTkFrame(container, fg_color="transparent")
        stats_section.pack(fill="x", padx=15)

        self.content_stats_var = tk.StringVar(value="No content loaded")
        ctk.CTkLabel(
            stats_section, textvariable=self.content_stats_var
        ).pack(side="left")

        self.file_info_var = tk.StringVar(value="")
        ctk.CTkLabel(
            stats_section, textvariable=self.file_info_var,
            font=ctk.CTkFont(size=10, slant="italic")
        ).pack(side="left", padx=(20, 0))

        self.processing_status_var = tk.StringVar(value="Ready")
        ctk.CTkLabel(
            stats_section, textvariable=self.processing_status_var
        ).pack(side="right")

        # Set initial template description
        self.update_template_description()

    # ──────────────────────────────────────────────
    #  Tab 4: MD to SSML (NEW)
    # ──────────────────────────────────────────────

    def create_md_to_ssml_tab(self, parent_frame):
        """Create the MD to SSML tab with SSML conversion, editor, save/load"""
        container = ctk.CTkScrollableFrame(parent_frame)
        container.pack(fill="both", expand=True, padx=5, pady=5)

        # Title
        ctk.CTkLabel(
            container, text="SSML Conversion",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))

        ctk.CTkLabel(
            container,
            text="Convert AI-processed text to SSML markup for fine-grained voice control.\n"
                 "Uses Gemini AI to add proper SSML tags (<p>, <s>, <break>, <emphasis>, <say-as>, etc.).",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        ).pack(anchor="w", padx=15, pady=(0, 15))

        # ── Action Buttons ──
        action_section = ctk.CTkFrame(container)
        action_section.pack(fill="x", padx=15, pady=(0, 15))

        action_frame = ctk.CTkFrame(action_section, fg_color="transparent")
        action_frame.pack(fill="x", padx=10, pady=10)

        self.ssml_convert_btn = ctk.CTkButton(
            action_frame, text="Convert to SSML", width=160,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.convert_md_to_ssml,
        )
        self.ssml_convert_btn.pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            action_frame, text="Load SSML", width=100,
            command=self.load_ssml_file,
        ).pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            action_frame, text="Save SSML", width=100,
            command=self.save_ssml_file,
        ).pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            action_frame, text="Clear", width=80,
            command=self.clear_ssml_content,
        ).pack(side="left")

        self.ssml_status_label = ctk.CTkLabel(
            action_frame, text="",
            font=ctk.CTkFont(size=11, slant="italic"),
        )
        self.ssml_status_label.pack(side="left", padx=(15, 0))

        # ── SSML Editor ──
        editor_section = ctk.CTkFrame(container)
        editor_section.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkLabel(
            editor_section, text="SSML Content",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self.ssml_text = ctk.CTkTextbox(
            editor_section,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word", height=400,
        )
        self.ssml_text.pack(fill="both", expand=True, padx=10, pady=(0, 5))

        ctk.CTkLabel(
            editor_section,
            text='Edit SSML directly. Supported tags: <speak>, <p>, <s>, <break>, '
                 '<prosody>, <emphasis>, <say-as>',
            font=ctk.CTkFont(size=10, slant="italic"),
            text_color="gray",
        ).pack(anchor="w", padx=10, pady=(0, 10))

        # ── SSML Statistics ──
        self.ssml_stats_var = tk.StringVar(value="No SSML content")
        ctk.CTkLabel(
            container, textvariable=self.ssml_stats_var,
            font=ctk.CTkFont(size=10, slant="italic"),
        ).pack(anchor="w", padx=15, pady=(0, 10))

    # ──────────────────────────────────────────────
    #  Tab 5: Audio Config
    # ──────────────────────────────────────────────

    def create_audio_config_tab(self, parent_frame):
        """Create the Audio Configuration tab with voice selection, rate, format controls"""
        # Use CTkScrollableFrame to fix overflow on small windows
        container = ctk.CTkScrollableFrame(parent_frame)
        container.pack(fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(
            container, text="Audio Generation Settings",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", padx=15, pady=(10, 15))

        # ── Voice Selection Section ──
        voice_section = ctk.CTkFrame(container)
        voice_section.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkLabel(
            voice_section, text="Voice Selection",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        voice_grid = ctk.CTkFrame(voice_section, fg_color="transparent")
        voice_grid.pack(fill="x", padx=10, pady=(0, 10))
        voice_grid.grid_columnconfigure(1, weight=1)

        # Voice model type selector
        ctk.CTkLabel(voice_grid, text="Model:").grid(
            row=0, column=0, sticky="w", padx=(0, 10), pady=5)
        self.voice_model_var = tk.StringVar(value=VOICE_MODEL_CHIRP3_HD)
        self.voice_model_combo = ctk.CTkComboBox(
            voice_grid, variable=self.voice_model_var,
            values=VOICE_MODELS, state="readonly", width=200,
            command=self._on_model_changed
        )
        self.voice_model_combo.grid(row=0, column=1, sticky="w", pady=5)

        # Gender selector
        ctk.CTkLabel(voice_grid, text="Gender:").grid(
            row=1, column=0, sticky="w", padx=(0, 10), pady=5)
        self.voice_gender_var = tk.StringVar(value="Male")
        gender_combo = ctk.CTkComboBox(
            voice_grid, variable=self.voice_gender_var,
            values=["Male", "Female"], state="readonly", width=150,
            command=self._on_gender_changed
        )
        gender_combo.grid(row=1, column=1, sticky="w", pady=5)

        # Voice name selector
        ctk.CTkLabel(voice_grid, text="Voice:").grid(
            row=2, column=0, sticky="w", padx=(0, 10), pady=5)
        self.voice_name_var = tk.StringVar(value="Charon")
        male_display = [voice_display_name(v) for v in CHIRP3_HD_MALE_VOICES]
        self.voice_name_combo = ctk.CTkComboBox(
            voice_grid, variable=self.voice_name_var,
            values=male_display if male_display else ["Charon"],
            state="readonly", width=250,
        )
        self.voice_name_combo.grid(row=2, column=1, sticky="w", pady=5)

        # Language/Locale
        ctk.CTkLabel(voice_grid, text="Locale:").grid(
            row=3, column=0, sticky="w", padx=(0, 10), pady=5)
        self.voice_locale_var = tk.StringVar(value="en-GB")
        locale_combo = ctk.CTkComboBox(
            voice_grid, variable=self.voice_locale_var,
            values=["en-GB", "en-US", "en-AU"], state="readonly", width=150,
        )
        locale_combo.grid(row=3, column=1, sticky="w", pady=5)

        # ── Speech Settings Section ──
        speech_section = ctk.CTkFrame(container)
        speech_section.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkLabel(
            speech_section, text="Speech Settings",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        speech_grid = ctk.CTkFrame(speech_section, fg_color="transparent")
        speech_grid.pack(fill="x", padx=10, pady=(0, 10))
        speech_grid.grid_columnconfigure(1, weight=1)

        # Speaking rate slider
        ctk.CTkLabel(speech_grid, text="Speaking Rate:").grid(
            row=0, column=0, sticky="w", padx=(0, 10), pady=5)

        rate_frame = ctk.CTkFrame(speech_grid, fg_color="transparent")
        rate_frame.grid(row=0, column=1, sticky="ew", pady=5)

        self.speaking_rate_var = tk.DoubleVar(value=DEFAULT_SPEAKING_RATE)
        self.rate_slider = ctk.CTkSlider(
            rate_frame, from_=0.25, to=2.0,
            variable=self.speaking_rate_var,
            number_of_steps=35,
            command=self._on_rate_changed,
            width=300,
        )
        self.rate_slider.pack(side="left", padx=(0, 10))

        self.rate_label = ctk.CTkLabel(
            rate_frame, text=f"{DEFAULT_SPEAKING_RATE:.2f}x",
            font=ctk.CTkFont(size=12, weight="bold"), width=60,
        )
        self.rate_label.pack(side="left")

        ctk.CTkLabel(
            speech_grid, text="(0.25 = slow, 1.0 = normal, 2.0 = fast)",
            font=ctk.CTkFont(size=10, slant="italic"), text_color="gray",
        ).grid(row=1, column=1, sticky="w", pady=(0, 5))

        # Pitch slider (row 2-3, disabled by default for Chirp 3 HD)
        ctk.CTkLabel(speech_grid, text="Pitch:").grid(
            row=2, column=0, sticky="w", padx=(0, 10), pady=5)

        pitch_frame = ctk.CTkFrame(speech_grid, fg_color="transparent")
        pitch_frame.grid(row=2, column=1, sticky="ew", pady=5)

        self.pitch_var = tk.DoubleVar(value=0.0)
        self.pitch_slider = ctk.CTkSlider(
            pitch_frame, from_=-20.0, to=20.0,
            variable=self.pitch_var,
            number_of_steps=40,
            command=self._on_pitch_changed,
            width=300,
        )
        self.pitch_slider.pack(side="left", padx=(0, 10))
        self.pitch_slider.configure(state="disabled")  # Disabled for Chirp 3 HD

        self.pitch_label = ctk.CTkLabel(
            pitch_frame, text="0.0 st",
            font=ctk.CTkFont(size=12, weight="bold"), width=60,
        )
        self.pitch_label.pack(side="left")

        # Note about pitch availability
        self.pitch_note_label = ctk.CTkLabel(
            speech_grid,
            text="Note: Pitch control is not available for Chirp 3 HD voices.",
            font=ctk.CTkFont(size=10, slant="italic"), text_color="gray",
        )
        self.pitch_note_label.grid(row=3, column=1, sticky="w", pady=(0, 5))

        # ── Output Format Section ──
        format_section = ctk.CTkFrame(container)
        format_section.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkLabel(
            format_section, text="Output Format",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        format_grid = ctk.CTkFrame(format_section, fg_color="transparent")
        format_grid.pack(fill="x", padx=10, pady=(0, 10))
        format_grid.grid_columnconfigure(1, weight=1)

        # Audio format selector
        ctk.CTkLabel(format_grid, text="Format:").grid(
            row=0, column=0, sticky="w", padx=(0, 10), pady=5)
        self.audio_format_var = tk.StringVar(value="MP3")
        format_combo = ctk.CTkComboBox(
            format_grid, variable=self.audio_format_var,
            values=AUDIO_FORMATS, state="readonly", width=150,
        )
        format_combo.grid(row=0, column=1, sticky="w", pady=5)

        # Format descriptions
        ctk.CTkLabel(
            format_grid,
            text="MP3 = standard | WAV = lossless | OGG = compressed | M4B = audiobook with chapters",
            font=ctk.CTkFont(size=10, slant="italic"), text_color="gray",
        ).grid(row=1, column=1, sticky="w", pady=(0, 5))

        # Bitrate selector
        ctk.CTkLabel(format_grid, text="Bitrate:").grid(
            row=2, column=0, sticky="w", padx=(0, 10), pady=5)
        self.bitrate_var = tk.StringVar(value="128k")
        bitrate_combo = ctk.CTkComboBox(
            format_grid, variable=self.bitrate_var,
            values=BITRATE_OPTIONS, state="readonly", width=150,
        )
        bitrate_combo.grid(row=2, column=1, sticky="w", pady=5)

        # Normalize audio checkbox
        self.normalize_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            format_grid, text="Normalize audio volume",
            variable=self.normalize_var,
        ).grid(row=3, column=1, sticky="w", pady=5)

        # ── Preview Section ──
        preview_section = ctk.CTkFrame(container)
        preview_section.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkLabel(
            preview_section, text="Voice Preview",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        preview_frame = ctk.CTkFrame(preview_section, fg_color="transparent")
        preview_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.preview_btn = ctk.CTkButton(
            preview_frame, text="Preview Voice", width=150,
            command=self.preview_voice,
        )
        self.preview_btn.pack(side="left")

        self.preview_status_label = ctk.CTkLabel(
            preview_frame, text="",
            font=ctk.CTkFont(size=11, slant="italic"),
        )
        self.preview_status_label.pack(side="left", padx=(15, 0))

        # TTS availability status
        if not TTS_AVAILABLE:
            ctk.CTkLabel(
                container,
                text="Google Cloud TTS SDK not available. Install with: pip install google-cloud-texttospeech",
                font=ctk.CTkFont(size=11, slant="italic"), text_color="orange",
            ).pack(anchor="w", padx=15, pady=(5, 0))
        elif audio_generator and not audio_generator.is_ready:
            ctk.CTkLabel(
                container,
                text="TTS client not initialized. Check Google Cloud credentials.",
                font=ctk.CTkFont(size=11, slant="italic"), text_color="orange",
            ).pack(anchor="w", padx=15, pady=(5, 0))

    # ──────────────────────────────────────────────
    #  Tab 6: Speech Output
    # ──────────────────────────────────────────────

    def create_speech_output_tab(self, parent_frame):
        """Create the Speech Output tab with generate button, progress, export"""
        container = ctk.CTkScrollableFrame(parent_frame)
        container.pack(fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(
            container, text="Speech Synthesis & Output",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", padx=15, pady=(10, 15))

        # ── Content Source Section ──
        source_section = ctk.CTkFrame(container)
        source_section.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkLabel(
            source_section, text="Content Source",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        source_options = ctk.CTkFrame(source_section, fg_color="transparent")
        source_options.pack(fill="x", padx=10, pady=(0, 10))

        self.content_source_var = tk.StringVar(value="ssml")

        ctk.CTkRadioButton(
            source_options, text="SSML content (from MD to SSML tab)",
            variable=self.content_source_var, value="ssml",
        ).pack(anchor="w", pady=2)

        ctk.CTkRadioButton(
            source_options, text="AI Processed text (from Markdown Processing tab)",
            variable=self.content_source_var, value="processed",
        ).pack(anchor="w", pady=2)

        ctk.CTkRadioButton(
            source_options, text="Source markdown (unprocessed)",
            variable=self.content_source_var, value="source",
        ).pack(anchor="w", pady=2)

        # Include description checkbox
        self.include_description_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            source_options, text="Prepend audio paper description as intro",
            variable=self.include_description_var,
        ).pack(anchor="w", pady=(5, 0))

        # ── Output Path Section ──
        output_section = ctk.CTkFrame(container)
        output_section.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkLabel(
            output_section, text="Output File",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        output_path_frame = ctk.CTkFrame(output_section, fg_color="transparent")
        output_path_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.output_path_var = tk.StringVar()
        output_entry = ctk.CTkEntry(
            output_path_frame, textvariable=self.output_path_var,
            state="readonly",
        )
        output_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(
            output_path_frame, text="Browse", width=100,
            command=self.browse_output_path,
        ).pack(side="right", padx=(0, 5))

        ctk.CTkButton(
            output_path_frame, text="Auto", width=80,
            command=self.auto_output_path,
        ).pack(side="right")

        # ── Generate Button ──
        generate_section = ctk.CTkFrame(container)
        generate_section.pack(fill="x", padx=15, pady=(0, 15))

        gen_btn_frame = ctk.CTkFrame(generate_section, fg_color="transparent")
        gen_btn_frame.pack(fill="x", padx=10, pady=10)

        self.generate_btn = ctk.CTkButton(
            gen_btn_frame, text="Generate Audio Paper",
            width=250, height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.generate_audio_paper,
        )
        self.generate_btn.pack(side="left")

        self.gen_status_label = ctk.CTkLabel(
            gen_btn_frame, text="Ready",
            font=ctk.CTkFont(size=12),
        )
        self.gen_status_label.pack(side="left", padx=(15, 0))

        # Progress bar
        self.gen_progress = ctk.CTkProgressBar(generate_section)
        self.gen_progress.pack(fill="x", padx=10, pady=(0, 5))
        self.gen_progress.set(0)

        self.gen_progress_label = ctk.CTkLabel(
            generate_section, text="",
            font=ctk.CTkFont(size=11, slant="italic"),
        )
        self.gen_progress_label.pack(anchor="w", padx=10, pady=(0, 10))

        # ── Results Section ──
        results_section = ctk.CTkFrame(container)
        results_section.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkLabel(
            results_section, text="Generation Results",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        results_grid = ctk.CTkFrame(results_section, fg_color="transparent")
        results_grid.pack(fill="x", padx=10, pady=(0, 10))
        results_grid.grid_columnconfigure(1, weight=1)

        # Result fields
        result_fields = [
            ("Duration:", "gen_duration_var"),
            ("File Size:", "gen_filesize_var"),
            ("Chunks:", "gen_chunks_var"),
            ("Voice:", "gen_voice_var"),
            ("Format:", "gen_format_var"),
            ("Generation Time:", "gen_time_var"),
        ]
        for row, (label, var_name) in enumerate(result_fields):
            ctk.CTkLabel(results_grid, text=label).grid(
                row=row, column=0, sticky="w", padx=(0, 10), pady=2)
            var = tk.StringVar(value="-")
            setattr(self, var_name, var)
            ctk.CTkLabel(
                results_grid, textvariable=var,
                font=ctk.CTkFont(size=12),
            ).grid(row=row, column=1, sticky="w", pady=2)

        # Playback / open file button
        playback_frame = ctk.CTkFrame(results_section, fg_color="transparent")
        playback_frame.pack(fill="x", padx=10, pady=(5, 10))

        self.open_file_btn = ctk.CTkButton(
            playback_frame, text="Open Output File", width=150,
            command=self.open_output_file, state="disabled",
        )
        self.open_file_btn.pack(side="left")

        self.open_folder_btn = ctk.CTkButton(
            playback_frame, text="Open Folder", width=120,
            command=self.open_output_folder, state="disabled",
        )
        self.open_folder_btn.pack(side="left", padx=(10, 0))

    # ──────────────────────────────────────────────
    #  Status Bar
    # ──────────────────────────────────────────────

    def setup_status_bar(self):
        """Create the status bar"""
        status_frame = ctk.CTkFrame(self.root)
        status_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))

        self.status_var = tk.StringVar(value="Ready")
        ctk.CTkLabel(status_frame, textvariable=self.status_var).pack(
            side="left", padx=10)

        self.progress_bar = ctk.CTkProgressBar(status_frame, width=200)
        self.progress_bar.pack(side="right", padx=10)
        self.progress_bar.set(0)

    # ══════════════════════════════════════════════
    #  Tab 1: Paper Information Methods
    # ══════════════════════════════════════════════

    def generate_description(self):
        """Generate audio paper description"""
        title = self.title_text.get("0.0", "end").strip()
        authors = self.authors_var.get().strip()
        journal = self.journal_var.get().strip()
        year = self.year_var.get().strip()
        doi = self.doi_var.get().strip()

        if not title:
            messagebox.showwarning("Missing Information",
                                   "Please enter a paper title first.")
            return

        # Build audio paper description
        description_parts = []
        description_parts.append(f'This is an audio version of the paper "{title}"')

        if authors:
            description_parts.append(f" by {authors}")

        if year and journal:
            description_parts.append(f", published {year} in {journal}")
        elif journal:
            description_parts.append(f", published in {journal}")
        elif year:
            description_parts.append(f", published in {year}")

        description_parts.append(".")

        if doi:
            description_parts.append(
                f"\n\nThe original paper can be found at: https://doi.org/{doi}"
            )

        if hasattr(self, 'pdf_metadata') and self.pdf_metadata.get('license'):
            license_info = self.pdf_metadata['license']
            description_parts.append(
                f"\n\nThe original work is published under {license_info}."
            )
            if 'creativecommons.org' in license_info.lower():
                description_parts.append(
                    " For license details, visit: "
                    "https://creativecommons.org/licenses/"
                )

        description_parts.append(
            "\n\nThis audio version is a derivative work created for "
            "accessibility and educational purposes. It preserves the "
            "original scientific content while optimizing the text for "
            "audio consumption."
        )

        description_parts.append(
            "\n\nGenerated by Science2Go - Turn Academic Papers into Audio Papers"
        )
        description_parts.append("\nhttps://github.com/biterik/science2go")

        description_text = "".join(description_parts)

        # Display in description preview (leave editable so user can tweak)
        self.description_text.configure(state="normal")
        self.description_text.delete("0.0", "end")
        self.description_text.insert("0.0", description_text)

        self.status_var.set("Audio paper description generated")

    # ── Paper Info: Save / Load / Clear ──

    def save_paper_info(self):
        """Save paper metadata to a JSON file."""
        title = self.title_text.get("0.0", "end").strip()
        if not title:
            messagebox.showwarning("No Data", "No paper information to save.")
            return

        # Build a safe default filename from the title
        safe_title = re.sub(r'[^\w\s-]', '', title)[:60].strip().replace(' ', '_')
        default_name = f"{safe_title}_info.json" if safe_title else "paper_info.json"

        file_path = filedialog.asksaveasfilename(
            title="Save Paper Info",
            defaultextension=".json",
            initialfile=default_name,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not file_path:
            return

        data = {
            "science2go_type": "paper_info",
            "saved_at": datetime.now().isoformat(),
            "source_pdf": self.pdf_path_var.get(),
            "paper_info": {
                "title": title,
                "authors": self.authors_var.get().strip(),
                "journal": self.journal_var.get().strip(),
                "year": self.year_var.get().strip(),
                "doi": self.doi_var.get().strip(),
                "abstract": self.abstract_text.get("0.0", "end").strip(),
            },
        }

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.status_var.set(f"Paper info saved: {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save paper info:\n{e}")

    def load_paper_info(self):
        """Load paper metadata from a JSON file."""
        file_path = filedialog.askopenfilename(
            title="Load Paper Info",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to read file:\n{e}")
            return

        if data.get("science2go_type") != "paper_info":
            messagebox.showwarning(
                "Wrong File",
                "This file does not appear to be a Science2Go paper info file."
            )
            return

        info = data.get("paper_info", {})

        # Populate fields
        self.title_text.delete("0.0", "end")
        if info.get("title"):
            self.title_text.insert("0.0", info["title"])

        self.authors_var.set(info.get("authors", ""))
        self.journal_var.set(info.get("journal", ""))
        self.year_var.set(info.get("year", ""))
        self.doi_var.set(info.get("doi", ""))

        self.abstract_text.delete("0.0", "end")
        if info.get("abstract"):
            self.abstract_text.insert("0.0", info["abstract"])

        if data.get("source_pdf"):
            self.pdf_path_var.set(data["source_pdf"])

        self.status_var.set(f"Paper info loaded: {os.path.basename(file_path)}")

    def clear_paper_info(self):
        """Clear all paper metadata fields."""
        self.title_text.delete("0.0", "end")
        self.authors_var.set("")
        self.journal_var.set("")
        self.year_var.set("")
        self.doi_var.set("")
        self.abstract_text.delete("0.0", "end")

        self.description_text.configure(state="normal")
        self.description_text.delete("0.0", "end")
        self.description_text.configure(state="disabled")

        self.status_var.set("Paper information cleared")

    # ══════════════════════════════════════════════
    #  Tab 2: PDF to Markdown Methods
    # ══════════════════════════════════════════════

    def browse_pdf(self):
        """Browse for PDF file"""
        file_path = filedialog.askopenfilename(
            title="Select Academic Paper",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if file_path:
            self.pdf_path_var.set(file_path)
            self.analyze_btn.configure(state="normal")
            if self.convert_btn is not None:
                self.convert_btn.configure(state="normal")
            self.status_var.set(f"PDF selected: {Path(file_path).name}")

            # Auto-detect PDF type and set OCR toggle
            self._detect_and_set_ocr(file_path)

    def _detect_and_set_ocr(self, pdf_path: str):
        """Run PDF type detection and auto-set the conversion mode."""
        if detect_pdf_type is None or not hasattr(self, 'conversion_mode_var'):
            return

        try:
            result = detect_pdf_type(pdf_path)
            has_text = result.get('has_native_text', False)
            avg_chars = result.get('avg_chars_per_page', 0)
            recommendation = result.get('recommendation', MODE_FULL_PIPELINE)

            self.conversion_mode_var.set(recommendation)

            if has_text:
                self.mode_detection_label.configure(
                    text=f"Auto: native text ({avg_chars:.0f} chars/page avg)",
                    text_color="green",
                )
            else:
                self.mode_detection_label.configure(
                    text="Auto: scanned PDF (OCR recommended)",
                    text_color="orange",
                )
        except Exception:
            self.mode_detection_label.configure(
                text="", text_color="gray",
            )

    def analyze_pdf(self):
        """Analyze PDF file for metadata"""
        pdf_path = self.pdf_path_var.get()
        if not pdf_path or not PDF_METADATA_AVAILABLE:
            messagebox.showerror("Error", "PDF analysis not available")
            return

        # Disable button during analysis
        self.analyze_btn.configure(state="disabled", text="Analyzing...")
        self.status_var.set("Analyzing PDF...")
        self.progress_bar.start()

        def analyze_thread():
            try:
                metadata = self.pdf_extractor.extract_metadata(pdf_path)
                self.root.after(0, lambda: self.handle_pdf_analysis_complete(metadata))
            except Exception as e:
                self.root.after(0, lambda: self.handle_pdf_analysis_error(str(e)))

        threading.Thread(target=analyze_thread, daemon=True).start()

    def handle_pdf_analysis_complete(self, metadata):
        """Handle PDF analysis completion"""
        self.progress_bar.stop()
        self.progress_bar.set(0)
        self.analyze_btn.configure(state="normal", text="Analyze PDF")

        if metadata.get('success', False):
            self.pdf_metadata = metadata

            # Populate form fields
            if metadata.get('title'):
                self.title_text.delete("0.0", "end")
                self.title_text.insert("0.0", metadata['title'])

            if metadata.get('authors'):
                self.authors_var.set(metadata['authors'])

            if metadata.get('journal'):
                self.journal_var.set(metadata['journal'])

            if metadata.get('year'):
                self.year_var.set(metadata['year'])

            if metadata.get('doi'):
                self.doi_var.set(metadata['doi'])

            if metadata.get('abstract'):
                self.abstract_text.delete("0.0", "end")
                self.abstract_text.insert("0.0", metadata['abstract'])

            method = metadata.get('extraction_method', 'Unknown')
            self.status_var.set(f"Metadata extracted via {method}")

            success_msg = (
                f"Paper metadata extracted successfully!\n\n"
                f"Method: {method}\n"
                f"Title: {metadata['title'][:50]}"
                f"{'...' if len(metadata.get('title', '')) > 50 else ''}"
            )
            if metadata.get('license'):
                success_msg += f"\nLicense: {metadata['license']}"

            messagebox.showinfo("Success", success_msg)
        else:
            error = metadata.get('error', 'Unknown error')
            self.handle_pdf_analysis_error(error)

    def handle_pdf_analysis_error(self, error_msg):
        """Handle PDF analysis error"""
        self.progress_bar.stop()
        self.progress_bar.set(0)
        self.analyze_btn.configure(state="normal", text="Analyze PDF")

        self.status_var.set(f"Analysis failed: {error_msg}")
        messagebox.showerror(
            "Analysis Failed",
            f"Failed to extract metadata from PDF:\n\n{error_msg}\n\n"
            f"You can still fill in the paper information manually."
        )

    # ── PDF-to-Markdown Conversion ──

    def convert_pdf_to_markdown(self):
        """Convert loaded PDF to Markdown using the selected conversion mode"""
        pdf_path = self.pdf_path_var.get()
        if not pdf_path:
            messagebox.showerror("Error", "Please select a PDF file first.")
            return

        # Read conversion mode on main thread
        mode = (self.conversion_mode_var.get()
                if hasattr(self, 'conversion_mode_var')
                else MODE_FULL_PIPELINE)

        # Fast Extract doesn't need marker-pdf
        if mode != MODE_FAST_EXTRACT:
            if not MARKER_AVAILABLE or pdf_converter is None:
                messagebox.showerror(
                    "Error",
                    "marker-pdf is not installed.\n"
                    "Install with: pip install marker-pdf"
                )
                return

        # Disable button during conversion
        self.convert_btn.configure(state="disabled", text="Converting...")
        self.convert_progress.start()
        self.convert_status_label.configure(
            text=f"Converting ({mode})..."
        )
        self.status_var.set("Converting PDF to Markdown...")

        def convert_thread():
            def progress_cb(msg):
                self.root.after(
                    0, lambda m=msg: self.convert_status_label.configure(text=m)
                )

            if mode == MODE_FAST_EXTRACT:
                result = fast_extract_text(pdf_path, progress_callback=progress_cb)
            elif mode == MODE_MARKER_NO_OCR:
                result = pdf_converter.convert(
                    pdf_path, disable_ocr=True, progress_callback=progress_cb,
                )
            else:
                result = pdf_converter.convert(
                    pdf_path, disable_ocr=False, progress_callback=progress_cb,
                )
            self.root.after(0, lambda: self._handle_conversion_result(result))

        threading.Thread(target=convert_thread, daemon=True).start()

    def _handle_conversion_result(self, result):
        """Handle PDF-to-Markdown conversion result on main thread"""
        self.convert_progress.stop()
        self.convert_progress.set(0)
        self.convert_btn.configure(
            state="normal", text="Convert PDF to Markdown"
        )

        if result.get('success'):
            markdown_text = result['markdown']
            self.converted_markdown = markdown_text

            # Populate Tab 2 markdown preview
            self.md_preview_text.configure(state="normal")
            self.md_preview_text.delete("0.0", "end")
            self.md_preview_text.insert("0.0", markdown_text)
            self.md_preview_text.configure(state="disabled")

            # Also populate Tab 3 source text
            self.source_text.configure(state="normal")
            self.source_text.delete("0.0", "end")
            self.source_text.insert("0.0", markdown_text)
            self.source_text.configure(state="disabled")

            # Update statistics
            self.update_md_preview_stats()
            self.update_content_statistics()

            # Update status
            word_count = len(markdown_text.split())
            mode_info = result.get('conversion_mode', '')
            mode_tag = f" [{mode_info}]" if mode_info else ""
            self.convert_status_label.configure(
                text=f"Done: {word_count:,} words extracted{mode_tag}"
            )
            self.status_var.set("PDF converted to Markdown successfully")

            messagebox.showinfo(
                "Conversion Complete",
                f"PDF converted to Markdown successfully!\n\n"
                f"Words extracted: {word_count:,}\n\n"
                f"The content is shown in the preview below.\n"
                f"Switch to the Markdown Processing tab to process it with AI."
            )
        else:
            error = result.get('error', 'Unknown error')
            self.convert_status_label.configure(text=f"Failed")
            self.status_var.set(f"PDF conversion failed: {error}")
            messagebox.showerror(
                "Conversion Failed",
                f"Failed to convert PDF to Markdown:\n\n{error}"
            )

    def update_md_preview_stats(self):
        """Update markdown preview statistics"""
        self.md_preview_text.configure(state="normal")
        content = self.md_preview_text.get("0.0", "end").strip()
        self.md_preview_text.configure(state="disabled")

        if content:
            words = len(content.split())
            chars = len(content)
            # Rough page estimate (~250 words/page)
            pages = max(1, words // 250)
            self.md_preview_stats_var.set(
                f"{words:,} words | {chars:,} characters | ~{pages} pages"
            )
        else:
            self.md_preview_stats_var.set("No markdown loaded")

    # ── Markdown File Operations ──

    def browse_markdown_file(self):
        """Browse for markdown file"""
        file_path = filedialog.askopenfilename(
            title="Select Markdown File",
            filetypes=[("Markdown files", "*.md"), ("Text files", "*.txt"),
                       ("All files", "*.*")]
        )
        if file_path:
            self.markdown_path_var.set(file_path)
            self.load_markdown_content(file_path)

    def load_markdown_content(self, file_path):
        """Load markdown content from file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Display in Tab 2 preview
            self.md_preview_text.configure(state="normal")
            self.md_preview_text.delete("0.0", "end")
            self.md_preview_text.insert("0.0", content)
            self.md_preview_text.configure(state="disabled")

            # Also display in Tab 3 source tab
            self.source_text.configure(state="normal")
            self.source_text.delete("0.0", "end")
            self.source_text.insert("0.0", content)
            self.source_text.configure(state="disabled")

            # Update statistics and file info
            self.update_md_preview_stats()
            self.update_content_statistics()
            self.update_file_info()

            self.status_var.set(f"Loaded: {Path(file_path).name}")

        except Exception as e:
            messagebox.showerror("Error",
                                 f"Failed to load markdown file:\n{str(e)}")

    def save_source_markdown(self):
        """Save the raw source markdown to a file"""
        # Get content from Tab 2 preview (or Tab 3 source)
        self.md_preview_text.configure(state="normal")
        source_content = self.md_preview_text.get("0.0", "end").strip()
        self.md_preview_text.configure(state="disabled")

        if not source_content:
            # Fall back to Tab 3 source
            self.source_text.configure(state="normal")
            source_content = self.source_text.get("0.0", "end").strip()
            self.source_text.configure(state="disabled")

        if not source_content:
            messagebox.showwarning("No Content",
                                   "No source markdown content to save.")
            return

        # Generate default filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"source_markdown_{timestamp}.md"

        file_path = filedialog.asksaveasfilename(
            title="Save Source Markdown",
            defaultextension=".md",
            initialfile=default_filename,
            initialdir=config.projects_dir,
            filetypes=[
                ("Markdown files", "*.md"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ]
        )

        if not file_path:
            return

        try:
            # Prepare metadata header
            metadata = {
                "saved_at": datetime.now().isoformat(),
                "source_pdf": self.pdf_path_var.get(),
                "content_type": "source_markdown",
                "paper_info": {
                    "title": self.title_text.get("0.0", "end").strip(),
                    "authors": self.authors_var.get(),
                    "journal": self.journal_var.get(),
                    "year": self.year_var.get(),
                    "doi": self.doi_var.get(),
                }
            }

            content_with_metadata = (
                f"<!--\nScience2Go Source Markdown\n"
                f"{json.dumps(metadata, indent=2)}\n-->\n\n"
                f"{source_content}"
            )

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content_with_metadata)

            self.current_source_file = file_path
            self.update_file_info()

            self.status_var.set(
                f"Source markdown saved: {Path(file_path).name}"
            )
            messagebox.showinfo("Saved",
                                f"Source markdown saved to:\n{file_path}")

        except Exception as e:
            messagebox.showerror("Save Error",
                                 f"Failed to save source markdown:\n{str(e)}")

    def load_source_markdown(self):
        """Load a markdown file into the Source Content tab"""
        file_path = filedialog.askopenfilename(
            title="Load Source Markdown",
            initialdir=config.projects_dir,
            filetypes=[
                ("Markdown files", "*.md"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ]
        )

        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Strip metadata header if present
            source_content = content
            if content.startswith('<!--\nScience2Go Source Markdown\n'):
                try:
                    metadata_end = content.find('-->')
                    if metadata_end != -1:
                        metadata_section = content[
                            content.find('{\n'):metadata_end
                        ]
                        metadata = json.loads(metadata_section)
                        source_content = content[metadata_end + 3:].strip()

                        # Restore paper info if available
                        paper_info = metadata.get('paper_info', {})
                        if paper_info.get('title'):
                            self.title_text.delete("0.0", "end")
                            self.title_text.insert("0.0", paper_info['title'])
                        if paper_info.get('authors'):
                            self.authors_var.set(paper_info['authors'])
                        if paper_info.get('journal'):
                            self.journal_var.set(paper_info['journal'])
                        if paper_info.get('year'):
                            self.year_var.set(paper_info['year'])
                        if paper_info.get('doi'):
                            self.doi_var.set(paper_info['doi'])
                except (json.JSONDecodeError, ValueError):
                    pass

            # Load into Tab 2 preview
            self.md_preview_text.configure(state="normal")
            self.md_preview_text.delete("0.0", "end")
            self.md_preview_text.insert("0.0", source_content)
            self.md_preview_text.configure(state="disabled")

            # Also load into Tab 3 source text widget
            self.source_text.configure(state="normal")
            self.source_text.delete("0.0", "end")
            self.source_text.insert("0.0", source_content)
            self.source_text.configure(state="disabled")

            # Track file and update UI
            self.current_source_file = file_path
            self.markdown_path_var.set(file_path)
            self.update_md_preview_stats()
            self.update_content_statistics()
            self.update_file_info()

            self.status_var.set(
                f"Source markdown loaded: {Path(file_path).name}"
            )

        except Exception as e:
            messagebox.showerror("Load Error",
                                 f"Failed to load source markdown:\n{str(e)}")

    # ══════════════════════════════════════════════
    #  Tab 3: Markdown Processing Methods
    # ══════════════════════════════════════════════

    def save_processed_text(self):
        """Save AI-processed text to file"""
        processed_content = self.processed_text.get("0.0", "end").strip()
        if not processed_content:
            messagebox.showwarning("No Content", "No processed content to save.")
            return

        # Generate default filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        template = self.template_var.get().replace(" ", "_").lower()
        default_filename = f"processed_{template}_{timestamp}.md"

        # Get save location
        file_path = filedialog.asksaveasfilename(
            title="Save Processed Text",
            defaultextension=".md",
            initialfile=default_filename,
            initialdir=config.projects_dir,
            filetypes=[
                ("Markdown files", "*.md"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ]
        )

        if not file_path:
            return

        try:
            # Prepare metadata for the processed file
            metadata = {
                "generated_at": datetime.now().isoformat(),
                "template_used": self.template_var.get(),
                "source_file": self.markdown_path_var.get(),
                "processing_stats": self.get_processing_stats(),
                "paper_info": {
                    "title": self.title_text.get("0.0", "end").strip(),
                    "authors": self.authors_var.get(),
                    "journal": self.journal_var.get(),
                    "year": self.year_var.get(),
                    "doi": self.doi_var.get(),
                }
            }

            # Create content with metadata header
            content_with_metadata = (
                f"<!--\nScience2Go Processed Content\n"
                f"{json.dumps(metadata, indent=2)}\n-->\n\n"
                f"{processed_content}"
            )

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content_with_metadata)

            # Update current file tracking
            self.current_processed_file = file_path
            self.update_file_info()

            self.status_var.set(f"Processed content saved: {Path(file_path).name}")
            messagebox.showinfo("Saved",
                                f"Processed content saved to:\n{file_path}")

        except Exception as e:
            messagebox.showerror("Save Error",
                                 f"Failed to save processed content:\n{str(e)}")

    def load_processed_text(self):
        """Load previously saved processed text"""
        file_path = filedialog.askopenfilename(
            title="Load Processed Text",
            initialdir=config.projects_dir,
            filetypes=[
                ("Markdown files", "*.md"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ]
        )

        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Try to extract metadata if present
            metadata = None
            processed_content = content

            if content.startswith('<!--\nScience2Go Processed Content\n'):
                try:
                    metadata_end = content.find('-->')
                    if metadata_end != -1:
                        metadata_section = content[content.find('{\n'):metadata_end]
                        metadata = json.loads(metadata_section)
                        processed_content = content[metadata_end + 3:].strip()
                except (json.JSONDecodeError, ValueError):
                    pass

            # Load content into processed text area
            self.processed_text.delete("0.0", "end")
            self.processed_text.insert("0.0", processed_content)

            # Switch to processed tab
            self.content_tabview.set("AI Processed")

            # Update template if metadata available
            if metadata and metadata.get('template_used'):
                template_used = metadata['template_used']
                if template_used in ["Review Papers", "Technical Papers",
                                     "Custom Template"]:
                    self.template_var.set(template_used)
                    self.update_template_description()

            # Track current file
            self.current_processed_file = file_path

            # Update statistics and file info
            self.update_content_statistics()
            self.update_file_info()

            # Update status
            self.processing_status_var.set("Loaded from file")
            self.status_var.set(
                f"Processed content loaded: {Path(file_path).name}"
            )

            # Show info about loaded content
            info_msg = f"Loaded processed content from:\n{Path(file_path).name}"
            if metadata:
                if metadata.get('generated_at'):
                    info_msg += f"\n\nGenerated: {metadata['generated_at'][:16]}"
                if metadata.get('template_used'):
                    info_msg += f"\nTemplate: {metadata['template_used']}"
                if metadata.get('paper_info', {}).get('title'):
                    title = metadata['paper_info']['title'][:50]
                    info_msg += (
                        f"\nPaper: {title}"
                        f"{'...' if len(metadata['paper_info']['title']) > 50 else ''}"
                    )

            messagebox.showinfo("Loaded", info_msg)

        except Exception as e:
            messagebox.showerror("Load Error",
                                 f"Failed to load processed content:\n{str(e)}")

    def get_processing_stats(self):
        """Get current processing statistics"""
        self.source_text.configure(state="normal")
        source_content = self.source_text.get("0.0", "end").strip()
        self.source_text.configure(state="disabled")
        processed_content = self.processed_text.get("0.0", "end").strip()

        stats = {
            "source_words": len(source_content.split()) if source_content else 0,
            "source_chars": len(source_content),
            "processed_words": (len(processed_content.split())
                                if processed_content else 0),
            "processed_chars": len(processed_content),
        }

        if source_content and processed_content:
            stats["reduction_percentage"] = (
                ((stats["source_chars"] - stats["processed_chars"])
                 / stats["source_chars"]) * 100
            )

        return stats

    def update_file_info(self):
        """Update file information display"""
        info_parts = []

        if self.current_source_file:
            filename = Path(self.current_source_file).name
            info_parts.append(f"Source file: {filename}")
        elif self.markdown_path_var.get():
            filename = Path(self.markdown_path_var.get()).name
            info_parts.append(f"Source: {filename}")

        if self.current_processed_file:
            filename = Path(self.current_processed_file).name
            info_parts.append(f"Processed file: {filename}")

        self.file_info_var.set(" | ".join(info_parts))

    def on_template_changed(self, choice=None):
        """Handle template selection change"""
        self.update_template_description()

    def update_template_description(self):
        """Update template description based on selection"""
        template = self.template_var.get()
        descriptions = {
            "Review Papers": "Optimized for comprehensive review articles and surveys",
            "Technical Papers": "Optimized for technical research papers and studies",
            "Custom Template": "Customizable template for specific processing needs",
        }
        self.template_desc_var.set(descriptions.get(template, ""))

    def process_markdown_ai(self):
        """Process markdown content with Gemini AI"""
        if not TEXT_PROCESSOR_AVAILABLE:
            messagebox.showerror(
                "Error",
                "Text processor not available. "
                "Please check Gemini AI configuration."
            )
            return

        # Check if we have content (need to temporarily enable to read)
        self.source_text.configure(state="normal")
        source_content = self.source_text.get("0.0", "end").strip()
        self.source_text.configure(state="disabled")

        if not source_content:
            messagebox.showwarning("No Content",
                                   "Please load a markdown file first, "
                                   "or convert a PDF to markdown.")
            return

        # Check content length
        if len(source_content) > 1000000:
            if not messagebox.askyesno(
                "Large Content",
                f"Content is quite large ({len(source_content):,} chars). "
                "This may take several minutes to process. Continue?"
            ):
                return

        # Clear current processed file tracking
        self.current_processed_file = None

        # Start processing
        self.processing_status_var.set("Processing with Gemini AI...")
        self.progress_bar.start()

        def process_thread():
            try:
                template_name = self.template_var.get()
                result = process_markdown_content(source_content, template_name)
                self.root.after(
                    0, lambda: self.handle_ai_processing_result(result)
                )
            except Exception as e:
                error_msg = f"AI processing failed: {str(e)}"
                self.root.after(
                    0, lambda: self.handle_ai_processing_error(error_msg)
                )

        threading.Thread(target=process_thread, daemon=True).start()

    def handle_ai_processing_result(self, result):
        """Handle AI processing results"""
        try:
            self.progress_bar.stop()
            self.progress_bar.set(0)

            if result and result.get('success', False):
                processed_content = result.get('processed_content', '')
                self.processed_text.delete("0.0", "end")
                self.processed_text.insert("0.0", processed_content)

                # Switch to processed tab
                self.content_tabview.set("AI Processed")

                # Update statistics
                self.update_content_statistics()
                self.update_file_info()

                # Update status
                processing_time = result.get('processing_time', 0)
                reduction = result.get('reduction_percentage', 0)

                gemini_cost = result.get('gemini_cost', 0)
                cost_str = f" | Est. cost: ${gemini_cost:.4f}" if gemini_cost else ""
                self.processing_status_var.set(
                    f"Processed ({processing_time:.1f}s, "
                    f"{reduction:.1f}% reduction{cost_str})"
                )
                self.status_var.set("AI processing completed successfully")

                # Build cost info for dialog
                cost_lines = ""
                input_tokens = result.get('input_tokens', 0)
                output_tokens = result.get('output_tokens', 0)
                if input_tokens or output_tokens:
                    cost_lines = (
                        f"\nGemini tokens: {input_tokens:,} in / "
                        f"{output_tokens:,} out\n"
                        f"Est. Gemini cost: ${gemini_cost:.4f}\n"
                    )

                messagebox.showinfo(
                    "Success",
                    f"Content processed successfully!\n\n"
                    f"Processing time: {processing_time:.1f} seconds\n"
                    f"Content reduction: {reduction:.1f}%\n"
                    f"{cost_lines}"
                    f"You can now review and edit the processed content.\n\n"
                    f"Tip: Use 'Save Processed' to save this content for later use."
                )
            else:
                error_msg = (result.get('error', 'Unknown error')
                             if result else 'No result returned')
                self.handle_ai_processing_error(
                    f"Processing failed: {error_msg}"
                )

        except Exception as e:
            self.handle_ai_processing_error(f"Error handling results: {str(e)}")

    def handle_ai_processing_error(self, error_msg):
        """Handle AI processing error"""
        self.progress_bar.stop()
        self.progress_bar.set(0)

        self.processing_status_var.set("Processing failed")
        self.status_var.set(f"AI processing error: {error_msg}")

        messagebox.showerror(
            "Processing Failed",
            f"Failed to process content with Gemini AI:\n\n{error_msg}"
        )

    def clear_markdown_content(self):
        """Clear all markdown content"""
        # Clear source content
        self.source_text.configure(state="normal")
        self.source_text.delete("0.0", "end")
        self.source_text.configure(state="disabled")

        # Clear processed content
        self.processed_text.delete("0.0", "end")

        # Clear file paths and tracking
        self.markdown_path_var.set("")
        self.current_processed_file = None
        self.current_source_file = None

        # Reset statistics and file info
        self.content_stats_var.set("No content loaded")
        self.file_info_var.set("")
        self.processing_status_var.set("Ready")

        # Switch back to source tab
        self.content_tabview.set("Source Content")

        self.status_var.set("Content cleared")

    def update_content_statistics(self):
        """Update content statistics"""
        # Need to temporarily enable source_text to read
        self.source_text.configure(state="normal")
        source_content = self.source_text.get("0.0", "end").strip()
        self.source_text.configure(state="disabled")

        processed_content = self.processed_text.get("0.0", "end").strip()

        source_words = len(source_content.split()) if source_content else 0
        source_chars = len(source_content)

        processed_words = (len(processed_content.split())
                           if processed_content else 0)
        processed_chars = len(processed_content)

        if processed_content and source_content:
            reduction = (
                ((source_chars - processed_chars) / source_chars) * 100
                if source_chars > 0 else 0
            )
            stats_text = (
                f"Source: {source_words:,} words, {source_chars:,} chars | "
                f"Processed: {processed_words:,} words, "
                f"{processed_chars:,} chars | "
                f"Reduction: {reduction:.1f}%"
            )
        elif source_content:
            stats_text = (
                f"Source: {source_words:,} words, "
                f"{source_chars:,} chars | Ready for processing"
            )
        else:
            stats_text = "No content loaded"

        self.content_stats_var.set(stats_text)

    # ══════════════════════════════════════════════
    #  Tab 4: MD to SSML Methods
    # ══════════════════════════════════════════════

    def convert_md_to_ssml(self):
        """Convert processed markdown to SSML using Gemini AI with SSML Converter template"""
        if not TEXT_PROCESSOR_AVAILABLE:
            messagebox.showerror(
                "Error",
                "Text processor not available.\n"
                "Please check Gemini AI configuration."
            )
            return

        # Get processed content from Tab 3
        processed_content = self.processed_text.get("0.0", "end").strip()

        if not processed_content:
            messagebox.showwarning(
                "No Content",
                "No processed content available.\n"
                "Process your markdown in the Markdown Processing tab first."
            )
            return

        # Check content length
        if len(processed_content) > 1000000:
            if not messagebox.askyesno(
                "Large Content",
                f"Content is quite large ({len(processed_content):,} chars). "
                "SSML conversion may take several minutes. Continue?"
            ):
                return

        # Start SSML conversion
        self.ssml_convert_btn.configure(state="disabled", text="Converting...")
        self.ssml_status_label.configure(text="Converting to SSML with Gemini AI...")
        self.progress_bar.start()

        def ssml_thread():
            try:
                result = process_markdown_content(
                    processed_content, "SSML Converter"
                )
                self.root.after(
                    0, lambda: self._handle_ssml_result(result)
                )
            except Exception as e:
                error_msg = f"SSML conversion failed: {str(e)}"
                self.root.after(
                    0, lambda: self._handle_ssml_error(error_msg)
                )

        threading.Thread(target=ssml_thread, daemon=True).start()

    def _handle_ssml_result(self, result):
        """Handle SSML conversion result"""
        self.progress_bar.stop()
        self.progress_bar.set(0)
        self.ssml_convert_btn.configure(state="normal", text="Convert to SSML")

        if result and result.get('success', False):
            ssml_content = result.get('processed_content', '')

            # Populate SSML editor
            self.ssml_text.delete("0.0", "end")
            self.ssml_text.insert("0.0", ssml_content)

            # Update statistics
            self.update_ssml_statistics()

            processing_time = result.get('processing_time', 0)
            gemini_cost = result.get('gemini_cost', 0)
            cost_str = f" | Est. cost: ${gemini_cost:.4f}" if gemini_cost else ""
            self.ssml_status_label.configure(
                text=f"Converted in {processing_time:.1f}s{cost_str}"
            )
            self.status_var.set("SSML conversion completed successfully")

            cost_lines = ""
            input_tokens = result.get('input_tokens', 0)
            output_tokens = result.get('output_tokens', 0)
            if input_tokens or output_tokens:
                cost_lines = (
                    f"Gemini tokens: {input_tokens:,} in / "
                    f"{output_tokens:,} out\n"
                    f"Est. Gemini cost: ${gemini_cost:.4f}\n\n"
                )

            messagebox.showinfo(
                "SSML Conversion Complete",
                f"Content converted to SSML successfully!\n\n"
                f"Processing time: {processing_time:.1f} seconds\n"
                f"{cost_lines}"
                f"You can review and edit the SSML before generating audio.\n"
                f"Use 'Save SSML' to save for later use."
            )
        else:
            error_msg = (result.get('error', 'Unknown error')
                         if result else 'No result returned')
            self._handle_ssml_error(f"SSML conversion failed: {error_msg}")

    def _handle_ssml_error(self, error_msg):
        """Handle SSML conversion error"""
        self.progress_bar.stop()
        self.progress_bar.set(0)
        self.ssml_convert_btn.configure(state="normal", text="Convert to SSML")
        self.ssml_status_label.configure(text="Conversion failed")
        self.status_var.set(f"SSML conversion error: {error_msg}")

        messagebox.showerror(
            "SSML Conversion Failed",
            f"Failed to convert content to SSML:\n\n{error_msg}"
        )

    def save_ssml_file(self):
        """Save SSML content to file"""
        ssml_content = self.ssml_text.get("0.0", "end").strip()
        if not ssml_content:
            messagebox.showwarning("No Content", "No SSML content to save.")
            return

        # Generate default filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"ssml_{timestamp}.xml"

        file_path = filedialog.asksaveasfilename(
            title="Save SSML File",
            defaultextension=".xml",
            initialfile=default_filename,
            initialdir=config.projects_dir,
            filetypes=[
                ("SSML/XML files", "*.xml"),
                ("SSML files", "*.ssml"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ]
        )

        if not file_path:
            return

        try:
            # Prepare metadata header
            metadata = {
                "saved_at": datetime.now().isoformat(),
                "content_type": "ssml",
                "source_processed_file": self.current_processed_file,
                "paper_info": {
                    "title": self.title_text.get("0.0", "end").strip(),
                    "authors": self.authors_var.get(),
                }
            }

            content_with_metadata = (
                f"<!--\nScience2Go SSML Content\n"
                f"{json.dumps(metadata, indent=2)}\n-->\n\n"
                f"{ssml_content}"
            )

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content_with_metadata)

            self.current_ssml_file = file_path
            self.status_var.set(f"SSML saved: {Path(file_path).name}")
            messagebox.showinfo("Saved", f"SSML saved to:\n{file_path}")

        except Exception as e:
            messagebox.showerror("Save Error",
                                 f"Failed to save SSML:\n{str(e)}")

    def load_ssml_file(self):
        """Load SSML content from file"""
        file_path = filedialog.askopenfilename(
            title="Load SSML File",
            initialdir=config.projects_dir,
            filetypes=[
                ("SSML/XML files", "*.xml"),
                ("SSML files", "*.ssml"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ]
        )

        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Strip metadata header if present
            ssml_content = content
            if content.startswith('<!--\nScience2Go SSML Content\n'):
                metadata_end = content.find('-->')
                if metadata_end != -1:
                    ssml_content = content[metadata_end + 3:].strip()

            # Load into SSML editor
            self.ssml_text.delete("0.0", "end")
            self.ssml_text.insert("0.0", ssml_content)

            self.current_ssml_file = file_path
            self.update_ssml_statistics()

            self.status_var.set(f"SSML loaded: {Path(file_path).name}")
            messagebox.showinfo("Loaded",
                                f"SSML loaded from:\n{Path(file_path).name}")

        except Exception as e:
            messagebox.showerror("Load Error",
                                 f"Failed to load SSML:\n{str(e)}")

    def clear_ssml_content(self):
        """Clear SSML editor"""
        self.ssml_text.delete("0.0", "end")
        self.current_ssml_file = None
        self.ssml_stats_var.set("No SSML content")
        self.ssml_status_label.configure(text="")
        self.status_var.set("SSML content cleared")

    def update_ssml_statistics(self):
        """Update SSML character count and chunk estimate"""
        ssml_content = self.ssml_text.get("0.0", "end").strip()

        if not ssml_content:
            self.ssml_stats_var.set("No SSML content")
            return

        char_count = len(ssml_content)
        byte_count = len(ssml_content.encode('utf-8'))

        # Estimate chunks based on MAX_TTS_BYTES (~4500)
        max_bytes = 4500
        estimated_chunks = max(1, (byte_count // max_bytes) + (1 if byte_count % max_bytes else 0))

        # Validate SSML structure
        stripped = ssml_content.strip()
        is_valid = stripped.startswith('<speak>') and stripped.endswith('</speak>')
        validation_status = "✓ Valid SSML structure" if is_valid else "⚠ Missing <speak> wrapper"

        stats_text = (
            f"Characters: {char_count:,} | Bytes: {byte_count:,} | "
            f"Est. chunks: {estimated_chunks} | {validation_status}"
        )
        self.ssml_stats_var.set(stats_text)

    # ══════════════════════════════════════════════
    #  Tab 5: Audio Config Methods
    # ══════════════════════════════════════════════

    def _on_model_changed(self, choice=None):
        """Update voice list and pitch controls when voice model changes."""
        model = self.voice_model_var.get()

        # Update pitch controls (guard against early calls during widget init)
        if hasattr(self, 'pitch_note_label'):
            if model == VOICE_MODEL_NEURAL2:
                self.pitch_note_label.configure(
                    text="Pitch adjustment available for Neural2 voices (-20 to +20 semitones)."
                )
                self.pitch_slider.configure(state="normal")
            else:
                self.pitch_note_label.configure(
                    text="Note: Pitch control is not available for Chirp 3 HD voices."
                )
                self.pitch_slider.configure(state="disabled")
                self.pitch_var.set(0.0)
                self.pitch_label.configure(text="0.0 st")

        # Refresh the voice list for the new model + current gender
        self._on_gender_changed()

    def _on_gender_changed(self, choice=None):
        """Update voice list when gender or model changes."""
        gender = self.voice_gender_var.get()
        model = self.voice_model_var.get()

        if model == VOICE_MODEL_NEURAL2:
            if gender == "Male":
                voice_list = NEURAL2_MALE_VOICES
            else:
                voice_list = NEURAL2_FEMALE_VOICES
        else:
            if gender == "Male":
                voice_list = CHIRP3_HD_MALE_VOICES
            else:
                voice_list = CHIRP3_HD_FEMALE_VOICES

        voices = [voice_display_name(v) for v in voice_list]
        if voices:
            self.voice_name_combo.configure(values=voices)
            self.voice_name_var.set(voices[0])

    def _on_rate_changed(self, value=None):
        """Update rate display label"""
        rate = self.speaking_rate_var.get()
        self.rate_label.configure(text=f"{rate:.2f}x")

    def _on_pitch_changed(self, value=None):
        """Update pitch display label"""
        pitch = self.pitch_var.get()
        self.pitch_label.configure(text=f"{pitch:.1f} st")

    def _get_full_voice_name(self) -> str:
        """Build full voice name from current UI selections."""
        display = self.voice_name_var.get()
        locale = self.voice_locale_var.get()
        model = self.voice_model_var.get()
        return voice_full_name(display, locale, model)

    def _apply_audio_settings(self):
        """Apply current UI settings to the audio generator instance."""
        if audio_generator is None:
            return
        audio_generator.voice_name = self._get_full_voice_name()
        audio_generator.language_code = self.voice_locale_var.get()
        audio_generator.speaking_rate = self.speaking_rate_var.get()
        audio_generator.audio_format = self.audio_format_var.get()
        audio_generator.bitrate = self.bitrate_var.get()
        audio_generator.normalize_audio = self.normalize_var.get()
        audio_generator.pitch_semitones = self.pitch_var.get()

    def preview_voice(self):
        """Generate a short voice preview"""
        if not TTS_AVAILABLE or audio_generator is None:
            messagebox.showerror(
                "Error",
                "Google Cloud TTS is not available.\n"
                "Make sure google-cloud-texttospeech is installed\n"
                "and Google Cloud credentials are configured."
            )
            return

        if not audio_generator.is_ready:
            messagebox.showerror(
                "Error",
                "TTS client not initialized.\n"
                "Check Google Cloud credentials:\n"
                "  export GOOGLE_APPLICATION_CREDENTIALS='/path/to/key.json'\n"
                "  or: gcloud auth application-default login"
            )
            return

        self._apply_audio_settings()

        self.preview_btn.configure(state="disabled", text="Generating...")
        self.preview_status_label.configure(text="Synthesizing preview...")

        def preview_thread():
            sample = (
                "This is a preview of the selected voice. "
                "Science2Go converts academic papers into audio papers, "
                "making research accessible to everyone."
            )
            audio_bytes = audio_generator.preview_voice(sample)

            if audio_bytes:
                # Save to temp file and play
                import tempfile
                tmp = tempfile.NamedTemporaryFile(
                    delete=False, suffix=".mp3"
                )
                tmp.write(audio_bytes)
                tmp.close()
                tmp_path = tmp.name

                self.root.after(0, lambda: self._play_preview(tmp_path))
            else:
                self.root.after(
                    0, lambda: self._preview_error("Failed to generate preview")
                )

        threading.Thread(target=preview_thread, daemon=True).start()

    def _play_preview(self, file_path: str):
        """Play a preview audio file"""
        self.preview_btn.configure(state="normal", text="Preview Voice")
        self.preview_status_label.configure(text="Preview ready!")

        try:
            import subprocess
            if platform.system() == "Darwin":
                subprocess.Popen(["afplay", file_path])
            elif platform.system() == "Windows":
                os.startfile(file_path)
            else:
                subprocess.Popen(["xdg-open", file_path])
        except Exception as e:
            self.preview_status_label.configure(
                text=f"Saved to: {file_path}"
            )
            print(f"Could not auto-play: {e}")

    def _preview_error(self, msg: str):
        """Handle preview generation error"""
        self.preview_btn.configure(state="normal", text="Preview Voice")
        self.preview_status_label.configure(text=msg)
        messagebox.showerror("Preview Error", msg)

    # ══════════════════════════════════════════════
    #  Tab 6: Speech Output Methods
    # ══════════════════════════════════════════════

    def browse_output_path(self):
        """Browse for output file location"""
        fmt = self.audio_format_var.get().lower()
        ext = f".{fmt}"

        # Generate default filename
        title = self.title_text.get("0.0", "end").strip()
        if title:
            # Sanitize title for filename
            safe_title = re.sub(r'[^\w\s-]', '', title)[:60].strip()
            safe_title = re.sub(r'[-\s]+', '_', safe_title)
        else:
            safe_title = "audio_paper"
        timestamp = datetime.now().strftime("%Y%m%d")
        default_name = f"{safe_title}_{timestamp}{ext}"

        file_path = filedialog.asksaveasfilename(
            title="Save Audio File",
            defaultextension=ext,
            initialfile=default_name,
            initialdir=config.audio_dir,
            filetypes=[
                ("MP3 files", "*.mp3"),
                ("M4B audiobook", "*.m4b"),
                ("WAV files", "*.wav"),
                ("OGG files", "*.ogg"),
                ("All files", "*.*"),
            ]
        )
        if file_path:
            self.output_path_var.set(file_path)

    def auto_output_path(self):
        """Auto-generate output path from paper title and settings"""
        fmt = self.audio_format_var.get().lower()
        ext = f".{fmt}"

        title = self.title_text.get("0.0", "end").strip()
        if title:
            safe_title = re.sub(r'[^\w\s-]', '', title)[:60].strip()
            safe_title = re.sub(r'[-\s]+', '_', safe_title)
        else:
            safe_title = "audio_paper"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_title}_{timestamp}{ext}"

        output_path = config.audio_dir / filename
        self.output_path_var.set(str(output_path))

    def generate_audio_paper(self):
        """Generate the audio paper file"""
        if not TTS_AVAILABLE or audio_generator is None:
            messagebox.showerror(
                "Error",
                "Google Cloud TTS is not available.\n"
                "Install with: pip install google-cloud-texttospeech"
            )
            return

        if not audio_generator.is_ready:
            messagebox.showerror(
                "Error",
                "TTS client not initialized.\n"
                "Check Google Cloud credentials."
            )
            return

        # Get content based on source selection
        source = self.content_source_var.get()

        if source == "ssml":
            content = self.ssml_text.get("0.0", "end").strip()
            if not content:
                messagebox.showwarning(
                    "No Content",
                    "No SSML content available.\n"
                    "Convert your processed text to SSML in the MD to SSML tab first,\n"
                    "or select a different content source."
                )
                return
        elif source == "processed":
            content = self.processed_text.get("0.0", "end").strip()
            if not content:
                messagebox.showwarning(
                    "No Content",
                    "No processed content available.\n"
                    "Process your text in the Markdown Processing tab first,\n"
                    "or select a different content source."
                )
                return
        else:  # source == "source"
            self.source_text.configure(state="normal")
            content = self.source_text.get("0.0", "end").strip()
            self.source_text.configure(state="disabled")
            if not content:
                messagebox.showwarning(
                    "No Content",
                    "No source content available.\n"
                    "Load or convert content in the previous tabs."
                )
                return

        # Prepend description if requested
        if self.include_description_var.get():
            desc = self.description_text.get("0.0", "end").strip()
            if desc:
                if is_ssml_content(content):
                    # For SSML content: wrap the description as SSML and insert
                    # inside the existing <speak> wrapper
                    desc_escaped = (desc
                        .replace('&', '&amp;')
                        .replace('<', '&lt;')
                        .replace('>', '&gt;')
                        .replace('"', '&quot;')
                        .replace("'", '&apos;'))
                    desc_ssml = (
                        f'<p><s>{desc_escaped}</s></p>\n'
                        f'<break time="1500ms"/>\n'
                    )
                    content = re.sub(
                        r'(<speak\s*>)',
                        r'\1\n' + desc_ssml,
                        content,
                        count=1,
                    )
                else:
                    content = desc + "\n\n" + content

        # Get output path
        output_path = self.output_path_var.get()
        if not output_path:
            self.auto_output_path()
            output_path = self.output_path_var.get()
        if not output_path:
            messagebox.showwarning(
                "No Output Path",
                "Please select an output file path."
            )
            return

        # Apply audio settings
        self._apply_audio_settings()

        # Get metadata
        title = self.title_text.get("0.0", "end").strip()
        author = self.authors_var.get()
        description = self.description_text.get("0.0", "end").strip()

        # Disable generate button
        self.generate_btn.configure(state="disabled", text="Generating...")
        self.gen_status_label.configure(text="Starting...")
        self.gen_progress.set(0)
        self.open_file_btn.configure(state="disabled")
        self.open_folder_btn.configure(state="disabled")

        def progress_cb(message: str, fraction: float):
            self.root.after(0, lambda m=message, f=fraction: self._update_gen_progress(m, f))

        def generate_thread():
            result = audio_generator.generate_audio(
                text=content,
                output_path=output_path,
                title=title,
                author=author,
                description=description,
                progress_callback=progress_cb,
            )
            self.root.after(0, lambda: self._handle_generation_result(result))

        threading.Thread(target=generate_thread, daemon=True).start()

    def _update_gen_progress(self, message: str, fraction: float):
        """Update generation progress on main thread"""
        self.gen_progress.set(fraction)
        self.gen_progress_label.configure(text=message)
        self.gen_status_label.configure(text=message)

    def _handle_generation_result(self, result: dict):
        """Handle audio generation result on main thread"""
        self.generate_btn.configure(
            state="normal", text="Generate Audio Paper"
        )

        if result.get('success'):
            # Update result fields
            self.gen_duration_var.set(result.get('duration_formatted', '-'))
            self.gen_filesize_var.set(result.get('file_size_formatted', '-'))
            chunks = result.get('total_chunks', 0)
            failed = result.get('failed_chunks', 0)
            self.gen_chunks_var.set(
                f"{chunks} total, {chunks - failed} successful"
                + (f", {failed} failed" if failed else "")
            )
            self.gen_voice_var.set(result.get('voice_used', '-'))
            self.gen_format_var.set(result.get('audio_format', '-'))
            gen_time = result.get('generation_time_seconds', 0)
            self.gen_time_var.set(f"{gen_time:.1f} seconds")

            self.gen_status_label.configure(text="Generation complete!")
            self.gen_progress.set(1.0)
            self.gen_progress_label.configure(
                text=f"Done! {result.get('duration_formatted', '')} audio file generated."
            )

            # Enable playback buttons
            self.open_file_btn.configure(state="normal")
            self.open_folder_btn.configure(state="normal")
            self._last_output_path = result.get('output_path', '')

            tts_cost = result.get('tts_cost', 0)
            tts_chars = result.get('tts_characters', 0)
            cost_str = f" | Est. TTS cost: ${tts_cost:.2f}" if tts_cost else ""

            self.status_var.set(
                f"Audio generated: {result.get('duration_formatted', '')} "
                f"({result.get('file_size_formatted', '')}){cost_str}"
            )

            cost_lines = ""
            if tts_chars:
                cost_lines = (
                    f"TTS characters: {tts_chars:,}\n"
                    f"Est. TTS cost: ${tts_cost:.4f}\n"
                )

            messagebox.showinfo(
                "Generation Complete",
                f"Audio paper generated successfully!\n\n"
                f"Duration: {result.get('duration_formatted', '-')}\n"
                f"File size: {result.get('file_size_formatted', '-')}\n"
                f"Output: {Path(result.get('output_path', '')).name}\n"
                f"Generation time: {gen_time:.1f}s\n"
                f"{cost_lines}"
            )
        else:
            error = result.get('error', 'Unknown error')
            self.gen_status_label.configure(text="Generation failed")
            self.gen_progress.set(0)
            self.gen_progress_label.configure(text=f"Error: {error}")
            self.status_var.set(f"Audio generation failed: {error}")

            messagebox.showerror(
                "Generation Failed",
                f"Failed to generate audio:\n\n{error}"
            )

    def open_output_file(self):
        """Open the generated output file with default application"""
        path = getattr(self, '_last_output_path', '')
        if not path or not Path(path).exists():
            messagebox.showwarning("File Not Found", "Output file not found.")
            return
        try:
            import subprocess
            if platform.system() == "Darwin":
                subprocess.Popen(["open", path])
            elif platform.system() == "Windows":
                os.startfile(path)
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {e}")

    def open_output_folder(self):
        """Open the folder containing the output file"""
        path = getattr(self, '_last_output_path', '')
        if not path:
            path = str(config.audio_dir)
        folder = str(Path(path).parent) if Path(path).exists() else str(config.audio_dir)
        try:
            import subprocess
            if platform.system() == "Darwin":
                subprocess.Popen(["open", folder])
            elif platform.system() == "Windows":
                os.startfile(folder)
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")

    # ══════════════════════════════════════════════
    #  Menu Handlers
    # ══════════════════════════════════════════════

    def new_project(self):
        """Create new project"""
        self.status_var.set("New project created")

    def open_project(self):
        """Open existing project"""
        self.status_var.set("Project opened")

    def save_project(self):
        """Save current project"""
        self.status_var.set("Project saved")

    def show_preferences(self):
        """Show preferences dialog"""
        messagebox.showinfo("Preferences",
                            "Preferences dialog will be implemented here.")

    def test_configuration(self):
        """Test API configuration"""
        messagebox.showinfo("Configuration Test",
                            "Configuration test will be implemented here.")

    def clear_cache(self):
        """Clear application cache"""
        self.status_var.set("Cache cleared")

    def show_about(self):
        """Show about dialog"""
        about_text = (
            "Science2Go v1.0\n\n"
            "Turn Academic Papers into Audio Papers\n\n"
            "Transforms dense academic papers into engaging audio "
            "content optimized for listening.\n\n"
            "Created for researchers and science enthusiasts."
        )
        messagebox.showinfo("About Science2Go", about_text)

    def open_documentation(self):
        """Open documentation"""
        messagebox.showinfo("Documentation",
                            "Documentation will be available online.")

    def on_closing(self):
        """Handle application closing"""
        if messagebox.askokcancel("Quit", "Do you want to quit Science2Go?"):
            self.root.destroy()


def main():
    """Main application entry point (standalone)"""
    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    app = Science2GoApp(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nApplication interrupted")
    except Exception as e:
        messagebox.showerror("Application Error",
                             f"An error occurred:\n{str(e)}")


if __name__ == "__main__":
    main()
