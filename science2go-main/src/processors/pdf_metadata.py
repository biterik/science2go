"""
PDF Metadata Extraction for Science2Go
Enhanced with title-based CrossRef lookup for better metadata extraction
"""

import re
import requests
from typing import Optional, Dict, Any, List
from pathlib import Path
import PyPDF2
import io
import urllib.parse

class PDFMetadataExtractor:
    """Extract paper metadata from PDF files using multiple strategies"""
    
    def __init__(self):
        self.crossref_base_url = "https://api.crossref.org/works"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Science2Go/1.0 (mailto:your-email@example.com)'
        })
    
    def extract_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """
        Enhanced metadata extraction: DOI lookup -> Title search -> Direct PDF parsing
        """
        result = {
            'title': '',
            'authors': '',
            'journal': '',
            'year': '',
            'doi': '',
            'abstract': '',
            'license': '',
            'url': '',
            'extraction_method': '',
            'success': False,
            'error': None
        }
        
        try:
            # Strategy 1: Try to find DOI and lookup via CrossRef
            print("🔍 Looking for DOI in PDF...")
            doi = self.extract_doi_from_pdf(pdf_path)
            if doi:
                print(f"✅ Found DOI: {doi}")
                crossref_data = self.lookup_doi_crossref(doi)
                if crossref_data:
                    result.update(crossref_data)
                    result['extraction_method'] = 'CrossRef API (DOI lookup)'
                    result['success'] = True
                    print(f"✅ Extracted metadata via CrossRef for DOI: {doi}")
                    return result
            else:
                print("⚠️ No valid DOI found in PDF")
            
            # Strategy 2: Extract title from PDF, then search CrossRef
            print("🔍 Attempting direct PDF parsing for title...")
            pdf_data = self.extract_from_pdf_direct(pdf_path)
            if pdf_data and pdf_data.get('title'):
                title = pdf_data['title']
                print(f"📄 Extracted title: {title[:60]}...")
                
                # Search CrossRef by title
                print("🌐 Searching CrossRef by title...")
                crossref_data = self.search_crossref_by_title(title)
                if crossref_data:
                    # Merge CrossRef data with PDF data (CrossRef takes priority)
                    merged_data = pdf_data.copy()
                    merged_data.update(crossref_data)
                    result.update(merged_data)
                    result['extraction_method'] = 'CrossRef API (title search) + PDF parsing'
                    result['success'] = True
                    print("✅ Enhanced metadata via CrossRef title search + PDF parsing")
                    return result
                else:
                    print("⚠️ CrossRef title search failed, using PDF data only")
                    result.update(pdf_data)
                    result['extraction_method'] = 'Direct PDF parsing'
                    result['success'] = True
                    return result
            
            # Strategy 3: If all fails, return what we could extract
            result['error'] = "Could not extract sufficient metadata from PDF"
            print("❌ All extraction strategies failed")
            return result
            
        except Exception as e:
            result['error'] = str(e)
            print(f"❌ Error during metadata extraction: {e}")
            return result
    
    def search_crossref_by_title(self, title: str) -> Optional[Dict[str, str]]:
        """Search CrossRef by paper title"""
        try:
            # Clean title for searching
            clean_title = self.clean_title_for_search(title)
            
            # URL encode the title
            encoded_title = urllib.parse.quote(clean_title)
            
            # Search CrossRef
            search_url = f"{self.crossref_base_url}?query.title={encoded_title}&rows=5&sort=score&order=desc"
            
            print(f"🌐 Querying CrossRef with title: {clean_title[:50]}...")
            response = self.session.get(search_url, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            items = data.get('message', {}).get('items', [])
            
            if not items:
                print("❌ No results from CrossRef title search")
                return None
            
            # Find best match based on title similarity
            best_match = self.find_best_title_match(clean_title, items)
            if best_match:
                # Extract metadata from best match
                result = {
                    'title': self.extract_title(best_match),
                    'authors': self.extract_authors(best_match),
                    'journal': self.extract_journal(best_match),
                    'year': self.extract_year(best_match),
                    'doi': best_match.get('DOI', ''),
                    'abstract': self.extract_abstract(best_match),
                    'license': self.extract_license(best_match),
                    'url': self.extract_url(best_match)
                }
                
                print("✅ CrossRef title search returned metadata successfully")
                print(f"   Matched title: {result['title'][:50]}{'...' if len(result['title']) > 50 else ''}")
                print(f"   Authors: {result['authors'][:50]}{'...' if len(result['authors']) > 50 else ''}")
                print(f"   Journal: {result['journal']}")
                print(f"   Year: {result['year']}")
                if result['license']:
                    print(f"   License: {result['license']}")
                
                return result
            else:
                print("❌ No good title match found in CrossRef results")
                return None
                
        except Exception as e:
            print(f"❌ CrossRef title search error: {e}")
            return None
    
    def clean_title_for_search(self, title: str) -> str:
        """Clean title for better CrossRef searching"""
        # Remove common PDF artifacts
        title = re.sub(r'\n+', ' ', title)  # Replace newlines with spaces
        title = re.sub(r'\s+', ' ', title)  # Normalize whitespace
        title = title.strip()
        
        # Remove page numbers and other artifacts
        title = re.sub(r'\b\d+\b', '', title)  # Remove standalone numbers
        title = re.sub(r'[^\w\s\-:.]', '', title)  # Keep only letters, spaces, hyphens, colons, periods
        title = re.sub(r'\s+', ' ', title).strip()  # Normalize whitespace again
        
        return title
    
    def find_best_title_match(self, search_title: str, items: List[Dict]) -> Optional[Dict]:
        """Find the best matching paper based on title similarity"""
        search_words = set(search_title.lower().split())
        best_match = None
        best_score = 0
        
        for item in items:
            # Get title from CrossRef result
            item_titles = item.get('title', [])
            if not item_titles:
                continue
                
            item_title = item_titles[0].lower()
            item_words = set(item_title.split())
            
            # Calculate similarity score (Jaccard similarity)
            if search_words and item_words:
                intersection = len(search_words.intersection(item_words))
                union = len(search_words.union(item_words))
                score = intersection / union if union > 0 else 0
                
                # Boost score if titles are very similar in length
                length_ratio = min(len(search_title), len(item_title)) / max(len(search_title), len(item_title))
                if length_ratio > 0.8:
                    score *= 1.2
                
                if score > best_score and score > 0.3:  # Minimum similarity threshold
                    best_score = score
                    best_match = item
        
        if best_match:
            print(f"🎯 Best match score: {best_score:.2f}")
        
        return best_match
    
    def extract_doi_from_pdf(self, pdf_path: str) -> Optional[str]:
        """Extract DOI from PDF text content"""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text_content = ""
                
                # Extract text from first few pages (DOI usually on first page)
                for page_num in range(min(3, len(reader.pages))):
                    page = reader.pages[page_num]
                    text_content += page.extract_text() + "\n"
                
                # DOI patterns to search for
                doi_patterns = [
                    r'doi[:\s]*([10]\.\d{4,}[^\s,;\.]+)',
                    r'DOI:\s*([10]\.\d{4,}[^\s,;\.]+)',
                    r'https://doi\.org/([10]\.\d{4,}[^\s,;\.]+)',
                    r'http://dx\.doi\.org/([10]\.\d{4,}[^\s,;\.]+)',
                    r'dx\.doi\.org/([10]\.\d{4,}[^\s,;\.]+)',
                    r'\b([10]\.\d{4,}/[^\s,;\.]+)'
                ]
                
                for pattern in doi_patterns:
                    match = re.search(pattern, text_content, re.IGNORECASE)
                    if match:
                        doi = match.group(1) if match.lastindex else match.group(0)
                        doi = doi.rstrip('.,;')
                        if self.validate_doi(doi):
                            print(f"✅ Found valid DOI in PDF: {doi}")
                            return doi
                
                return None
                
        except Exception as e:
            print(f"❌ Error extracting DOI from PDF: {e}")
            return None
    
    def validate_doi(self, doi: str) -> bool:
        """Validate DOI format"""
        doi_regex = r'^10\.\d{4,}/.+$'
        return bool(re.match(doi_regex, doi))
    
    def lookup_doi_crossref(self, doi: str) -> Optional[Dict[str, str]]:
        """Lookup paper metadata using CrossRef API"""
        try:
            print(f"🌐 Querying CrossRef API for DOI: {doi}")
            url = f"{self.crossref_base_url}/{doi}"
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            work = data.get('message', {})
            
            if not work:
                print("❌ No work data returned from CrossRef")
                return None
            
            # Extract metadata from CrossRef response
            result = {
                'title': self.extract_title(work),
                'authors': self.extract_authors(work),
                'journal': self.extract_journal(work),
                'year': self.extract_year(work),
                'doi': doi,
                'abstract': self.extract_abstract(work),
                'license': self.extract_license(work),
                'url': self.extract_url(work)
            }
            
            print("✅ CrossRef API returned metadata successfully")
            if result['license']:
                print(f"   License: {result['license']}")
            return result
            
        except Exception as e:
            print(f"❌ CrossRef API error: {e}")
            return None
    
    def extract_title(self, work: Dict) -> str:
        """Extract title from CrossRef work data"""
        titles = work.get('title', [])
        if titles and isinstance(titles, list) and len(titles) > 0:
            return titles[0].strip()
        return ''
    
    def extract_authors(self, work: Dict) -> str:
        """Extract ALL authors from CrossRef work data"""
        authors = work.get('author', [])
        if not authors:
            return ''
        
        author_names = []
        
        for author in authors:
            given = author.get('given', '').strip()
            family = author.get('family', '').strip()
            
            if family:
                if given:
                    # Use full given name, not just initials
                    full_name = f"{given} {family}"
                    author_names.append(full_name)
                else:
                    author_names.append(family)
            elif given:
                # Sometimes only given name is provided
                author_names.append(given)
        
        # Return comma-separated list of all authors
        result = ', '.join(author_names)
        return result
    
    def extract_journal(self, work: Dict) -> str:
        """Extract journal name from CrossRef work data"""
        # Try container-title first (journal name)
        container_title = work.get('container-title', [])
        if container_title and isinstance(container_title, list) and len(container_title) > 0:
            return container_title[0].strip()
        
        # Fallback to publisher
        publisher = work.get('publisher', '')
        return publisher.strip() if publisher else ''
    
    def extract_year(self, work: Dict) -> str:
        """Extract publication year from CrossRef work data"""
        # Try published-print first, then published-online, then created
        date_fields = ['published-print', 'published-online', 'created']
        
        for field in date_fields:
            date_parts = work.get(field, {}).get('date-parts', [])
            if date_parts and len(date_parts) > 0 and len(date_parts[0]) > 0:
                year = date_parts[0][0]
                return str(year) if year else ''
        
        return ''
    
    def extract_abstract(self, work: Dict) -> str:
        """Extract abstract from CrossRef work data"""
        abstract = work.get('abstract', '')
        if abstract:
            # Clean up HTML tags that might be in the abstract
            abstract = re.sub(r'<[^>]+>', '', abstract)
            abstract = abstract.strip()
        
        return abstract
    
    def extract_license(self, work: Dict) -> str:
        """Extract license information from CrossRef work data"""
        licenses = work.get('license', [])
        if licenses and isinstance(licenses, list):
            for license_info in licenses:
                if isinstance(license_info, dict):
                    # Try to get license URL
                    license_url = license_info.get('URL', '')
                    if license_url:
                        # Common license patterns
                        if 'creativecommons.org/licenses/by/4.0' in license_url:
                            return 'Creative Commons Attribution 4.0 International (CC BY 4.0)'
                        elif 'creativecommons.org/licenses/by/3.0' in license_url:
                            return 'Creative Commons Attribution 3.0 Unported (CC BY 3.0)'
                        elif 'creativecommons.org/licenses/by/' in license_url:
                            return 'Creative Commons Attribution (CC BY)'
                        elif 'creativecommons.org/licenses/by-sa/' in license_url:
                            return 'Creative Commons Attribution-ShareAlike (CC BY-SA)'
                        elif 'creativecommons.org/licenses/by-nc/' in license_url:
                            return 'Creative Commons Attribution-NonCommercial (CC BY-NC)'
                        elif 'creativecommons.org/licenses/by-nd/' in license_url:
                            return 'Creative Commons Attribution-NoDerivatives (CC BY-ND)'
                        elif 'creativecommons.org' in license_url:
                            return 'Creative Commons License'
                        else:
                            return license_url
        return ''
    
    def extract_url(self, work: Dict) -> str:
        """Extract paper URL from CrossRef work data"""
        # Try DOI URL first
        doi = work.get('DOI', '')
        if doi:
            return f"https://doi.org/{doi}"
        
        # Try URL field
        url = work.get('URL', '')
        if url:
            return url
        
        return ''
    
    def extract_from_pdf_direct(self, pdf_path: str) -> Optional[Dict[str, str]]:
        """Extract metadata directly from PDF properties and text"""
        try:
            result = {
                'title': '',
                'authors': '',
                'journal': '',
                'year': '',
                'doi': '',
                'abstract': '',
                'license': '',
                'url': ''
            }
            
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                # Try PDF metadata first
                if reader.metadata:
                    if reader.metadata.title:
                        result['title'] = reader.metadata.title.strip()
                    if reader.metadata.author:
                        result['authors'] = reader.metadata.author.strip()
                
                # Extract text content for further parsing
                text_content = ""
                for page_num in range(min(3, len(reader.pages))):
                    page = reader.pages[page_num]
                    text_content += page.extract_text() + "\n"
                
                # Try to find title if not in metadata
                if not result['title']:
                    title_match = self.extract_title_from_text(text_content)
                    if title_match:
                        result['title'] = title_match
                
                # Try to find authors if not in metadata
                if not result['authors']:
                    authors_match = self.extract_authors_from_text(text_content)
                    if authors_match:
                        result['authors'] = authors_match
                
                # Try to find year
                year_match = self.extract_year_from_text(text_content)
                if year_match:
                    result['year'] = year_match
                
                # Try to find journal/conference
                journal_match = self.extract_journal_from_text(text_content)
                if journal_match:
                    result['journal'] = journal_match
                
                # Try to find abstract
                abstract_match = self.extract_abstract_from_text(text_content)
                if abstract_match:
                    result['abstract'] = abstract_match
                
                return result if result['title'] else None
                
        except Exception as e:
            print(f"❌ Error in direct PDF extraction: {e}")
            return None
    
    def extract_title_from_text(self, text: str) -> Optional[str]:
        """Extract title from PDF text content"""
        lines = text.split('\n')
        
        # Title is usually one of the first few lines, and is often longer than other lines
        for i, line in enumerate(lines[:10]):
            line = line.strip()
            if (len(line) > 20 and  # Reasonable title length
                not line.lower().startswith(('abstract', 'introduction', 'keywords')) and
                not re.match(r'^\d+\.', line) and  # Not numbered section
                not line.isupper() and  # Not all caps (likely header)
                len(line.split()) > 3):  # More than 3 words
                return line
        
        return None
    
    def extract_authors_from_text(self, text: str) -> Optional[str]:
        """Extract authors from PDF text content"""
        lines = text.split('\n')
        
        # Look for author patterns after title
        for i, line in enumerate(lines[:15]):
            line = line.strip()
            
            # Check for common author patterns
            if (re.search(r'^[A-Z][a-z]+ [A-Z][a-z]+', line) or  # FirstName LastName
                re.search(r'^[A-Z]\. [A-Z][a-z]+', line) or      # F. LastName  
                ',' in line and len(line.split(',')) > 1):        # Name, Name format
                
                # Clean and return
                authors = re.sub(r'[0-9*†‡§¶]', '', line)  # Remove superscript markers
                authors = authors.strip()
                if len(authors) > 5:  # Minimum reasonable length
                    return authors
        
        return None
    
    def extract_year_from_text(self, text: str) -> Optional[str]:
        """Extract publication year from PDF text"""
        # Look for 4-digit years (likely publication years)
        year_pattern = r'\b(19|20)\d{2}\b'
        matches = re.findall(year_pattern, text)
        
        if matches:
            # Return the most recent reasonable year
            years = [int(match + year[-2:]) for match in matches for year in re.findall(r'\d{2}', text) if 1990 <= int(match + year[-2:]) <= 2024]
            if years:
                return str(max(years))
        
        return None
    
    def extract_journal_from_text(self, text: str) -> Optional[str]:
        """Extract journal/conference name from PDF text"""
        # Common journal/conference patterns
        journal_patterns = [
            r'(?:Published in|Proceedings of|Journal of|Conference on|In:)\s*([^.\n]+)',
            r'([A-Z][a-z]+ (?:Journal|Proceedings|Conference|Review|Letters))',
        ]
        
        for pattern in journal_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                journal = match.group(1).strip()
                if len(journal) > 5:  # Minimum reasonable length
                    return journal
        
        return None
    
    def extract_abstract_from_text(self, text: str) -> Optional[str]:
        """Extract abstract from PDF text"""
        # Look for abstract section
        abstract_pattern = r'(?:ABSTRACT|Abstract)\s*[:\-]?\s*(.*?)(?:\n\s*\n|\n\s*(?:1\.|I\.|INTRODUCTION|Introduction|Keywords|KEYWORDS))'
        
        match = re.search(abstract_pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            abstract = match.group(1).strip()
            # Clean up the abstract
            abstract = re.sub(r'\s+', ' ', abstract)  # Normalize whitespace
            abstract = abstract[:1000]  # Limit length
            if len(abstract) > 50:  # Minimum reasonable length
                return abstract
        
        return None

# Convenience function for direct use
def extract_pdf_metadata(pdf_path: str) -> Dict[str, Any]:
    """Extract metadata from PDF file"""
    extractor = PDFMetadataExtractor()
    return extractor.extract_metadata(pdf_path)