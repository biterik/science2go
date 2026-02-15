"""
Advanced Text Editor Manager for Science2Go
Handles editing, saving, loading, and management of AI-generated texts
"""

import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import hashlib

class TextDocument:
    """Represents a text document with metadata"""
    
    def __init__(self, content: str = "", title: str = "", template_used: str = "", 
                 source_file: str = "", processing_stats: Dict = None):
        self.content = content
        self.title = title
        self.template_used = template_used
        self.source_file = source_file
        self.processing_stats = processing_stats or {}
        self.created_at = datetime.now().isoformat()
        self.modified_at = self.created_at
        self.word_count = len(content.split()) if content else 0
        self.char_count = len(content)
        self.document_id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Generate unique document ID"""
        content_hash = hashlib.md5(f"{self.title}{self.created_at}".encode()).hexdigest()
        return content_hash[:12]
    
    def update_content(self, new_content: str):
        """Update document content and metadata"""
        self.content = new_content
        self.modified_at = datetime.now().isoformat()
        self.word_count = len(new_content.split()) if new_content else 0
        self.char_count = len(new_content)
    
    def to_dict(self) -> Dict:
        """Convert document to dictionary for serialization"""
        return {
            'document_id': self.document_id,
            'content': self.content,
            'title': self.title,
            'template_used': self.template_used,
            'source_file': self.source_file,
            'processing_stats': self.processing_stats,
            'created_at': self.created_at,
            'modified_at': self.modified_at,
            'word_count': self.word_count,
            'char_count': self.char_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TextDocument':
        """Create document from dictionary"""
        doc = cls(
            content=data.get('content', ''),
            title=data.get('title', ''),
            template_used=data.get('template_used', ''),
            source_file=data.get('source_file', ''),
            processing_stats=data.get('processing_stats', {})
        )
        doc.document_id = data.get('document_id', doc.document_id)
        doc.created_at = data.get('created_at', doc.created_at)
        doc.modified_at = data.get('modified_at', doc.modified_at)
        doc.word_count = data.get('word_count', doc.word_count)
        doc.char_count = data.get('char_count', doc.char_count)
        return doc

class DocumentLibrary:
    """Manages a library of saved documents"""
    
    def __init__(self, library_path: str = "output/document_library"):
        self.library_path = Path(library_path)
        self.library_path.mkdir(parents=True, exist_ok=True)
        self.index_file = self.library_path / "library_index.json"
        self.documents: Dict[str, TextDocument] = {}
        self.load_library()
    
    def load_library(self):
        """Load document library from disk"""
        try:
            if self.index_file.exists():
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                    
                for doc_data in index_data.get('documents', []):
                    doc = TextDocument.from_dict(doc_data)
                    self.documents[doc.document_id] = doc
                    
                print(f"📚 Loaded {len(self.documents)} documents from library")
            else:
                print("📚 Created new document library")
                self.save_index()
                
        except Exception as e:
            print(f"⚠️ Error loading document library: {e}")
            self.documents = {}
    
    def save_index(self):
        """Save document library index to disk"""
        try:
            index_data = {
                'version': '1.0',
                'last_updated': datetime.now().isoformat(),
                'document_count': len(self.documents),
                'documents': [doc.to_dict() for doc in self.documents.values()]
            }
            
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"❌ Error saving document library: {e}")
    
    def add_document(self, document: TextDocument) -> str:
        """Add document to library"""
        self.documents[document.document_id] = document
        self.save_index()
        return document.document_id
    
    def update_document(self, document: TextDocument):
        """Update existing document"""
        if document.document_id in self.documents:
            self.documents[document.document_id] = document
            self.save_index()
    
    def delete_document(self, document_id: str) -> bool:
        """Delete document from library"""
        if document_id in self.documents:
            del self.documents[document_id]
            self.save_index()
            return True
        return False
    
    def get_document(self, document_id: str) -> Optional[TextDocument]:
        """Get document by ID"""
        return self.documents.get(document_id)
    
    def list_documents(self) -> List[TextDocument]:
        """Get list of all documents sorted by modification date"""
        docs = list(self.documents.values())
        docs.sort(key=lambda d: d.modified_at, reverse=True)
        return docs
    
    def search_documents(self, query: str) -> List[TextDocument]:
        """Search documents by title or content"""
        query_lower = query.lower()
        results = []
        
        for doc in self.documents.values():
            if (query_lower in doc.title.lower() or 
                query_lower in doc.content.lower()[:1000]):  # Search first 1000 chars
                results.append(doc)
        
        results.sort(key=lambda d: d.modified_at, reverse=True)
        return results

class TextEditorManager:
    """Advanced text editor with full document management"""
    
    def __init__(self, parent_widget, update_statistics_callback=None):
        self.parent = parent_widget
        self.update_statistics_callback = update_statistics_callback
        self.library = DocumentLibrary()
        self.current_document: Optional[TextDocument] = None
        self.unsaved_changes = False
        
        # Text change tracking
        self.last_saved_content = ""
        
    def create_editor_interface(self, text_widget) -> tk.Frame:
        """Create the editor interface with toolbar"""
        # Main editor frame
        editor_frame = tk.Frame(self.parent)
        
        # Toolbar
        toolbar = tk.Frame(editor_frame, bg='#f0f0f0', height=40)
        toolbar.pack(fill='x', padx=2, pady=2)
        toolbar.pack_propagate(False)
        
        # File operations
        file_frame = tk.LabelFrame(toolbar, text="📁 Document", bg='#f0f0f0')
        file_frame.pack(side='left', fill='y', padx=5)
        
        tk.Button(file_frame, text="💾 Save", command=self.save_document,
                 bg='#4CAF50', fg='white', relief='flat', padx=8).pack(side='left', padx=2)
        
        tk.Button(file_frame, text="💾+ Save As", command=self.save_document_as,
                 bg='#2196F3', fg='white', relief='flat', padx=8).pack(side='left', padx=2)
        
        tk.Button(file_frame, text="📂 Load", command=self.load_document,
                 bg='#FF9800', fg='white', relief='flat', padx=8).pack(side='left', padx=2)
        
        tk.Button(file_frame, text="📋 New", command=self.new_document,
                 bg='#9C27B0', fg='white', relief='flat', padx=8).pack(side='left', padx=2)
        
        # Library operations
        library_frame = tk.LabelFrame(toolbar, text="📚 Library", bg='#f0f0f0')
        library_frame.pack(side='left', fill='y', padx=5)
        
        tk.Button(library_frame, text="📚 Browse", command=self.browse_library,
                 bg='#607D8B', fg='white', relief='flat', padx=8).pack(side='left', padx=2)
        
        tk.Button(library_frame, text="🔍 Search", command=self.search_library,
                 bg='#795548', fg='white', relief='flat', padx=8).pack(side='left', padx=2)
        
        # Export operations
        export_frame = tk.LabelFrame(toolbar, text="📤 Export", bg='#f0f0f0')
        export_frame.pack(side='left', fill='y', padx=5)
        
        tk.Button(export_frame, text="📝 TXT", command=lambda: self.export_document('txt'),
                 bg='#4CAF50', fg='white', relief='flat', padx=6).pack(side='left', padx=1)
        
        tk.Button(export_frame, text="📄 MD", command=lambda: self.export_document('md'),
                 bg='#2196F3', fg='white', relief='flat', padx=6).pack(side='left', padx=1)
        
        tk.Button(export_frame, text="📊 JSON", command=lambda: self.export_document('json'),
                 bg='#FF9800', fg='white', relief='flat', padx=6).pack(side='left', padx=1)
        
        # Document info
        info_frame = tk.LabelFrame(toolbar, text="📋 Info", bg='#f0f0f0')
        info_frame.pack(side='right', fill='y', padx=5)
        
        self.doc_info_label = tk.Label(info_frame, text="No document", 
                                      bg='#f0f0f0', fg='#666')
        self.doc_info_label.pack(side='right', padx=5)
        
        # Status indicator
        self.status_label = tk.Label(toolbar, text="Ready", bg='#4CAF50', fg='white', 
                                    relief='flat', padx=10)
        self.status_label.pack(side='right', padx=5)
        
        # Text widget setup
        self.text_widget = text_widget
        self.setup_text_change_tracking()
        
        return editor_frame
    
    def setup_text_change_tracking(self):
        """Setup automatic change tracking for the text widget"""
        def on_text_change(event=None):
            if self.current_document:
                current_content = self.text_widget.get(1.0, tk.END).strip()
                if current_content != self.last_saved_content:
                    self.unsaved_changes = True
                    self.update_status("Modified", "#FF9800")
                    self.update_document_info()
                else:
                    self.unsaved_changes = False
                    self.update_status("Saved", "#4CAF50")
                
                # Update statistics if callback provided
                if self.update_statistics_callback:
                    self.update_statistics_callback()
        
        # Bind change events
        self.text_widget.bind('<KeyRelease>', on_text_change)
        self.text_widget.bind('<Button-1>', on_text_change)
        self.text_widget.bind('<ButtonRelease-1>', on_text_change)
    
    def new_document(self):
        """Create a new document"""
        if self.check_unsaved_changes():
            return
        
        title = simpledialog.askstring("New Document", "Enter document title:")
        if title:
            self.current_document = TextDocument(title=title)
            self.text_widget.delete(1.0, tk.END)
            self.last_saved_content = ""
            self.unsaved_changes = False
            self.update_document_info()
            self.update_status("New document created", "#4CAF50")
    
    def save_document(self):
        """Save the current document"""
        if not self.current_document:
            self.save_document_as()
            return
        
        content = self.text_widget.get(1.0, tk.END).strip()
        self.current_document.update_content(content)
        
        # Save to library
        self.library.update_document(self.current_document)
        self.last_saved_content = content
        self.unsaved_changes = False
        
        self.update_document_info()
        self.update_status("Saved to library", "#4CAF50")
    
    def save_document_as(self):
        """Save document with new title"""
        content = self.text_widget.get(1.0, tk.END).strip()
        if not content:
            messagebox.showwarning("Empty Document", "Cannot save empty document.")
            return
        
        title = simpledialog.askstring("Save As", "Enter document title:",
                                      initialvalue=self.current_document.title if self.current_document else "")
        if not title:
            return
        
        # Create new document or update existing
        if self.current_document:
            self.current_document.title = title
            self.current_document.update_content(content)
        else:
            self.current_document = TextDocument(content=content, title=title)
        
        # Save to library
        doc_id = self.library.add_document(self.current_document)
        self.last_saved_content = content
        self.unsaved_changes = False
        
        self.update_document_info()
        self.update_status(f"Saved as '{title}'", "#4CAF50")
    
    def load_document(self):
        """Load document from file"""
        if self.check_unsaved_changes():
            return
        
        file_path = filedialog.askopenfilename(
            title="Load Text Document",
            filetypes=[
                ("Text files", "*.txt"),
                ("Markdown files", "*.md"), 
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        try:
            file_path = Path(file_path)
            
            if file_path.suffix.lower() == '.json':
                # Load Science2Go document
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.current_document = TextDocument.from_dict(data)
            else:
                # Load plain text
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.current_document = TextDocument(
                    content=content,
                    title=file_path.stem,
                    source_file=str(file_path)
                )
            
            # Load into editor
            self.text_widget.delete(1.0, tk.END)
            self.text_widget.insert(1.0, self.current_document.content)
            self.last_saved_content = self.current_document.content
            self.unsaved_changes = False
            
            self.update_document_info()
            self.update_status(f"Loaded '{self.current_document.title}'", "#4CAF50")
            
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load document:\n{str(e)}")
    
    def browse_library(self):
        """Browse document library"""
        if self.check_unsaved_changes():
            return
        
        # Create library browser window
        browser = tk.Toplevel(self.parent)
        browser.title("📚 Document Library")
        browser.geometry("800x600")
        browser.transient(self.parent)
        browser.grab_set()
        
        # Library list
        list_frame = tk.Frame(browser)
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Listbox with scrollbar
        listbox_frame = tk.Frame(list_frame)
        listbox_frame.pack(fill='both', expand=True)
        
        scrollbar = tk.Scrollbar(listbox_frame)
        scrollbar.pack(side='right', fill='y')
        
        listbox = tk.Listbox(listbox_frame, yscrollcommand=scrollbar.set, font=('Consolas', 10))
        listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=listbox.yview)
        
        # Populate listbox
        documents = self.library.list_documents()
        doc_map = {}
        
        for i, doc in enumerate(documents):
            created = datetime.fromisoformat(doc.created_at).strftime("%Y-%m-%d %H:%M")
            modified = datetime.fromisoformat(doc.modified_at).strftime("%Y-%m-%d %H:%M")
            
            display_text = (f"{doc.title[:40]:<42} │ "
                          f"{doc.template_used[:15]:<17} │ "
                          f"{doc.word_count:>6} words │ "
                          f"Modified: {modified}")
            
            listbox.insert(tk.END, display_text)
            doc_map[i] = doc
        
        # Buttons
        button_frame = tk.Frame(browser)
        button_frame.pack(fill='x', padx=10, pady=5)
        
        def load_selected():
            selection = listbox.curselection()
            if selection:
                doc = doc_map[selection[0]]
                self.current_document = doc
                
                self.text_widget.delete(1.0, tk.END)
                self.text_widget.insert(1.0, doc.content)
                self.last_saved_content = doc.content
                self.unsaved_changes = False
                
                self.update_document_info()
                self.update_status(f"Loaded '{doc.title}'", "#4CAF50")
                browser.destroy()
            else:
                messagebox.showwarning("No Selection", "Please select a document to load.")
        
        def delete_selected():
            selection = listbox.curselection()
            if selection:
                doc = doc_map[selection[0]]
                if messagebox.askyesno("Confirm Delete", f"Delete document '{doc.title}'?"):
                    self.library.delete_document(doc.document_id)
                    listbox.delete(selection[0])
                    del doc_map[selection[0]]
                    # Update indices
                    new_doc_map = {}
                    for i, idx in enumerate(sorted(doc_map.keys())):
                        if idx > selection[0]:
                            new_doc_map[idx - 1] = doc_map[idx]
                        else:
                            new_doc_map[idx] = doc_map[idx]
                    doc_map.clear()
                    doc_map.update(new_doc_map)
        
        tk.Button(button_frame, text="📂 Load Selected", command=load_selected,
                 bg='#4CAF50', fg='white', padx=10).pack(side='left', padx=5)
        
        tk.Button(button_frame, text="🗑️ Delete Selected", command=delete_selected,
                 bg='#f44336', fg='white', padx=10).pack(side='left', padx=5)
        
        tk.Button(button_frame, text="❌ Cancel", command=browser.destroy,
                 bg='#757575', fg='white', padx=10).pack(side='right', padx=5)
        
        # Add header
        header = tk.Label(list_frame, text="Title                                       │ Template      │  Words │ Last Modified",
                         font=('Consolas', 9, 'bold'), anchor='w')
        header.pack(fill='x', pady=(0, 5))
    
    def search_library(self):
        """Search document library"""
        query = simpledialog.askstring("Search Library", "Enter search term:")
        if not query:
            return
        
        results = self.library.search_documents(query)
        if not results:
            messagebox.showinfo("No Results", f"No documents found containing '{query}'")
            return
        
        # Show search results (similar to browse but filtered)
        messagebox.showinfo("Search Results", f"Found {len(results)} document(s) containing '{query}'")
        # Could implement a search results window here
    
    def export_document(self, format_type: str):
        """Export document in specified format"""
        if not self.current_document:
            messagebox.showwarning("No Document", "No document to export.")
            return
        
        content = self.text_widget.get(1.0, tk.END).strip()
        if not content:
            messagebox.showwarning("Empty Document", "Cannot export empty document.")
            return
        
        # Get export filename
        extensions = {'txt': '.txt', 'md': '.md', 'json': '.json'}
        file_types = {
            'txt': [("Text files", "*.txt")],
            'md': [("Markdown files", "*.md")], 
            'json': [("JSON files", "*.json")]
        }
        
        filename = filedialog.asksaveasfilename(
            title=f"Export as {format_type.upper()}",
            defaultextension=extensions[format_type],
            filetypes=file_types[format_type]
        )
        
        if not filename:
            return
        
        try:
            if format_type == 'json':
                # Export full document with metadata
                self.current_document.update_content(content)
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.current_document.to_dict(), f, indent=2, ensure_ascii=False)
            else:
                # Export plain text
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            self.update_status(f"Exported as {format_type.upper()}", "#4CAF50")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export document:\n{str(e)}")
    
    def set_document_from_processing(self, processed_content: str, processing_result: Dict[str, Any]):
        """Set document from AI processing results"""
        template_used = processing_result.get('template_used', 'Unknown')
        source_file = getattr(self, 'last_source_file', '')
        
        # Extract processing stats
        processing_stats = {
            'input_chars': processing_result.get('input_chars', 0),
            'output_chars': processing_result.get('output_chars', 0),
            'reduction_percentage': processing_result.get('reduction_percentage', 0),
            'processing_time': processing_result.get('processing_time', 0),
            'template_used': template_used,
            'chunks_processed': processing_result.get('chunks_processed', 1),
            'success_rate': processing_result.get('success_rate', 100)
        }
        
        # Generate title
        if source_file:
            base_title = Path(source_file).stem
        else:
            base_title = "AI Processed Text"
        
        title = f"{base_title} ({template_used})"
        
        # Create document
        self.current_document = TextDocument(
            content=processed_content,
            title=title,
            template_used=template_used,
            source_file=source_file,
            processing_stats=processing_stats
        )
        
        self.last_saved_content = processed_content
        self.unsaved_changes = True  # Mark as needing save
        self.update_document_info()
        self.update_status("AI processing completed", "#4CAF50")
    
    def check_unsaved_changes(self) -> bool:
        """Check for unsaved changes and prompt user"""
        if self.unsaved_changes:
            result = messagebox.askyesnocancel(
                "Unsaved Changes", 
                "You have unsaved changes. Save before continuing?",
                icon='warning'
            )
            if result is True:  # Yes - save
                self.save_document()
                return False
            elif result is False:  # No - discard
                return False
            else:  # Cancel
                return True
        return False
    
    def update_document_info(self):
        """Update document information display"""
        if self.current_document:
            content = self.text_widget.get(1.0, tk.END).strip()
            words = len(content.split()) if content else 0
            chars = len(content)
            
            status = "●" if self.unsaved_changes else "○"
            info_text = f"{status} {self.current_document.title} ({words} words, {chars} chars)"
            self.doc_info_label.config(text=info_text)
        else:
            self.doc_info_label.config(text="No document")
    
    def update_status(self, message: str, color: str = "#4CAF50"):
        """Update status label"""
        self.status_label.config(text=message, bg=color)