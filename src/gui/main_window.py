"""
Science2Go Main Window - Enhanced with Save/Load for AI-generated content
Added functionality to save and load processed text to avoid re-generation
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
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
    print(f"⚠️ PDF metadata extraction not available: {e}")
    PDF_METADATA_AVAILABLE = False

try:
    from src.processors.text_processor import process_markdown_content
    TEXT_PROCESSOR_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Text processor not available: {e}")
    TEXT_PROCESSOR_AVAILABLE = False

class Science2GoApp:
    """Main Science2Go application with cross-platform GUI"""
    
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
        self.current_processed_file = None  # Track loaded processed file
        
        # PDF extractor
        if PDF_METADATA_AVAILABLE:
            self.pdf_extractor = PDFMetadataExtractor()
        else:
            self.pdf_extractor = None
        
        # Ensure output directories exist
        config.ensure_directories()
        
        print("✅ Science2Go GUI initialized successfully")
    
    def setup_window(self):
        """Configure main window with platform-specific styling"""
        self.root.title("Science2Go - Academic Paper to Podcast Converter")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 600)
        
        # Center window on screen
        self.center_window()
        
        # Configure platform-specific styling
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
        """Create the application menu"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Project", command=self.new_project, accelerator="Cmd+N" if platform.system() == "Darwin" else "Ctrl+N")
        file_menu.add_command(label="Open Project", command=self.open_project, accelerator="Cmd+O" if platform.system() == "Darwin" else "Ctrl+O")
        file_menu.add_command(label="Save Project", command=self.save_project, accelerator="Cmd+S" if platform.system() == "Darwin" else "Ctrl+S")
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
        """Create the main tabbed interface"""
        # Main container with padding
        main_frame = ttk.Frame(self.root)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Configure grid weights
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, sticky="nsew")
        
        # Create all tabs
        self.create_paper_setup_tab()
        self.create_markdown_processing_tab()
        self.create_audio_config_tab()
        self.create_output_generation_tab()
    
    def create_paper_setup_tab(self):
        """Create the Paper Setup tab with working PDF metadata extraction"""
        paper_frame = ttk.Frame(self.notebook)
        self.notebook.add(paper_frame, text="📄 Paper Setup")
        
        # Main container with padding
        container = ttk.Frame(paper_frame)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        
        # Title
        title_label = ttk.Label(container, text="Paper Information & Setup", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(anchor=tk.W, pady=(0, 15))
        
        # PDF Upload Section
        upload_section = ttk.LabelFrame(container, text="📄 PDF Upload", padding=15)
        upload_section.pack(fill=tk.X, pady=(0, 15))
        
        upload_frame = ttk.Frame(upload_section)
        upload_frame.pack(fill=tk.X)
        
        ttk.Label(upload_frame, text="Select your academic paper (PDF):").pack(anchor=tk.W, pady=(0, 5))
        
        pdf_button_frame = ttk.Frame(upload_frame)
        pdf_button_frame.pack(fill=tk.X)
        
        self.pdf_path_var = tk.StringVar()
        pdf_entry = ttk.Entry(pdf_button_frame, textvariable=self.pdf_path_var, state="readonly")
        pdf_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        ttk.Button(pdf_button_frame, text="Browse PDF", 
                  command=self.browse_pdf).pack(side=tk.RIGHT, padx=(0, 5))
        
        # Analyze PDF button
        self.analyze_btn = ttk.Button(pdf_button_frame, text="🔍 Analyze PDF", 
                                     command=self.analyze_pdf, state="disabled")
        self.analyze_btn.pack(side=tk.RIGHT)
        
        # Paper Information Section
        info_section = ttk.LabelFrame(container, text="📋 Paper Information", padding=15)
        info_section.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Create scrollable frame for form fields
        canvas = tk.Canvas(info_section)
        scrollbar = ttk.Scrollbar(info_section, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Form fields
        form_frame = ttk.Frame(scrollable_frame)
        form_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Title field
        ttk.Label(form_frame, text="Title:").grid(row=0, column=0, sticky="nw", padx=(0, 10), pady=5)
        self.title_text = tk.Text(form_frame, height=3, wrap=tk.WORD)
        self.title_text.grid(row=0, column=1, sticky="ew", pady=5)
        form_frame.grid_columnconfigure(1, weight=1)
        
        # Authors field
        ttk.Label(form_frame, text="Authors:").grid(row=1, column=0, sticky="nw", padx=(0, 10), pady=5)
        self.authors_var = tk.StringVar()
        authors_entry = ttk.Entry(form_frame, textvariable=self.authors_var, width=50)
        authors_entry.grid(row=1, column=1, sticky="ew", pady=5)
        
        # Journal field
        ttk.Label(form_frame, text="Journal:").grid(row=2, column=0, sticky="nw", padx=(0, 10), pady=5)
        self.journal_var = tk.StringVar()
        journal_entry = ttk.Entry(form_frame, textvariable=self.journal_var, width=50)
        journal_entry.grid(row=2, column=1, sticky="ew", pady=5)
        
        # Year field
        ttk.Label(form_frame, text="Year:").grid(row=3, column=0, sticky="nw", padx=(0, 10), pady=5)
        self.year_var = tk.StringVar()
        year_entry = ttk.Entry(form_frame, textvariable=self.year_var, width=20)
        year_entry.grid(row=3, column=1, sticky="w", pady=5)
        
        # DOI field
        ttk.Label(form_frame, text="DOI:").grid(row=4, column=0, sticky="nw", padx=(0, 10), pady=5)
        self.doi_var = tk.StringVar()
        doi_entry = ttk.Entry(form_frame, textvariable=self.doi_var, width=50)
        doi_entry.grid(row=4, column=1, sticky="ew", pady=5)
        
        # Abstract field
        ttk.Label(form_frame, text="Abstract:").grid(row=5, column=0, sticky="nw", padx=(0, 10), pady=5)
        self.abstract_text = tk.Text(form_frame, height=6, wrap=tk.WORD)
        self.abstract_text.grid(row=5, column=1, sticky="ew", pady=5)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Generate Description Button
        description_frame = ttk.Frame(container)
        description_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(description_frame, text="Generate Podcast Description", 
                  command=self.generate_description).pack(side=tk.RIGHT)
        
        # Description Preview
        description_section = ttk.LabelFrame(container, text="Generated Podcast Description", padding=10)
        description_section.pack(fill=tk.X)
        
        self.description_text = tk.Text(description_section, height=6, wrap=tk.WORD, state="disabled")
        self.description_text.pack(fill=tk.X)
    
    def create_markdown_processing_tab(self):
        """Create the Markdown Processing tab with AI integration and Save/Load functionality"""
        markdown_frame = ttk.Frame(self.notebook)
        self.notebook.add(markdown_frame, text="📝 Markdown Processing")
        
        # Main container with padding
        container = ttk.Frame(markdown_frame)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        
        # Title and Action buttons at the TOP
        title_and_buttons_frame = ttk.Frame(container)
        title_and_buttons_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Title on the left
        title_label = ttk.Label(title_and_buttons_frame, text="Markdown Content Processing", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(side=tk.LEFT, anchor=tk.W)
        
        # Buttons on the right - ENHANCED with Save/Load
        button_frame = ttk.Frame(title_and_buttons_frame)
        button_frame.pack(side=tk.RIGHT)
        
        # File operations
        ttk.Button(button_frame, text="Load Processed", 
                  command=self.load_processed_text).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Save Processed", 
                  command=self.save_processed_text).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Separator
        ttk.Separator(button_frame, orient='vertical').pack(side=tk.RIGHT, fill='y', padx=5)
        
        # Processing operations
        ttk.Button(button_frame, text="Process with AI", 
                  command=self.process_markdown_ai).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Clear Content", 
                  command=self.clear_markdown_content).pack(side=tk.RIGHT)
        
        # Markdown File Input Section
        file_section = ttk.LabelFrame(container, text="Markdown File Input", padding=15)
        file_section.pack(fill=tk.X, pady=(0, 15))
        
        file_frame = ttk.Frame(file_section)
        file_frame.pack(fill=tk.X)
        
        ttk.Label(file_frame, text="Select markdown file (.md or .txt) with your paper content:").pack(anchor=tk.W, pady=(0, 5))
        
        file_button_frame = ttk.Frame(file_frame)
        file_button_frame.pack(fill=tk.X)
        
        self.markdown_path_var = tk.StringVar()
        markdown_entry = ttk.Entry(file_button_frame, textvariable=self.markdown_path_var, state="readonly")
        markdown_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        ttk.Button(file_button_frame, text="Browse", 
                  command=self.browse_markdown_file).pack(side=tk.RIGHT)
        
        # Template Selection Section
        template_section = ttk.LabelFrame(container, text="Processing Template", padding=15)
        template_section.pack(fill=tk.X, pady=(0, 15))
        
        template_frame = ttk.Frame(template_section)
        template_frame.pack(fill=tk.X)
        
        ttk.Label(template_frame, text="Choose processing template for AI optimization:").pack(anchor=tk.W, pady=(0, 5))
        
        template_button_frame = ttk.Frame(template_frame)
        template_button_frame.pack(fill=tk.X)
        
        self.template_var = tk.StringVar(value="Review Papers")
        template_combo = ttk.Combobox(template_button_frame, textvariable=self.template_var, 
                                     values=["Review Papers", "Technical Papers", "Custom Template"],
                                     state="readonly", width=25)
        template_combo.pack(side=tk.LEFT)
        template_combo.bind('<<ComboboxSelected>>', self.on_template_changed)
        
        # Template description
        self.template_desc_var = tk.StringVar()
        desc_label = ttk.Label(template_button_frame, textvariable=self.template_desc_var, 
                              font=('Arial', 9, 'italic'))
        desc_label.pack(side=tk.LEFT, padx=(15, 0))
        
        # Content Processing Area
        content_section = ttk.LabelFrame(container, text="Content Processing", padding=10)
        content_section.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Create notebook for content tabs
        self.content_notebook = ttk.Notebook(content_section)
        self.content_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Source Content Tab
        source_frame = ttk.Frame(self.content_notebook)
        self.content_notebook.add(source_frame, text="📄 Source Content")
        
        self.source_text = scrolledtext.ScrolledText(source_frame, wrap=tk.WORD, 
                                                   font=('Consolas', 10), state="disabled")
        self.source_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # AI Processed Tab
        processed_frame = ttk.Frame(self.content_notebook)
        self.content_notebook.add(processed_frame, text="🤖 AI Processed")
        
        self.processed_text = scrolledtext.ScrolledText(processed_frame, wrap=tk.WORD, 
                                                      font=('Consolas', 10))
        self.processed_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Statistics and File Info Section
        stats_section = ttk.Frame(container)
        stats_section.pack(fill=tk.X)
        
        # Content statistics
        self.content_stats_var = tk.StringVar(value="No content loaded")
        stats_label = ttk.Label(stats_section, textvariable=self.content_stats_var)
        stats_label.pack(side=tk.LEFT)
        
        # File info
        self.file_info_var = tk.StringVar(value="")
        file_info_label = ttk.Label(stats_section, textvariable=self.file_info_var, 
                                   font=('Arial', 9, 'italic'))
        file_info_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # Processing status
        self.processing_status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(stats_section, textvariable=self.processing_status_var)
        status_label.pack(side=tk.RIGHT)
        
        # Set initial template description
        self.update_template_description()
    
    def create_audio_config_tab(self):
        """Create the Audio Configuration tab"""
        audio_frame = ttk.Frame(self.notebook)
        self.notebook.add(audio_frame, text="🎙️ Audio Config")
        
        # Placeholder content  
        container = ttk.Frame(audio_frame)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        
        title_label = ttk.Label(container, text="Audio Generation Settings", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(anchor=tk.W, pady=(0, 15))
        
        ttk.Label(container, text="This tab will be implemented for audio settings. Features include:", 
                 font=('Arial', 11)).pack(anchor=tk.W, pady=(0, 10))
        
        # Feature list
        features = [
            "• Voice selection and customization",
            "• Speech rate and pitch adjustment",
            "• Audio quality settings",
            "• Preview and test voice settings",
            "• Export format configuration"
        ]
        
        for feature in features:
            ttk.Label(container, text=feature, 
                     font=('Arial', 10)).pack(anchor=tk.W, pady=2)
    
    def create_output_generation_tab(self):
        """Create the Output Generation tab"""
        output_frame = ttk.Frame(self.notebook)
        self.notebook.add(output_frame, text="🎧 Output Generation")
        
        # Placeholder content
        container = ttk.Frame(output_frame)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        
        title_label = ttk.Label(container, text="Podcast Output Generation", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(anchor=tk.W, pady=(0, 15))
        
        ttk.Label(container, text="This tab will be implemented for final podcast creation:", 
                 font=('Arial', 11)).pack(anchor=tk.W, pady=(0, 10))
        
        # Feature list
        features = [
            "• Combine description and processed content",
            "• Generate high-quality audio files",
            "• Add chapter markers and metadata",
            "• Preview generated podcasts",
            "• Export in various formats"
        ]
        
        for feature in features:
            ttk.Label(container, text=feature, 
                     font=('Arial', 10)).pack(anchor=tk.W, pady=2)
    
    def setup_status_bar(self):
        """Create the status bar"""
        status_frame = ttk.Frame(self.root)
        status_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.pack(side=tk.LEFT)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, length=200)
        self.progress_bar.pack(side=tk.RIGHT, padx=(10, 0))
    
    # Paper Setup Tab Methods (unchanged)
    def browse_pdf(self):
        """Browse for PDF file"""
        file_path = filedialog.askopenfilename(
            title="Select Academic Paper",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if file_path:
            self.pdf_path_var.set(file_path)
            self.analyze_btn.config(state="normal")
            self.status_var.set(f"PDF selected: {Path(file_path).name}")
    
    def analyze_pdf(self):
        """Analyze PDF file for metadata"""
        pdf_path = self.pdf_path_var.get()
        if not pdf_path or not PDF_METADATA_AVAILABLE:
            messagebox.showerror("Error", "PDF analysis not available")
            return
        
        # Disable button during analysis
        self.analyze_btn.config(state="disabled", text="📄 Analyzing...")
        self.status_var.set("Analyzing PDF...")
        self.progress_bar.config(mode='indeterminate')
        self.progress_bar.start()
        
        def analyze_thread():
            try:
                # Extract metadata
                metadata = self.pdf_extractor.extract_metadata(pdf_path)
                
                # Update UI in main thread
                self.root.after(0, lambda: self.handle_pdf_analysis_complete(metadata))
                
            except Exception as e:
                self.root.after(0, lambda: self.handle_pdf_analysis_error(str(e)))
        
        # Start analysis in background thread
        threading.Thread(target=analyze_thread, daemon=True).start()
    
    def handle_pdf_analysis_complete(self, metadata):
        """Handle PDF analysis completion"""
        # Stop progress animation
        self.progress_bar.stop()
        self.progress_bar.config(mode='determinate', value=0)
        self.analyze_btn.config(state="normal", text="🔍 Analyze PDF")
        
        if metadata.get('success', False):
            # Store metadata for later use
            self.pdf_metadata = metadata
            
            # Populate form fields
            if metadata.get('title'):
                self.title_text.delete(1.0, tk.END)
                self.title_text.insert(1.0, metadata['title'])
            
            if metadata.get('authors'):
                self.authors_var.set(metadata['authors'])
            
            if metadata.get('journal'):
                self.journal_var.set(metadata['journal'])
            
            if metadata.get('year'):
                self.year_var.set(metadata['year'])
            
            if metadata.get('doi'):
                self.doi_var.set(metadata['doi'])
            
            if metadata.get('abstract'):
                self.abstract_text.delete(1.0, tk.END)
                self.abstract_text.insert(1.0, metadata['abstract'])
            
            # Update status
            method = metadata.get('extraction_method', 'Unknown')
            self.status_var.set(f"Metadata extracted via {method}")
            
            # Show success message with license info if available
            success_msg = f"Paper metadata extracted successfully!\n\nMethod: {method}\nTitle: {metadata['title'][:50]}{'...' if len(metadata['title']) > 50 else ''}"
            if metadata.get('license'):
                success_msg += f"\nLicense: {metadata['license']}"
            
            messagebox.showinfo("Success", success_msg)
        else:
            error = metadata.get('error', 'Unknown error')
            self.handle_pdf_analysis_error(error)
    
    def handle_pdf_analysis_error(self, error_msg):
        """Handle PDF analysis error"""
        self.progress_bar.stop()
        self.progress_bar.config(mode='determinate', value=0)
        self.analyze_btn.config(state="normal", text="🔍 Analyze PDF")
        
        self.status_var.set(f"Analysis failed: {error_msg}")
        messagebox.showerror("Analysis Failed", 
                           f"Failed to extract metadata from PDF:\n\n{error_msg}\n\n"
                           f"You can still fill in the paper information manually.")
    
    def generate_description(self):
        """Generate podcast description (not intro)"""
        title = self.title_text.get(1.0, tk.END).strip()
        authors = self.authors_var.get().strip()
        journal = self.journal_var.get().strip()
        year = self.year_var.get().strip()
        doi = self.doi_var.get().strip()
        
        if not title:
            messagebox.showwarning("Missing Information", "Please enter a paper title first.")
            return
        
        # Generate podcast description
        description_parts = []
        
        # Main description
        description_parts.append(f"This is an audio version of the paper \"{title}\"")
        
        if authors:
            description_parts.append(f" by {authors}")
        
        if year and journal:
            description_parts.append(f", published {year} in {journal}")
        elif journal:
            description_parts.append(f", published in {journal}")
        elif year:
            description_parts.append(f", published in {year}")
        
        description_parts.append(".")
        
        # Paper availability
        if doi:
            description_parts.append(f"\n\nThe original paper can be found at: https://doi.org/{doi}")
        
        # License information (if available from metadata)
        if hasattr(self, 'pdf_metadata') and self.pdf_metadata.get('license'):
            license_info = self.pdf_metadata['license']
            description_parts.append(f"\n\nThe original work is published under {license_info}.")
            if 'creativecommons.org' in license_info.lower():
                description_parts.append(" For license details, visit: https://creativecommons.org/licenses/")
        
        # Derivative work notice
        description_parts.append("\n\nThis audio version is a derivative work created for accessibility and educational purposes. It preserves the original scientific content while optimizing the text for audio consumption.")
        
        # Footer
        description_parts.append("\n\nGenerated by Science2Go - Academic Paper to Podcast Converter")
        description_parts.append("\nhttps://github.com/biterik/science2go")
        
        description_text = "".join(description_parts)
        
        # Display in description preview
        self.description_text.config(state="normal")
        self.description_text.delete(1.0, tk.END)
        self.description_text.insert(1.0, description_text)
        self.description_text.config(state="disabled")
        
        self.status_var.set("Podcast description generated")
    
    # ENHANCED Markdown Processing Tab Methods with Save/Load
    def browse_markdown_file(self):
        """Browse for markdown file"""
        file_path = filedialog.askopenfilename(
            title="Select Markdown File",
            filetypes=[("Markdown files", "*.md"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            self.markdown_path_var.set(file_path)
            self.load_markdown_content(file_path)
    
    def load_markdown_content(self, file_path):
        """Load markdown content from file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Display in source tab
            self.source_text.config(state="normal")
            self.source_text.delete(1.0, tk.END)
            self.source_text.insert(1.0, content)
            self.source_text.config(state="disabled")
            
            # Update statistics and file info
            self.update_content_statistics()
            self.update_file_info()
            
            self.status_var.set(f"Loaded: {Path(file_path).name}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load markdown file:\n{str(e)}")
    
    def save_processed_text(self):
        """Save AI-processed text to file"""
        processed_content = self.processed_text.get(1.0, tk.END).strip()
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
                ("All files", "*.*")
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
                    "title": self.title_text.get(1.0, tk.END).strip() if hasattr(self, 'title_text') else "",
                    "authors": self.authors_var.get() if hasattr(self, 'authors_var') else "",
                    "journal": self.journal_var.get() if hasattr(self, 'journal_var') else "",
                    "year": self.year_var.get() if hasattr(self, 'year_var') else "",
                    "doi": self.doi_var.get() if hasattr(self, 'doi_var') else ""
                }
            }
            
            # Create the content with metadata header
            content_with_metadata = f"""<!--
Science2Go Processed Content
{json.dumps(metadata, indent=2)}
-->

{processed_content}"""
            
            # Save the file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content_with_metadata)
            
            # Update current file tracking
            self.current_processed_file = file_path
            self.update_file_info()
            
            self.status_var.set(f"Processed content saved: {Path(file_path).name}")
            messagebox.showinfo("Saved", f"Processed content saved to:\n{file_path}")
            
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save processed content:\n{str(e)}")
    
    def load_processed_text(self):
        """Load previously saved processed text"""
        file_path = filedialog.askopenfilename(
            title="Load Processed Text",
            initialdir=config.projects_dir,
            filetypes=[
                ("Markdown files", "*.md"),
                ("Text files", "*.txt"),
                ("All files", "*.*")
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
                    # Extract metadata from comment
                    metadata_end = content.find('-->')
                    if metadata_end != -1:
                        metadata_section = content[content.find('{\n'):metadata_end]
                        metadata = json.loads(metadata_section)
                        processed_content = content[metadata_end + 3:].strip()
                except (json.JSONDecodeError, ValueError):
                    # If metadata parsing fails, just use the whole content
                    pass
            
            # Load content into processed text area
            self.processed_text.delete(1.0, tk.END)
            self.processed_text.insert(1.0, processed_content)
            
            # Switch to processed tab
            self.content_notebook.select(1)
            
            # Update template if metadata available
            if metadata and metadata.get('template_used'):
                template_used = metadata['template_used']
                if template_used in ["Review Papers", "Technical Papers", "Custom Template"]:
                    self.template_var.set(template_used)
                    self.update_template_description()
            
            # Track current file
            self.current_processed_file = file_path
            
            # Update statistics and file info
            self.update_content_statistics()
            self.update_file_info()
            
            # Update status
            self.processing_status_var.set("✅ Loaded from file")
            self.status_var.set(f"Processed content loaded: {Path(file_path).name}")
            
            # Show info about loaded content
            info_msg = f"Loaded processed content from:\n{Path(file_path).name}"
            if metadata:
                if metadata.get('generated_at'):
                    info_msg += f"\n\nGenerated: {metadata['generated_at'][:16]}"
                if metadata.get('template_used'):
                    info_msg += f"\nTemplate: {metadata['template_used']}"
                if metadata.get('paper_info', {}).get('title'):
                    title = metadata['paper_info']['title'][:50]
                    info_msg += f"\nPaper: {title}{'...' if len(metadata['paper_info']['title']) > 50 else ''}"
            
            messagebox.showinfo("Loaded", info_msg)
            
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load processed content:\n{str(e)}")
    
    def get_processing_stats(self):
        """Get current processing statistics"""
        source_content = self.source_text.get(1.0, tk.END).strip()
        processed_content = self.processed_text.get(1.0, tk.END).strip()
        
        stats = {
            "source_words": len(source_content.split()) if source_content else 0,
            "source_chars": len(source_content),
            "processed_words": len(processed_content.split()) if processed_content else 0,
            "processed_chars": len(processed_content)
        }
        
        if source_content and processed_content:
            stats["reduction_percentage"] = ((stats["source_chars"] - stats["processed_chars"]) / stats["source_chars"]) * 100
        
        return stats
    
    def update_file_info(self):
        """Update file information display"""
        info_parts = []
        
        # Current processed file info
        if self.current_processed_file:
            filename = Path(self.current_processed_file).name
            info_parts.append(f"Processed file: {filename}")
        
        # Source file info
        source_file = self.markdown_path_var.get()
        if source_file:
            filename = Path(source_file).name
            info_parts.append(f"Source: {filename}")
        
        self.file_info_var.set(" | ".join(info_parts))
    
    def on_template_changed(self, event=None):
        """Handle template selection change"""
        self.update_template_description()
    
    def update_template_description(self):
        """Update template description based on selection"""
        template = self.template_var.get()
        descriptions = {
            "Review Papers": "Optimized for comprehensive review articles and surveys",
            "Technical Papers": "Optimized for technical research papers and studies", 
            "Custom Template": "Customizable template for specific processing needs"
        }
        
        desc = descriptions.get(template, "")
        self.template_desc_var.set(desc)
    
    def process_markdown_ai(self):
        """Process markdown content with Gemini AI"""
        if not TEXT_PROCESSOR_AVAILABLE:
            messagebox.showerror("Error", "Text processor not available. Please check Gemini AI configuration.")
            return
        
        # Check if we have content
        source_content = self.source_text.get(1.0, tk.END).strip()
        if not source_content:
            messagebox.showwarning("No Content", "Please load a markdown file first.")
            return
        
        # Check content length (Gemini has limits)
        if len(source_content) > 1000000:  # 1MB limit
            if not messagebox.askyesno("Large Content", 
                                     f"Content is quite large ({len(source_content):,} chars). "
                                     "This may take several minutes to process. Continue?"):
                return
        
        # Clear current processed file tracking since we're generating new content
        self.current_processed_file = None
        
        # Start processing
        self.processing_status_var.set("🔄 Processing with Gemini AI...")
        self.progress_bar.config(mode='indeterminate')
        self.progress_bar.start()
        
        def process_thread():
            try:
                # Get selected template
                template_name = self.template_var.get()
                
                # Process content with Gemini
                result = process_markdown_content(source_content, template_name)
                
                # Update UI from main thread
                self.root.after(0, lambda: self.handle_ai_processing_result(result))
                
            except Exception as e:
                error_msg = f"AI processing failed: {str(e)}"
                self.root.after(0, lambda: self.handle_ai_processing_error(error_msg))
        
        # Start processing in background thread
        threading.Thread(target=process_thread, daemon=True).start()
    
    def handle_ai_processing_result(self, result):
        """Handle AI processing results"""
        try:
            # Stop progress animation
            self.progress_bar.stop()
            self.progress_bar.config(mode='determinate', value=0)
            
            if result and result.get('success', False):
                # Update processed content
                processed_content = result.get('processed_content', '')
                self.processed_text.delete(1.0, tk.END)
                self.processed_text.insert(1.0, processed_content)
                
                # Switch to processed tab
                self.content_notebook.select(1)
                
                # Update statistics
                self.update_content_statistics()
                self.update_file_info()
                
                # Update status
                processing_time = result.get('processing_time', 0)
                reduction = result.get('reduction_percentage', 0)
                
                self.processing_status_var.set(f"✅ Processed successfully ({processing_time:.1f}s, {reduction:.1f}% reduction)")
                self.status_var.set("AI processing completed successfully")
                
                # Show success message
                messagebox.showinfo("Success", 
                                  f"Content processed successfully!\n\n"
                                  f"Processing time: {processing_time:.1f} seconds\n"
                                  f"Content reduction: {reduction:.1f}%\n"
                                  f"You can now review and edit the processed content.\n\n"
                                  f"💡 Tip: Use 'Save Processed' to save this content for later use.")
                
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'No result returned'
                self.handle_ai_processing_error(f"Processing failed: {error_msg}")
                
        except Exception as e:
            self.handle_ai_processing_error(f"Error handling results: {str(e)}")
    
    def handle_ai_processing_error(self, error_msg):
        """Handle AI processing error"""
        self.progress_bar.stop()
        self.progress_bar.config(mode='determinate', value=0)
        
        self.processing_status_var.set(f"❌ Processing failed")
        self.status_var.set(f"AI processing error: {error_msg}")
        
        messagebox.showerror("Processing Failed", f"Failed to process content with Gemini AI:\n\n{error_msg}")
    
    def clear_markdown_content(self):
        """Clear all markdown content"""
        # Clear source content
        self.source_text.config(state="normal")
        self.source_text.delete(1.0, tk.END)
        self.source_text.config(state="disabled")
        
        # Clear processed content
        self.processed_text.delete(1.0, tk.END)
        
        # Clear file paths and tracking
        self.markdown_path_var.set("")
        self.current_processed_file = None
        
        # Reset statistics and file info
        self.content_stats_var.set("No content loaded")
        self.file_info_var.set("")
        self.processing_status_var.set("Ready")
        
        # Switch back to source tab
        self.content_notebook.select(0)
        
        self.status_var.set("Content cleared")
    
    def update_content_statistics(self):
        """Update content statistics"""
        source_content = self.source_text.get(1.0, tk.END).strip()
        processed_content = self.processed_text.get(1.0, tk.END).strip()
        
        source_words = len(source_content.split()) if source_content else 0
        source_chars = len(source_content)
        
        processed_words = len(processed_content.split()) if processed_content else 0
        processed_chars = len(processed_content)
        
        if processed_content and source_content:
            reduction = ((source_chars - processed_chars) / source_chars) * 100 if source_chars > 0 else 0
            stats_text = (f"📊 Source: {source_words:,} words, {source_chars:,} chars | "
                         f"Processed: {processed_words:,} words, {processed_chars:,} chars | "
                         f"Reduction: {reduction:.1f}%")
        elif source_content:
            stats_text = f"📊 Source: {source_words:,} words, {source_chars:,} chars | Ready for processing"
        else:
            stats_text = "No content loaded"
        
        self.content_stats_var.set(stats_text)
    
    # Menu handlers (unchanged)
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
        messagebox.showinfo("Preferences", "Preferences dialog will be implemented here.")
    
    def test_configuration(self):
        """Test API configuration"""
        messagebox.showinfo("Configuration Test", "Configuration test will be implemented here.")
    
    def clear_cache(self):
        """Clear application cache"""
        self.status_var.set("Cache cleared")
    
    def show_about(self):
        """Show about dialog"""
        about_text = """Science2Go v1.0
        
Academic Paper to Podcast Converter

Transforms dense academic papers into engaging audio content optimized for listening.

Created with ❤️ for researchers and science enthusiasts."""
        
        messagebox.showinfo("About Science2Go", about_text)
    
    def open_documentation(self):
        """Open documentation"""
        messagebox.showinfo("Documentation", "Documentation will be available online.")
    
    def on_closing(self):
        """Handle application closing"""
        if messagebox.askokcancel("Quit", "Do you want to quit Science2Go?"):
            self.root.destroy()

def main():
    """Main application entry point"""
    root = tk.Tk()
    app = Science2GoApp(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\n🛑 Application interrupted")
    except Exception as e:
        messagebox.showerror("Application Error", f"An error occurred:\n{str(e)}")

if __name__ == "__main__":
    main()