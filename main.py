#!/usr/bin/env python3
"""
Science2Go - Turn Academic Papers into Audio Papers
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


def check_conda_env():
    """Check if the correct conda environment is active"""
    python_path = sys.executable
    if "science2go" in python_path:
        return True
    conda_env = os.environ.get("CONDA_DEFAULT_ENV", "")
    if conda_env == "science2go":
        return True
    return False


def check_requirements():
    """Check if core requirements are met (GUI can start)"""
    missing_critical = []
    missing_optional = []

    # Critical: needed to start the GUI at all
    try:
        import customtkinter
    except ImportError:
        missing_critical.append("customtkinter")

    try:
        import yaml
    except ImportError:
        missing_critical.append("PyYAML")

    try:
        from dotenv import load_dotenv
    except ImportError:
        missing_critical.append("python-dotenv")

    # Optional: app will start but features will be limited
    try:
        import google.generativeai
    except ImportError:
        missing_optional.append("google-generativeai (for AI text processing)")

    try:
        import google.cloud.texttospeech
    except ImportError:
        missing_optional.append("google-cloud-texttospeech (for TTS audio)")

    try:
        import pydub
    except ImportError:
        missing_optional.append("pydub (for audio processing)")

    try:
        import mutagen
    except ImportError:
        missing_optional.append("mutagen (for audio metadata)")

    if missing_critical:
        print("Error: Missing critical packages:")
        for pkg in missing_critical:
            print(f"  - {pkg}")

        if not check_conda_env():
            print(f"\n>>> You are running outside the 'science2go' conda environment!")
            print(f">>> Current Python: {sys.executable}")
            print(f">>> Activate it first:")
            print(f"      conda activate science2go")
        else:
            print(f"\nInstall missing packages:")
            print(f"   pip install {' '.join(missing_critical)}")

        return False

    if missing_optional:
        print("Note: Some optional packages are missing (app will still start):")
        for pkg in missing_optional:
            print(f"  - {pkg}")

    return True


def main():
    """Main application entry point"""
    print("Starting Science2Go...")
    print(f"Python: {sys.executable}")
    conda_env = os.environ.get('CONDA_DEFAULT_ENV', '(none)')
    print(f"Conda env: {conda_env}")

    # Check core requirements (must-have for GUI)
    if not check_requirements():
        return 1

    try:
        # Configure CustomTkinter appearance
        import customtkinter as ctk
        ctk.set_appearance_mode("system")  # "system", "dark", or "light"
        ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"

        # Create CustomTkinter root window
        root = ctk.CTk()

        # Import and create the application
        from src.gui.main_window import Science2GoApp
        app = Science2GoApp(root)

        print("Application started successfully!")

        # Start the GUI event loop
        root.mainloop()

        print("Application closed")
        return 0

    except ImportError as e:
        error_msg = f"Failed to import application modules: {e}"
        print(f"Error: {error_msg}")

        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Import Error", error_msg)
        except:
            pass

        return 1

    except Exception as e:
        error_msg = f"Application error: {e}"
        print(f"Error: {error_msg}")

        try:
            if 'root' in locals():
                messagebox.showerror("Application Error",
                                     f"An unexpected error occurred:\n{str(e)}")
        except:
            pass

        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
