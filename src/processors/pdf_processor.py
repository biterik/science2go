"""
PDF Metadata Extraction for Science2Go
Extracts paper information using DOI lookup via CrossRef API with PDF fallback
"""

import re
import requests
from typing import Optional, Dict, Any, List
from pathlib import Path
import PyPDF2
import io

class PDFMetadataExtractor:
    """Extract paper metadata from PDF files using multiple strategies"""
    
    def __init__(self):
        self.crossref_base_url = "https://api.crossref.org/works"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Science2Go/1.0 (mailto:your-email@example.com)'  # CrossRef requires User-Agent
        })
    
    def extract_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract metadata from PDF using DOI lookup first, then direct PDF parsing
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary with paper metadata
        """
        result = {
            'title': '',
            'authors': '',
            'journal': '',
            'year': '',
            'doi': '',
            'abstract': '',
            'extraction_method': '',
            'success': False,
            'error': None
        }
        
        try:
            # Strategy 1: Try to find DOI and lookup via CrossRef
            doi = self.extract_doi_from_pdf(pdf_path)
            if doi:
                crossref_data = self.lookup_doi_crossref(doi)
                if crossref_data:
                    result.update(crossref_data)
                    result['extraction_method'] = 'CrossRef API (DOI lookup)'
                    result['success'] = True
                    print(f"✅ Extracted metadata via CrossRef for DOI: {doi}")
                    return result
            
            # Strategy 2: Direct PDF metadata extraction
            pdf_data = self.extract_from_pdf_direct(pdf_path)
            if pdf_data and any(pdf_data.values()):
                result.update(pdf_data)
                result['extraction_method'] = 'Direct PDF parsing'
                result['success'] = True
                print("✅ Extracted metadata directly from PDF")
                return result
            
            # If we get here, extraction failed
            result['error'] = "Could not extract metadata from PDF"
            print("⚠️ Failed to extract metadata from PDF")
            
        except Exception as e:
            result['error'] = str(e)
            print(f"❌ Error extracting PDF metadata: {e}")
        
        return result
    
    def extract_doi_from_pdf(self, pdf_path: str) -> Optional[str]:
        """
        Extract DOI from PDF text content
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            DOI string if found, None otherwise
        """
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Search first few pages for DOI
                pages_to_search = min(3, len(pdf_reader.pages))
                text_content = ""
                
                for i in range(pages_to_search):
                    try:
                        text_content += pdf_reader.pages[i].extract_text()
                    except Exception as e:
                        print(f"Warning: Could not extract text from page {i+1}: {e}")
                        continue
                
                # DOI patterns (common formats)
                doi_patterns = [
                    r'doi:\s*([10]\.\d{4,}[^\s]+)',  # doi: 10.xxxx/xxxxx
                    r'DOI:\s*([10]\.\d{4,}[^\s]+)',  # DOI: 10.xxxx/xxxxx
                    r'https://doi\.org/([10]\.\d{4,}[^\s]+)',  # https://doi.org/10.xxxx/xxxxx
                    r'http://dx\.doi\.org/([10]\.\d{4,}[^\s]+)',  # http://dx.doi.org/10.xxxx/xxxxx
                    r'dx\.doi\.org/([10]\.\d{4,}[^\s]+)',  # dx.doi.org/10.xxxx/xxxxx
                    r'([10]\.\d{4,}/[^\s]+)'  # Direct DOI format
                ]
                
                for pattern in doi_patterns:
                    match = re.search(pattern, text_content, re.IGNORECASE)
                    if match:
                        doi = match.group(1) if match.lastindex else match.group(0)
                        # Clean up DOI
                        doi = doi.rstrip('.,;')  # Remove trailing punctuation
                        if self.validate_doi(doi):
                            print(f"✅ Found DOI in PDF: {doi}")
                            return doi
                
                print("⚠️ No valid DOI found in PDF")
                return None
                
        except Exception as e:
            print(f"❌ Error extracting DOI from PDF: {e}")
            return None
    
    def validate_doi(self, doi: str) -> bool:
        """
        Validate DOI format
        
        Args:
            doi: DOI string to validate
            
        Returns:
            True if valid DOI format
        """
        # Basic DOI validation
        doi_regex = r'^10\.\d{4,}/.+$'
        return bool(re.match(doi_regex, doi))
    
    def lookup_doi_crossref(self, doi: str) -> Optional[Dict[str, str]]:
        """
        Lookup paper metadata using CrossRef API
        
        Args:
            doi: DOI to lookup
            
        Returns:
            Dictionary with metadata if successful, None otherwise
        """
        try:
            url = f"{self.crossref_base_url}/{doi}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            work = data.get('message', {})
            
            # Extract metadata from CrossRef response
            result = {
                'title': self.extract_title(work),
                'authors': self.extract_authors(work),
                'journal': self.extract_journal(work),
                'year': self.extract_year(work),
                'doi': doi,
                'abstract': self.extract_abstract(work)
            }
            
            print(f"✅ Successfully retrieved metadata from CrossRef")
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"❌ CrossRef API request failed: {e}")
            return None
        except Exception as e:
            print(f"❌ Error processing CrossRef response: {e}")
            return None
    
    def extract_title(self, work: Dict) -> str:
        """Extract title from CrossRef work data"""
        title_list = work.get('title', [])
        return title_list[0] if title_list else ''
    
    def extract_authors(self, work: Dict) -> str:
        """Extract authors from CrossRef work data"""
        authors = work.get('author', [])
        author_names = []
        
        for author in authors:
            given = author.get('given', '')
            family = author.get('family', '')
            if family:
                if given:
                    author_names.append(f"{given} {family}")
                else:
                    author_names.append(family)
        
        return ', '.join(author_names)
    
    def extract_journal(self, work: Dict) -> str:
        """Extract journal name from CrossRef work data"""
        # Try different fields for journal name
        container_title = work.get('container-title', [])
        if container_title:
            return container_title[0]
        
        publisher = work.get('publisher', '')
        return publisher if publisher else ''
    
    def extract_year(self, work: Dict) -> str:
        """Extract publication year from CrossRef work data"""
        # Try different date fields
        published = work.get('published-print') or work.get('published-online') or work.get('created')
        if published and 'date-parts' in published:
            date_parts = published['date-parts'][0]
            if date_parts:
                return str(date_parts[0])
        
        return ''
    
    def extract_abstract(self, work: Dict) -> str:
        """Extract abstract from CrossRef work data"""
        return work.get('abstract', '')
    
    def extract_from_pdf_direct(self, pdf_path: str) -> Dict[str, str]:
        """
        Extract metadata directly from PDF file
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary with extracted metadata
        """
        result = {
            'title': '',
            'authors': '',
            'journal': '',
            'year': '',
            'doi': '',
            'abstract': ''
        }
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # First try to get metadata from PDF properties
                if pdf_reader.metadata:
                    metadata = pdf_reader.metadata
                    result['title'] = metadata.get('/Title', '') or ''
                    result['authors'] = metadata.get('/Author', '') or ''
                    
                    # Try to extract year from creation date
                    creation_date = metadata.get('/CreationDate', '') or metadata.get('/ModDate', '')
                    if creation_date:
                        year_match = re.search(r'D:(\d{4})', str(creation_date))
                        if year_match:
                            result['year'] = year_match.group(1)
                
                # Extract text from first few pages for additional parsing
                text_content = ""
                pages_to_extract = min(2, len(pdf_reader.pages))
                
                for i in range(pages_to_extract):
                    try:
                        text_content += pdf_reader.pages[i].extract_text() + "\n"
                    except Exception as e:
                        print(f"Warning: Could not extract text from page {i+1}: {e}")
                        continue
                
                # If title is empty, try to extract from text
                if not result['title']:
                    result['title'] = self.extract_title_from_text(text_content)
                
                # If authors is empty, try to extract from text
                if not result['authors']:
                    result['authors'] = self.extract_authors_from_text(text_content)
                
                # Try to extract journal and year from text
                if not result['journal']:
                    result['journal'] = self.extract_journal_from_text(text_content)
                
                if not result['year']:
                    result['year'] = self.extract_year_from_text(text_content)
                
                # Try to extract abstract
                result['abstract'] = self.extract_abstract_from_text(text_content)
                
        except Exception as e:
            print(f"❌ Error in direct PDF extraction: {e}")
        
        return result
    
    def extract_title_from_text(self, text: str) -> str:
        """Extract title from PDF text content"""
        lines = text.split('\n')
        
        # Look for title in first few lines
        for i, line in enumerate(lines[:10]):
            line = line.strip()
            if line and len(line) > 10:  # Title should be substantial
                # Skip common headers/footers
                skip_patterns = ['abstract', 'introduction', 'page', 'doi:', 'published', 'copyright']
                if not any(pattern in line.lower() for pattern in skip_patterns):
                    return line
        
        return ''
    
    def extract_authors_from_text(self, text: str) -> str:
        """Extract authors from PDF text content"""
        lines = text.split('\n')
        
        # Look for author patterns
        for line in lines[:20]:  # Search in first 20 lines
            line = line.strip()
            
            # Common author patterns
            author_patterns = [
                r'^([A-Z][a-z]+ [A-Z]\. [A-Z][a-z]+(?:, [A-Z][a-z]+ [A-Z]\. [A-Z][a-z]+)*)',
                r'^([A-Z][a-z]+ [A-Z][a-z]+(?:, [A-Z][a-z]+ [A-Z][a-z]+)*)',
            ]
            
            for pattern in author_patterns:
                match = re.match(pattern, line)
                if match:
                    return match.group(1)
        
        return ''
    
    def extract_journal_from_text(self, text: str) -> str:
        """Extract journal name from PDF text content"""
        # Look for journal patterns
        journal_patterns = [
            r'published in ([^,\n]+)',
            r'([A-Z][a-z]+ (?:Journal|Review|Letters|Science|Nature)[^,\n]*)',
            r'Journal of ([^,\n]+)',
            r'([A-Z][a-z]+ Research[^,\n]*)',
        ]
        
        for pattern in journal_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return ''
    
    def extract_year_from_text(self, text: str) -> str:
        """Extract publication year from PDF text content"""
        # Look for year patterns (recent years)
        year_patterns = [
            r'(20[0-2][0-9])',  # 2000-2029
            r'(19[8-9][0-9])',  # 1980-1999
        ]
        
        for pattern in year_patterns:
            matches = re.findall(pattern, text)
            if matches:
                # Return the most recent year found
                return str(max(int(year) for year in matches))
        
        return ''
    
    def extract_abstract_from_text(self, text: str) -> str:
        """Extract abstract from PDF text content"""
        # Look for abstract section
        abstract_pattern = r'(?:ABSTRACT|Abstract)\s*[:\-]?\s*(.*?)(?=\n\s*\n|\n\s*[A-Z]|\n\s*\d+\.|\n\s*Keywords|\n\s*Introduction|$)'
        
        match = re.search(abstract_pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            abstract = match.group(1).strip()
            # Clean up the abstract
            abstract = re.sub(r'\s+', ' ', abstract)  # Normalize whitespace
            return abstract[:500] + '...' if len(abstract) > 500 else abstract
        
        return ''

# Convenience function for easy import
def extract_pdf_metadata(pdf_path: str) -> Dict[str, Any]:
    """
    Extract metadata from PDF file
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Dictionary with extracted metadata
    """
    extractor = PDFMetadataExtractor()
    return extractor.extract_metadata(pdf_path)