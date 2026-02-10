"""
Cross-platform GUI styling utilities for CustomTkinter
Provides platform-appropriate fonts and window configuration.
"""

import customtkinter as ctk
import platform
from pathlib import Path


class PlatformStyle:
    """Cross-platform styling manager for Science2Go GUI (CustomTkinter)"""

    def __init__(self):
        self.system = platform.system()
        self.configure_platform_defaults()

    def configure_platform_defaults(self):
        """Configure platform-specific font defaults"""
        if self.system == "Darwin":  # macOS
            self.config = {
                'font_family': 'SF Pro Display',
                'font_family_mono': 'SF Mono',
                'title_size': 18,
                'body_size': 13,
                'small_size': 11,
            }
        elif self.system == "Windows":
            self.config = {
                'font_family': 'Segoe UI',
                'font_family_mono': 'Consolas',
                'title_size': 16,
                'body_size': 11,
                'small_size': 9,
            }
        else:  # Linux and others
            self.config = {
                'font_family': 'Ubuntu',
                'font_family_mono': 'Ubuntu Mono',
                'title_size': 16,
                'body_size': 11,
                'small_size': 9,
            }

    def apply_to_window(self, root):
        """Apply platform-specific window configuration"""
        self.set_window_icon(root)

        # macOS-specific tweaks
        if self.system == "Darwin":
            try:
                root.tk.call('tk::mac::appearance', 'system')
            except Exception:
                pass

    def set_window_icon(self, root):
        """Set application icon if available"""
        try:
            import tkinter as tk
            icon_path = Path(__file__).parent.parent.parent / 'assets' / 'icon.png'
            if icon_path.exists():
                icon = tk.PhotoImage(file=str(icon_path))
                root.iconphoto(True, icon)
        except Exception:
            pass

    def get_font(self, size_type='body', weight='normal'):
        """Get platform-appropriate CTkFont"""
        size_map = {
            'title': self.config['title_size'],
            'body': self.config['body_size'],
            'small': self.config['small_size'],
        }
        size = size_map.get(size_type, self.config['body_size'])
        return ctk.CTkFont(
            family=self.config['font_family'],
            size=size,
            weight=weight,
        )

    def get_mono_font(self, size_type='body'):
        """Get platform-appropriate monospace CTkFont"""
        size_map = {
            'title': self.config['title_size'],
            'body': self.config['body_size'],
            'small': self.config['small_size'],
        }
        size = size_map.get(size_type, self.config['body_size'])
        return ctk.CTkFont(
            family=self.config['font_family_mono'],
            size=size,
        )
