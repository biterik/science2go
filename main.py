#!/usr/bin/env python3
"""
Science2Go - Academic Paper to Podcast Converter
Main application entry point
"""

import tkinter as tk
from tkinter import messagebox
import sys
import os
from pathlib import Path

# Add src directory to Python path
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

def check_requirements():
    """Check if all requirements are met"""
    missing_requirements = []
    
    # Check for required packages
    try:
        import google.generativeai
    except ImportError:
        missing_requirements.append("google-generativeai")
    
    try:
        import yaml
    except ImportError:
        missing_requirements.append("PyYAML")
    
    # Check for API key
    if not os.getenv('GEMINI_API_KEY'):
        missing_requirements.append("GEMINI_API_KEY environment variable")
    
    if missing_requirements:
        error_msg = "Missing requirements:\n" + "\n".join(f"• {req}" for req in missing_requirements)
        print(f"❌ {error_msg}")
        return False
    
    return True

def main():
    """Main application entry point"""
    print("🎙️ Starting Science2Go...")
    
    # Check requirements
    if not check_requirements():
        print("\n💡 Install missing packages with:")
        print("   pip install google-generativeai PyYAML")
        print("\n💡 Set your API key with:")
        print("   export GEMINI_API_KEY='your-api-key-here'")
        return 1
    
    try:
        # Create Tkinter root
        root = tk.Tk()
        
        # Import and create the application
        from src.gui.main_window import Science2GoApp
        app = Science2GoApp(root)
        
        print("🚀 Application started successfully!")
        
        # Start the GUI event loop
        root.mainloop()
        
        print("👋 Application closed")
        return 0
        
    except ImportError as e:
        error_msg = f"Failed to import application modules: {e}"
        print(f"❌ {error_msg}")
        
        # Show GUI error if possible
        try:
            root = tk.Tk()
            root.withdraw()  # Hide main window
            messagebox.showerror("Import Error", error_msg)
        except:
            pass  # If even Tkinter fails
        
        return 1
        
    except Exception as e:
        error_msg = f"Application error: {e}"
        print(f"❌ {error_msg}")
        
        # Show GUI error if possible
        try:
            if 'root' in locals():
                messagebox.showerror("Application Error", f"An unexpected error occurred:\n{str(e)}")
        except:
            pass
        
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)