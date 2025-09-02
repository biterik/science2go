"""
Cross-platform GUI styling utilities
Provides native look and feel across macOS, Windows, and Linux
"""

import tkinter as tk
from tkinter import ttk
import platform
import sys

class PlatformStyle:
    """Cross-platform styling manager for Science2Go GUI"""
    
    def __init__(self):
        self.system = platform.system()
        self.configure_platform_defaults()
    
    def configure_platform_defaults(self):
        """Configure platform-specific defaults"""
        if self.system == "Darwin":  # macOS
            self.config = {
                'font_family': 'SF Pro Display',
                'font_family_mono': 'SF Mono',
                'title_size': 18,
                'body_size': 13,
                'small_size': 11,
                'button_padding': (12, 8),
                'frame_padding': 15,
                'use_native_buttons': True,
                'accent_color': '#007AFF',
                'background_color': '#FFFFFF',
                'text_color': '#000000',
                'secondary_color': '#8E8E93'
            }
        elif self.system == "Windows":  # Windows
            self.config = {
                'font_family': 'Segoe UI',
                'font_family_mono': 'Consolas',
                'title_size': 16,
                'body_size': 11,
                'small_size': 9,
                'button_padding': (10, 6),
                'frame_padding': 12,
                'use_native_buttons': True,
                'accent_color': '#0078D4',
                'background_color': '#FFFFFF',
                'text_color': '#000000',
                'secondary_color': '#666666'
            }
        else:  # Linux and others
            self.config = {
                'font_family': 'Ubuntu',
                'font_family_mono': 'Ubuntu Mono',
                'title_size': 16,
                'body_size': 11,
                'small_size': 9,
                'button_padding': (10, 6),
                'frame_padding': 12,
                'use_native_buttons': False,
                'accent_color': '#4A90E2',
                'background_color': '#FFFFFF',
                'text_color': '#000000',
                'secondary_color': '#666666'
            }
    
    @staticmethod
    def apply_platform_styling(root):
        """Apply platform-specific styling to the main window (static method)"""
        system = platform.system()
        
        if system == "Darwin":  # macOS
            # macOS specific styling
            root.configure(bg='#FFFFFF')
            try:
                # Try to set native macOS appearance
                root.tk.call('tk::mac::appearance', 'system')
            except tk.TclError:
                pass
        
        elif system == "Windows":  # Windows
            # Windows specific styling
            root.configure(bg='#FFFFFF')
            try:
                # Try to enable Windows 10/11 modern styling
                root.tk.call('tk', 'scaling', 1.0)
            except tk.TclError:
                pass
        
        else:  # Linux
            # Linux specific styling
            root.configure(bg='#FFFFFF')
    
    def apply_to_window(self, root):
        """Apply platform-specific styling to the main window (instance method)"""
        # Set window icon if available
        self.set_window_icon(root)
        
        # Configure ttk styles
        self.configure_ttk_styles(root)
        
        # Platform-specific window tweaks
        if self.system == "Darwin":
            # macOS specific
            root.configure(bg=self.config['background_color'])
            try:
                # Try to set native macOS appearance
                root.tk.call('tk::mac::appearance', 'system')
            except tk.TclError:
                pass
        
        elif self.system == "Windows":
            # Windows specific
            root.configure(bg=self.config['background_color'])
            try:
                # Try to enable Windows 10/11 modern styling
                root.tk.call('tk', 'scaling', 1.0)
            except tk.TclError:
                pass
        
        else:
            # Linux specific
            root.configure(bg=self.config['background_color'])
    
    def set_window_icon(self, root):
        """Set application icon if available"""
        try:
            # Look for icon file in project root
            from pathlib import Path
            icon_path = Path(__file__).parent.parent.parent / 'assets' / 'icon.png'
            if icon_path.exists():
                # Load icon
                icon = tk.PhotoImage(file=str(icon_path))
                root.iconphoto(True, icon)
        except Exception:
            # Icon loading failed, continue without icon
            pass
    
    def configure_ttk_styles(self, root):
        """Configure ttk widget styles for platform consistency"""
        style = ttk.Style()
        
        # Configure fonts
        try:
            style.configure('.', font=(self.config['font_family'], self.config['body_size']))
            style.configure('Title.TLabel', font=(self.config['font_family'], self.config['title_size'], 'bold'))
            style.configure('Heading.TLabel', font=(self.config['font_family'], self.config['body_size'], 'bold'))
            style.configure('Small.TLabel', font=(self.config['font_family'], self.config['small_size']))
            style.configure('Mono.TLabel', font=(self.config['font_family_mono'], self.config['small_size']))
        except tk.TclError:
            # Font configuration failed, use defaults
            pass
        
        # Configure button styles
        try:
            style.configure('Accent.TButton', 
                          background=self.config['accent_color'],
                          foreground='white')
        except tk.TclError:
            pass
    
    def get_font(self, size_type='body', weight='normal'):
        """Get platform-appropriate font"""
        size_map = {
            'title': self.config['title_size'],
            'body': self.config['body_size'], 
            'small': self.config['small_size']
        }
        
        size = size_map.get(size_type, self.config['body_size'])
        family = self.config['font_family']
        
        if weight == 'bold':
            return (family, size, 'bold')
        else:
            return (family, size)
    
    def get_mono_font(self, size_type='body'):
        """Get platform-appropriate monospace font"""
        size_map = {
            'title': self.config['title_size'],
            'body': self.config['body_size'],
            'small': self.config['small_size']
        }
        
        size = size_map.get(size_type, self.config['body_size'])
        return (self.config['font_family_mono'], size)