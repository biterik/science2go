#!/usr/bin/env python3
"""
Science2Go Project Cleanup Script
Removes temporary files, cache, and debugging artifacts
"""

import os
import shutil
from pathlib import Path
import sys

def cleanup_project():
    """Clean up the Science2Go project directory"""
    
    project_root = Path.cwd()
    print(f"Cleaning up Science2Go project in: {project_root}")
    
    # Files and directories to remove
    cleanup_targets = [
        # Python cache files
        "**/__pycache__",
        "**/*.pyc",
        "**/*.pyo", 
        "**/*.pyd",
        "**/.Python",
        
        # Debug and test files (based on your current directory)
        "check_gui_init.py",
        "debug_extraction.py",
        "debug_templates.py",
        "find_bad_import.py",
        "fix_gui_init.py", 
        "fix_imports.py",
        "import_fix_diagnostic.py",
        "test_imports.py",
        "test_pdf_extraction.py",
        "src/test_buttons.py",
        
        # Temporary output (keep structure, clean contents)
        "output/temp/*",
        "output/audio/*",
        "output/projects/*",
        
        # IDE and editor files
        ".vscode/settings.json",  # Keep .vscode folder structure
        ".idea",
        "*.swp",
        "*.swo",
        "*~",
        
        # OS generated files
        ".DS_Store",
        "Thumbs.db",
        "desktop.ini",
        
        # Backup files
        "*.bak",
        "*.backup",
        "*.orig",
    ]
    
    removed_files = []
    removed_dirs = []
    kept_files = []
    
    # Process cleanup targets
    for pattern in cleanup_targets:
        if pattern.endswith("/*"):
            # Clean directory contents but keep the directory
            dir_path = project_root / pattern[:-2]
            if dir_path.exists() and dir_path.is_dir():
                for item in dir_path.iterdir():
                    if item.is_file():
                        item.unlink()
                        removed_files.append(str(item.relative_to(project_root)))
                    elif item.is_dir():
                        shutil.rmtree(item)
                        removed_dirs.append(str(item.relative_to(project_root)))
        elif "**/" in pattern:
            # Recursive pattern matching
            for path in project_root.rglob(pattern.replace("**/", "")):
                try:
                    if path.is_file():
                        path.unlink()
                        removed_files.append(str(path.relative_to(project_root)))
                    elif path.is_dir():
                        shutil.rmtree(path)
                        removed_dirs.append(str(path.relative_to(project_root)))
                except OSError as e:
                    print(f"Warning: Could not remove {path}: {e}")
        else:
            # Direct file/directory
            path = project_root / pattern
            if path.exists():
                try:
                    if path.is_file():
                        path.unlink()
                        removed_files.append(str(path.relative_to(project_root)))
                    elif path.is_dir():
                        shutil.rmtree(path)
                        removed_dirs.append(str(path.relative_to(project_root)))
                except OSError as e:
                    print(f"Warning: Could not remove {path}: {e}")
    
    # Keep important files that might look like temp files
    important_files = [
        "src/processors/text_processor_fixed.py",  # This might be your working version
    ]
    
    for file_path in important_files:
        path = project_root / file_path
        if path.exists():
            kept_files.append(file_path)
    
    # Ensure required directories exist and are empty
    required_dirs = [
        "output/audio",
        "output/temp", 
        "output/projects",
        "output/document_library"
    ]
    
    for dir_path in required_dirs:
        (project_root / dir_path).mkdir(parents=True, exist_ok=True)
        
        # Create .gitkeep files to preserve empty directories in git
        gitkeep_file = project_root / dir_path / ".gitkeep"
        if not gitkeep_file.exists():
            gitkeep_file.touch()
    
    # Summary
    print("\n" + "="*50)
    print("CLEANUP SUMMARY")
    print("="*50)
    
    if removed_files:
        print(f"\nRemoved {len(removed_files)} files:")
        for f in sorted(removed_files):
            print(f"  - {f}")
    
    if removed_dirs:
        print(f"\nRemoved {len(removed_dirs)} directories:")
        for d in sorted(removed_dirs):
            print(f"  - {d}/")
    
    if kept_files:
        print(f"\nKept important files:")
        for f in kept_files:
            print(f"  ✓ {f}")
    
    print(f"\nCreated .gitkeep files in {len(required_dirs)} output directories")
    
    if not removed_files and not removed_dirs:
        print("\nProject was already clean!")
    else:
        print(f"\nCleaned up {len(removed_files)} files and {len(removed_dirs)} directories")
    
    print("\n✅ Project cleanup completed!")
    
    # Check for any remaining debug files
    remaining_debug = []
    for pattern in ["*debug*", "*test*", "*fix*", "*check*"]:
        for path in project_root.rglob(pattern):
            if path.is_file() and path.suffix == ".py":
                remaining_debug.append(str(path.relative_to(project_root)))
    
    if remaining_debug:
        print("\n⚠️  Remaining files that might be debug/test files:")
        for f in remaining_debug:
            print(f"  ? {f}")
        print("\nReview these files and remove manually if they're not needed.")

if __name__ == "__main__":
    try:
        cleanup_project()
    except KeyboardInterrupt:
        print("\n❌ Cleanup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during cleanup: {e}")
        sys.exit(1)