"""
Template Manager for Science2Go - FIXED PATH RESOLUTION
Handles loading and processing of YAML templates for AI processing
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import os

class TemplateManager:
    """Manages AI processing templates"""
    
    def __init__(self):
        # Fix path resolution - check multiple possible locations
        possible_paths = [
            Path(__file__).parent,  # src/templates/
            Path(__file__).parent.parent / "templates",  # src/templates/ (if called from elsewhere)
            Path("src/templates"),  # relative to project root
            Path("templates"),  # if templates are in project root
        ]
        
        self.templates_dir = None
        for path in possible_paths:
            if path.exists() and path.is_dir():
                self.templates_dir = path
                break
        
        if self.templates_dir is None:
            print("❌ Templates directory not found! Checked paths:")
            for path in possible_paths:
                print(f"   - {path.absolute()} (exists: {path.exists()})")
            self.templates_dir = Path(__file__).parent  # fallback
        
        print(f"📁 Using templates directory: {self.templates_dir.absolute()}")
        
        self.templates = {}
        self.load_templates()
    
    def load_templates(self):
        """Load all YAML templates from the templates directory"""
        try:
            template_files = {
                "Review Papers": "review_papers.yaml",
                "Technical Papers": "technical_papers.yaml",
                "Custom Template": "custom_template.yaml",
                "SSML Converter": "ssml_converter.yaml",
            }
            
            print(f"🔍 Looking for templates in: {self.templates_dir}")
            print(f"📋 Directory contents: {list(self.templates_dir.iterdir()) if self.templates_dir.exists() else 'DIR DOES NOT EXIST'}")
            
            for name, filename in template_files.items():
                template_path = self.templates_dir / filename
                print(f"   Checking: {template_path} (exists: {template_path.exists()})")
                
                if template_path.exists():
                    with open(template_path, 'r', encoding='utf-8') as file:
                        template_data = yaml.safe_load(file)
                        self.templates[name] = template_data
                        print(f"✅ Loaded template: {name}")
                else:
                    print(f"⚠️ Template file not found: {filename}")
                    # Create a basic template if missing
                    self.create_default_template(name, template_path)
                    
        except Exception as e:
            print(f"❌ Error loading templates: {e}")
            import traceback
            traceback.print_exc()
    
    def create_default_template(self, name: str, path: Path):
        """Create a default template if missing"""
        print(f"🏗️ Creating default template: {name}")
        
        if "Review" in name:
            template_content = {
                'name': name,
                'description': 'Default review paper template',
                'system_prompt': 'You are an expert at converting academic review papers into audio-friendly format.',
                'user_prompt': 'Convert this academic text to audio-friendly format. Remove figures, tables, citations. Add natural transitions.\n\nTEXT TO CONVERT:\n{content}',
                'post_processing': {
                    'add_section_markers': True,
                    'natural_transitions': True,
                    'tts_optimizations': True
                }
            }
        elif "Technical" in name:
            template_content = {
                'name': name,
                'description': 'Default technical paper template',
                'system_prompt': 'You are an expert at converting technical research papers into audio-friendly format.',
                'user_prompt': 'Convert this technical paper to audio-friendly format. Explain complex concepts clearly. Remove figures, tables, citations.\n\nTEXT TO CONVERT:\n{content}',
                'post_processing': {
                    'add_section_markers': True,
                    'technical_explanations': True,
                    'tts_optimizations': True
                }
            }
        else:
            template_content = {
                'name': name,
                'description': 'Custom template',
                'system_prompt': 'You are an expert content processor.',
                'user_prompt': 'Process this content according to user specifications.\n\nTEXT TO CONVERT:\n{content}',
                'post_processing': {
                    'user_defined': True
                }
            }
        
        try:
            # Ensure directory exists
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as file:
                yaml.dump(template_content, file, default_flow_style=False, allow_unicode=True)
            
            self.templates[name] = template_content
            print(f"✅ Created and loaded default template: {name}")
            
        except Exception as e:
            print(f"❌ Failed to create default template {name}: {e}")
    
    def get_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Get template by name"""
        return self.templates.get(template_name)
    
    def get_system_prompt(self, template_name: str) -> str:
        """Get system prompt for template"""
        template = self.get_template(template_name)
        if template:
            return template.get('system_prompt', '')
        return ''
    
    def get_user_prompt(self, template_name: str, content: str, **kwargs) -> str:
        """Get formatted user prompt with content and optional extra placeholders.

        The SSML Converter template uses {context} in addition to {content}.
        Any extra keyword arguments (e.g. context='...') are passed through
        to str.format().  Missing placeholders default to empty string.
        """
        template = self.get_template(template_name)
        if template:
            prompt_template = template.get('user_prompt', '')
            # Build format dict with content + any extras; default missing keys
            fmt = {'content': content, **kwargs}
            # Use format_map with a defaultdict so missing keys become ''
            import collections
            safe_fmt = collections.defaultdict(str, fmt)
            return prompt_template.format_map(safe_fmt)
        return content
    
    def get_description(self, template_name: str) -> str:
        """Get template description"""
        template = self.get_template(template_name)
        if template:
            return template.get('description', '')
        return ''
    
    def list_templates(self) -> list:
        """List all available template names"""
        return list(self.templates.keys())

# Global template manager instance
template_manager = TemplateManager()