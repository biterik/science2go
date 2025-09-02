"""
Chunking Configuration for Science2Go
Optimized for handling 100+ page academic papers
"""

# Chunking parameters optimized for Gemini Pro
CHUNKING_CONFIG = {
    # Maximum characters per chunk (safe for Gemini Pro ~8K tokens)
    "max_chunk_size": 30000,
    
    # Overlap between chunks to maintain context
    "overlap_size": 1000,
    
    # Minimum chunk size (prevent tiny chunks)
    "min_chunk_size": 5000,
    
    # Delay between chunk processing (API rate limiting)
    "chunk_delay_seconds": 1.0,
    
    # Maximum retries for failed chunks
    "max_retries": 3,
    
    # Retry delay (exponential backoff)
    "retry_delay_seconds": 2.0,
}

# Text patterns for finding good chunk boundaries (in order of preference)
CHUNK_BREAK_PATTERNS = [
    # Section breaks (highest priority)
    r'\n\n#+\s',                    # Markdown headers (## Section)
    r'\n\n\d+\.?\s+[A-Z]',         # Numbered sections (1. Introduction)
    r'\n\n[A-Z][A-Za-z\s]+:?\n',   # Section titles (ABSTRACT\n)
    
    # Subsection breaks
    r'\n\n\d+\.\d+\.?\s',          # Numbered subsections (1.1. Method)
    r'\n\n[a-z]\)\s',              # Lettered subsections (a) Results)
    
    # Paragraph breaks (medium priority)
    r'\n\n[A-Z]',                  # Double newline + capital letter
    r'\n\n\w',                     # Any double newline + word
    
    # Sentence breaks (lowest priority - last resort)
    r'\.[\s\n]+[A-Z]',            # Period + space/newline + capital
    r'\.\s+However,',              # Common transition words
    r'\.\s+Furthermore,',
    r'\.\s+Moreover,',
    r'\.\s+Therefore,',
]

# Document size estimates (for user feedback)
DOCUMENT_SIZE_ESTIMATES = {
    "small": (0, 50000),         # 0-50K chars (~12 pages)
    "medium": (50000, 150000),   # 50-150K chars (~12-37 pages)  
    "large": (150000, 400000),   # 150-400K chars (~37-100 pages)
    "huge": (400000, float('inf')),  # 400K+ chars (100+ pages)
}

def get_document_size_category(char_count: int) -> str:
    """Get document size category for user feedback"""
    for category, (min_size, max_size) in DOCUMENT_SIZE_ESTIMATES.items():
        if min_size <= char_count < max_size:
            return category
    return "unknown"

def estimate_processing_time(char_count: int) -> int:
    """Estimate processing time in seconds based on character count"""
    # Based on observed performance: ~1000 chars per second including API delays
    base_time = char_count / 800  # Conservative estimate
    
    # Add overhead for chunking
    if char_count > CHUNKING_CONFIG["max_chunk_size"]:
        num_chunks = (char_count // CHUNKING_CONFIG["max_chunk_size"]) + 1
        chunk_overhead = num_chunks * CHUNKING_CONFIG["chunk_delay_seconds"]
        base_time += chunk_overhead
    
    return int(base_time)

def estimate_page_count(char_count: int) -> int:
    """Estimate page count from character count"""
    # Academic papers: roughly 2000-2500 chars per page
    return max(1, char_count // 2200)