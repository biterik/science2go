#!/usr/bin/env python3
"""
Science2Go Setup Script
Cross-platform installation and configuration
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path

class Science2GoSetup:
    def __init__(self):
        self.system = platform.system()
        self.python_version = sys.version_info
        self.project_root = Path(__file__).parent
        
    def check_python_version(self):
        """Ensure Python 3.11+ is available"""
        if self.python_version < (3, 11):
            print(f"❌ Python 3.11+ required. Found: {sys.version}")
            return False
        print(f"✅ Python {sys.version} detected")
        return True
    
    def check_system_dependencies(self):
        """Check for system-specific dependencies"""
        print(f"🔍 Checking system dependencies on {self.system}...")
        
        # Check for ffmpeg (required for pydub)
        if not shutil.which('ffmpeg'):
            print("⚠️  ffmpeg not found. Installing...")
            self.install_ffmpeg()
        else:
            print("✅ ffmpeg found")
    
    def install_ffmpeg(self):
        """Install ffmpeg based on the operating system"""
        try:
            if self.system == "Darwin":  # macOS
                if shutil.which('brew'):
                    subprocess.run(['brew', 'install', 'ffmpeg'], check=True)
                    print("✅ ffmpeg installed via Homebrew")
                else:
                    print("❌ Homebrew not found. Please install ffmpeg manually:")
                    print("   brew install ffmpeg")
                    
            elif self.system == "Linux":
                # Try different package managers
                if shutil.which('apt'):
                    subprocess.run(['sudo', 'apt', 'update'], check=True)
                    subprocess.run(['sudo', 'apt', 'install', '-y', 'ffmpeg'], check=True)
                    print("✅ ffmpeg installed via apt")
                elif shutil.which('yum'):
                    subprocess.run(['sudo', 'yum', 'install', '-y', 'ffmpeg'], check=True)
                    print("✅ ffmpeg installed via yum")
                elif shutil.which('pacman'):
                    subprocess.run(['sudo', 'pacman', '-S', 'ffmpeg'], check=True)
                    print("✅ ffmpeg installed via pacman")
                else:
                    print("❌ Package manager not found. Please install ffmpeg manually")
                    
            elif self.system == "Windows":
                print("ℹ️  On Windows, ffmpeg will be handled by conda-forge")
                print("   If using pip only, download from: https://ffmpeg.org/download.html")
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install ffmpeg: {e}")
            print("Please install ffmpeg manually for your system")
    
    def setup_conda_environment(self):
        """Set up conda environment"""
        if not shutil.which('conda'):
            print("❌ Conda not found. Using pip installation method...")
            return self.setup_pip_environment()
        
        print("🐍 Setting up conda environment...")
        try:
            # Create environment
            subprocess.run([
                'conda', 'env', 'create', 
                '-f', 'environment.yml', 
                '--force'
            ], check=True)
            
            print("✅ Conda environment 'science2go' created successfully!")
            print("\nTo activate the environment, run:")
            print("   conda activate science2go")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create conda environment: {e}")
            print("Falling back to pip installation...")
            return self.setup_pip_environment()
    
    def setup_pip_environment(self):
        """Set up pip environment (fallback)"""
        print("📦 Installing packages with pip...")
        try:
            # Upgrade pip first
            subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'], check=True)
            
            # Install requirements
            subprocess.run([
                sys.executable, '-m', 'pip', 'install', 
                '-r', 'requirements.txt'
            ], check=True)
            
            print("✅ Pip packages installed successfully!")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install pip packages: {e}")
            return False
    
    def create_directories(self):
        """Create necessary project directories"""
        print("📁 Creating project directories...")
        
        directories = [
            'output/audio',
            'output/temp', 
            'output/projects',
            'src/templates',
            'tests'
        ]
        
        for directory in directories:
            dir_path = self.project_root / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"   ✅ {directory}")
    
    def create_env_template(self):
        """Create .env template file (safe for GitHub)"""
        env_template_path = self.project_root / '.env.template'
        
        print("✅ .env.template already exists (safe for GitHub)")
        print("ℹ️  Using your existing shell environment variables:")
        
        # Check for existing shell environment variables
        shell_vars = ['GEMINI_API_KEY', 'GOOGLE_APPLICATION_CREDENTIALS', 'GOOGLE_API_KEY']
        found_vars = [var for var in shell_vars if os.getenv(var)]
        
        if found_vars:
            for var in found_vars:
                print(f"   ✅ {var} (from shell)")
        else:
            print("⚠️  No shell environment variables found.")
            print("   Add to ~/.zshrc:")
            print("   export GEMINI_API_KEY='your_key'")
            print("   export GOOGLE_APPLICATION_CREDENTIALS='/path/to/service-account.json'")
            print("   Then run: source ~/.zshrc")
    
    def verify_installation(self):
        """Verify the installation works"""
        print("🔍 Verifying installation...")
        
        try:
            # Test imports
            test_imports = [
                'PyPDF2',
                'google.cloud.texttospeech',
                'google.generativeai',
                'pydub',
                'mutagen',
                'yaml',
                'dotenv'
            ]
            
            for module in test_imports:
                __import__(module)
                print(f"   ✅ {module}")
            
            print("✅ All modules imported successfully!")
            return True
            
        except ImportError as e:
            print(f"❌ Import test failed: {e}")
            return False
    
    def run_setup(self):
        """Run complete setup process"""
        print("🚀 Science2Go Setup Starting...")
        print("=" * 50)
        
        # Check prerequisites
        if not self.check_python_version():
            return False
        
        self.check_system_dependencies()
        
        # Setup environment
        if not self.setup_conda_environment():
            return False
        
        # Create project structure
        self.create_directories()
        self.create_env_template()
        
        # Verify installation
        if not self.verify_installation():
            print("\n❌ Setup completed with warnings. Some modules may not import correctly.")
            return False
        
        print("\n" + "=" * 50)
        print("🎉 Science2Go setup completed successfully!")
        print("\nNext steps:")
        print("1. Copy .env.template to .env and add your API keys")
        print("2. If using conda: conda activate science2go")
        print("3. Run: python main.py")
        print("\nFor API key setup instructions, see README.md")
        
        return True

if __name__ == "__main__":
    setup = Science2GoSetup()
    success = setup.run_setup()
    sys.exit(0 if success else 1)