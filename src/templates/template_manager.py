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
                "Custom Template": "custom_template.yaml"
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
        
        _context_block = (
            'CONTEXT FROM PREVIOUS SECTION (for continuity only — do NOT include in your output):\n'
            '---\n{context}\n---\n\n'
        )

        if "Review" in name:
            template_content = {
                'name': name,
                'description': 'Default review paper cleanup template',
                'system_prompt': 'You are an expert at cleaning academic review papers. Remove citations, figure/table references, front/back matter. Expand acronyms on first use. Preserve all scientific content.',
                'user_prompt': _context_block + 'TEXT TO CLEAN (clean ONLY the text below and output it):\n{content}',
                'post_processing': {
                    'cleanup_only': True,
                    'preserve_content': True,
                }
            }
        elif "Technical" in name:
            template_content = {
                'name': name,
                'description': 'Default technical paper cleanup template',
                'system_prompt': 'You are an expert at cleaning technical research papers. Remove citations, figure/table references, front/back matter. Expand abbreviations and spell out equations. Preserve all technical content.',
                'user_prompt': _context_block + 'TEXT TO CLEAN (clean ONLY the text below and output it):\n{content}',
                'post_processing': {
                    'cleanup_only': True,
                    'preserve_content': True,
                    'technical_accuracy': True,
                }
            }
        else:
            template_content = {
                'name': name,
                'description': 'Custom cleanup template',
                'system_prompt': 'You are a conservative text processor. Make only minimal changes necessary for clarity. Preserve all original content and structure.',
                'user_prompt': _context_block + 'TEXT TO CLEAN (make minimal changes only):\n{content}',
                'post_processing': {
                    'cleanup_only': True,
                    'minimal_changes': True,
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
    
    def get_user_prompt(self, template_name: str, content: str, context: str = "") -> str:
        """Get formatted user prompt with content and optional context preamble.

        Args:
            template_name: Name of the template to use.
            content: The text chunk to process.
            context: Trailing text from the previous chunk's output, used for
                     continuity. Empty string for single-document or first chunk.
        """
        template = self.get_template(template_name)
        if template:
            prompt_template = template.get('user_prompt', '')
            context_text = context if context else "None — this is the first section of the document."
            try:
                return prompt_template.format(content=content, context=context_text)
            except KeyError:
                # Template doesn't have {context} placeholder — format without it
                return prompt_template.format(content=content)
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