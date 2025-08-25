"""
Science2Go Configuration Management
Safely handles API keys from shell environment or .env file
"""

import os
import sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

class Config:
    """
    Configuration manager that prioritizes shell environment variables
    over .env files for security. Perfect for public GitHub repos.
    """
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.load_environment()
        self.validate_configuration()
    
    def load_environment(self):
        """Load environment variables with priority: shell > .env > defaults"""
        
        # Try to load .env file if it exists (for local development)
        env_file = self.project_root / '.env'
        if env_file.exists():
            load_dotenv(env_file)
            print("ℹ️  Loaded configuration from .env file")
        
        # Shell environment variables take priority (your .zshrc setup)
        if any(key in os.environ for key in ['GEMINI_API_KEY', 'GOOGLE_APPLICATION_CREDENTIALS', 'GOOGLE_API_KEY']):
            print("✅ Using shell environment variables (secure)")
    
    def validate_configuration(self):
        """Validate that required API keys are available"""
        errors = []
        
        # Check for Gemini API key
        if not self.gemini_api_key:
            errors.append("GEMINI_API_KEY not found")
        
        # Check for Google Cloud credentials (either service account or API key)
        if not (self.google_credentials_path or self.google_api_key):
            errors.append("Either GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_API_KEY required")
        
        if errors:
            print("❌ Configuration errors found:")
            for error in errors:
                print(f"   - {error}")
            print("\nSetup instructions:")
            print("1. Add to ~/.zshrc: export GEMINI_API_KEY='your_key'")
            print("2. Add to ~/.zshrc: export GOOGLE_APPLICATION_CREDENTIALS='/path/to/service-account.json'")
            print("   OR: export GOOGLE_API_KEY='your_key'")
            print("3. Run: source ~/.zshrc")
            sys.exit(1)
        
        print("✅ Configuration validated successfully")
    
    # =============================================================================
    # API Keys (your existing shell variables)
    # =============================================================================
    
    @property
    def gemini_api_key(self) -> Optional[str]:
        """Gemini AI API key (your GEMINI_API_KEY)"""
        return os.getenv('GEMINI_API_KEY')
    
    @property
    def google_credentials_path(self) -> Optional[str]:
        """Google Cloud service account path (your GOOGLE_APPLICATION_CREDENTIALS)"""
        return os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    @property
    def google_api_key(self) -> Optional[str]:
        """Google API key alternative (your GOOGLE_API_KEY)"""
        return os.getenv('GOOGLE_API_KEY')
    
    @property
    def google_project_id(self) -> Optional[str]:
        """Google Cloud project ID"""
        return os.getenv('GOOGLE_CLOUD_PROJECT_ID')
    
    # =============================================================================
    # Application Settings (safe defaults)
    # =============================================================================
    
    @property
    def debug(self) -> bool:
        """Enable debug mode"""
        return os.getenv('DEBUG', 'False').lower() == 'true'
    
    @property
    def log_level(self) -> str:
        """Logging level"""
        return os.getenv('LOG_LEVEL', 'INFO')
    
    @property
    def max_audio_length_minutes(self) -> int:
        """Maximum audio length in minutes"""
        return int(os.getenv('MAX_AUDIO_LENGTH_MINUTES', '120'))
    
    @property
    def temp_dir_cleanup(self) -> bool:
        """Clean up temporary directories"""
        return os.getenv('TEMP_DIR_CLEANUP', 'True').lower() == 'true'
    
    # =============================================================================
    # Audio Processing Settings
    # =============================================================================
    
    @property
    def default_speaking_rate(self) -> float:
        """Default TTS speaking rate"""
        return float(os.getenv('DEFAULT_SPEAKING_RATE', '0.95'))
    
    @property
    def default_pitch(self) -> float:
        """Default TTS pitch"""
        return float(os.getenv('DEFAULT_PITCH', '0.0'))
    
    @property
    def default_volume_gain(self) -> float:
        """Default volume gain"""
        return float(os.getenv('DEFAULT_VOLUME_GAIN', '0.0'))
    
    # =============================================================================
    # Podcast Output Settings
    # =============================================================================
    
    @property
    def output_bitrate(self) -> str:
        """MP3 output bitrate"""
        return os.getenv('OUTPUT_BITRATE', '128k')
    
    @property
    def output_sample_rate(self) -> int:
        """Audio sample rate"""
        return int(os.getenv('OUTPUT_SAMPLE_RATE', '44100'))
    
    @property
    def normalize_audio(self) -> bool:
        """Normalize audio for podcasts"""
        return os.getenv('NORMALIZE_AUDIO', 'True').lower() == 'true'
    
    @property
    def add_chapter_markers(self) -> bool:
        """Add chapter markers to MP3"""
        return os.getenv('ADD_CHAPTER_MARKERS', 'True').lower() == 'true'
    
    # =============================================================================
    # Directory Paths
    # =============================================================================
    
    @property
    def output_dir(self) -> Path:
        """Output directory for generated files"""
        return self.project_root / 'output'
    
    @property
    def audio_dir(self) -> Path:
        """Audio output directory"""
        return self.output_dir / 'audio'
    
    @property
    def temp_dir(self) -> Path:
        """Temporary processing directory"""
        return self.output_dir / 'temp'
    
    @property
    def projects_dir(self) -> Path:
        """User projects directory"""
        return self.output_dir / 'projects'
    
    @property
    def templates_dir(self) -> Path:
        """Templates directory"""
        return self.project_root / 'src' / 'templates'
    
    def ensure_directories(self):
        """Create necessary directories if they don't exist"""
        directories = [
            self.output_dir,
            self.audio_dir, 
            self.temp_dir,
            self.projects_dir,
            self.templates_dir
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    # =============================================================================
    # Utility Methods
    # =============================================================================
    
    def get_google_tts_client_config(self) -> dict:
        """Get configuration for Google TTS client"""
        config = {}
        
        if self.google_credentials_path:
            config['credentials_path'] = self.google_credentials_path
        elif self.google_api_key:
            config['api_key'] = self.google_api_key
            
        if self.google_project_id:
            config['project_id'] = self.google_project_id
            
        return config
    
    def get_gemini_client_config(self) -> dict:
        """Get configuration for Gemini client"""
        return {
            'api_key': self.gemini_api_key
        }
    
    def __repr__(self) -> str:
        """Safe representation without exposing API keys"""
        return (f"Config(debug={self.debug}, "
                f"has_gemini_key={bool(self.gemini_api_key)}, "
                f"has_google_auth={bool(self.google_credentials_path or self.google_api_key)})")

# Global configuration instance
config = Config()