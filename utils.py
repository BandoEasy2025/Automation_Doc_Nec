"""
Enhanced utility functions for the grant documentation crawler.
Added functionality for better text processing and document extraction.
"""
import logging
import os
import re
import string
import json
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
import unicodedata

logger = logging.getLogger(__name__)

def setup_logging(log_level: str = "INFO") -> None:
    """
    Set up logging configuration.
    
    Args:
        log_level (str): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")
    
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

def clean_text(text: Optional[str]) -> str:
    """
    Cleans and normalizes text for documentation extraction.
    Enhanced with better handling of Italian text and document formatting.
    
    Args:
        text (Optional[str]): The text to clean.
        
    Returns:
        str: The cleaned text.
    """
    if text is None:
        return ""
    
    text = normalize_whitespace(text)
    
    # Normalize unicode characters
    text = unicodedata.normalize('NFKC', text)
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    text = text.replace("\u00A0", " ")  # Non-breaking space
    text = text.replace("\u2022", "•")  # Bullet point
    
    # Clean up bullet points for better readability
    text = re.sub(r'•\s*([•\-*])\s*', '• ', text)  # Remove double bullets
    text = re.sub(r'([.!?])\s+([A-Z])', r'\1 \2', text)  # Fix sentence spacing
    
    # Remove excessive punctuation
    text = re.sub(r'([.!?,:;]){2,}', r'\1', text)
    
    # Normalize Italian definite articles
    text = re.sub(r'\b(l)\s+([aeiouAEIOU])', r"l'\2", text)
    
    # Fix spacing around punctuation
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    text = re.sub(r'([.,;:!?])\s+', r'\1 ', text)
    
    # Remove any bullet-points or numbering at the beginning of the text
    text = re.sub(r'^[•\-*\d]+[\.\)]*\s*', '', text)
    
    # Clean up common OCR errors often found in PDFs
    text = re.sub(r'(\w)l(\w)', r'\1i\2', text)  # Replace "l" with "i" in certain contexts
    text = text.replace('c0n', 'con')  # Fix common OCR error
    text = text.replace('d1', 'di')    # Fix common OCR error
    
    # Normalize document-related terms
    text = re.sub(r'\b[Aa]llegat[oi]\b', 'allegato', text)
    text = re.sub(r'\b[Dd]ocument[oi]\b', 'documento', text)
    text = re.sub(r'\b[Dd]ichiarazion[ei]\b', 'dichiarazione', text)
    text = re.sub(r'\b[Cc]ertificat[oi]\b', 'certificato', text)
    
    return text.strip()

def normalize_whitespace(text: Optional[str]) -> str:
    """
    Normalizes whitespace in text.
    
    Args:
        text (Optional[str]): The text to normalize.
        
    Returns:
        str: The text with normalized whitespace.
    """
    if text is None:
        return ""
    
    # Replace multiple whitespace with a single space
    text = re.sub(r'\s+', ' ', text)
    
    # Remove leading/trailing whitespace
    return text.strip()

def sanitize_filename(filename: str) -> str:
    """
    Sanitizes a filename to ensure it's valid across operating systems.
    
    Args:
        filename (str): The filename to sanitize.
        
    Returns:
        str: A sanitized filename.
    """
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    sanitized = ''.join(c for c in filename if c in valid_chars)
    
    # Replace spaces with underscores
    sanitized = sanitized.replace(' ', '_')
    
    # Limit length
    if len(sanitized) > 255:
        base, ext = os.path.splitext(sanitized)
        sanitized = base[:255 - len(ext)] + ext
    
    # Ensure we have something
    if not sanitized:
        sanitized = "unnamed_file"
    
    return sanitized

def is_valid_url(url: str) -> bool:
    """
    Checks if a URL is valid.
    
    Args:
        url (str): The URL to check.
        
    Returns:
        bool: True if the URL is valid, False otherwise.
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def truncate_text(text: str, max_length: int = 1000) -> str:
    """
    Truncates text to a maximum length while preserving complete sentences.
    
    Args:
        text (str): The text to truncate.
        max_length (int): Maximum length of the truncated text.
        
    Returns:
        str: The truncated text.
    """
    if not text or len(text) <= max_length:
        return text
    
    # Find the last period before max_length
    last_period = text[:max_length].rfind('.')
    
    # If no period found, truncate at max_length
    if last_period == -1:
        return text[:max_length] + "..."
    
    # Truncate at the last period before max_length
    return text[:last_period + 1]

def extract_document_info(text: str, document_keywords: List[str], 
                         doc_section_patterns: List[str] = None) -> Dict[str, List[str]]:
    """
    Extracts information about documentation requirements from text.
    
    Args:
        text (str): The text to analyze.
        document_keywords (List[str]): Keywords related to documentation.
        doc_section_patterns (List[str], optional): Patterns to identify documentation sections.
        
    Returns:
        Dict[str, List[str]]: Found documentation information categorized.
    """
    if not text or not document_keywords:
        return {}
    
    found_docs = {
        "general": [],
        "sections": [],
        "specific": {}
    }
    
    # Tokenize text into sentences for analysis
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # Default section patterns if none provided
    if not doc_section_patterns:
        doc_section_patterns = [
            r'document[azio\-\s]+necessari[ao]',
            r'allegat[io]',
            r'modulistic[ao]',
            r'presentazione[\s]+(?:della[\s]+)?domanda'
        ]
    
    # First pass: look for sentences with documentation keywords
    for sentence in sentences:
        sentence_lower = sentence.lower()
        
        # Check for documentation keywords
        if any(keyword in sentence_lower for keyword in document_keywords):
            clean_sentence = clean_text(sentence)
            if clean_sentence and len(clean_sentence) > 15:
                found_docs["general"].append(clean_sentence)
                
                # If it's a section header or list intro, add as section
                if any(re.search(pattern, sentence_lower) for pattern in doc_section_patterns):
                    found_docs["sections"].append(clean_sentence)
                    
                    # Check next few sentences for list items
                    try:
                        sentence_idx = sentences.index(sentence)
                        for i in range(sentence_idx + 1, min(sentence_idx + 6, len(sentences))):
                            next_sent = sentences[i]
                            if re.match(r'^[\s]*[-•*]\s|^\d+[.)\s]', next_sent):
                                clean_next = clean_text(next_sent)
                                if clean_next:
                                    found_docs["general"].append(clean_next)
                    except ValueError:
                        pass  # If sentence not found in list (unlikely)
    
    # Second pass: look for specific document types
    common_docs = {
        "visura camerale": ["visura", "camerale", "CCIAA"],
        "DURC": ["DURC", "regolarità contributiva"],
        "business plan": ["business plan", "piano aziendale"],
        "dichiarazione sostitutiva": ["dichiarazione sostitutiva", "autocertificazione"],
        "curriculum vitae": ["curriculum", "CV"],
        "piano finanziario": ["piano finanziar", "budget", "preventivo"],
        "scheda progettuale": ["scheda progett", "scheda tecnica"],
        "fatture": ["fattur", "spesa", "giustificativ"],
        "quietanze": ["quietanz", "pagament", "ricevut"]
    }
    
    for doc_type, keywords in common_docs.items():
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(keyword in sentence_lower for keyword in keywords):
                clean_sentence = clean_text(sentence)
                if clean_sentence and len(clean_sentence) > 15:
                    if doc_type not in found_docs["specific"]:
                        found_docs["specific"][doc_type] = []
                    found_docs["specific"][doc_type].append(clean_sentence)
    
    return found_docs

def format_documentation_output(doc_info: Dict[str, Any], grant_title: str = "") -> str:
    """
    Formats documentation information into a structured output.
    
    Args:
        doc_info (Dict[str, Any]): The documentation information to format.
        grant_title (str, optional): The grant title.
        
    Returns:
        str: Formatted documentation information.
    """
    if not doc_info:
        return "Nessuna informazione sulla documentazione necessaria è stata trovata."
    
    output_parts = []
    
    # Add title
    if grant_title:
        output_parts.append(f"# Documentazione Necessaria per {grant_title}")
    else:
        output_parts.append("# Documentazione Necessaria")
    
    # Add sections if available
    if doc_info.get("sections"):
        output_parts.append("\n## Sezioni di Documentazione")
        for section in doc_info["sections"]:
            output_parts.append(f"- {section}")
    
    # Add specific document types
    if doc_info.get("specific"):
        output_parts.append("\n## Documenti Specifici")
        
        for doc_type, sentences in doc_info["specific"].items():
            output_parts.append(f"\n### {doc_type.capitalize()}")
            for sentence in sentences:
                output_parts.append(f"- {sentence}")
    
    # Add general documentation if available
    if doc_info.get("general") and (not doc_info.get("sections") and not doc_info.get("specific")):
        output_parts.append("\n## Informazioni Generali sulla Documentazione")
        for item in doc_info["general"]:
            output_parts.append(f"- {item}")
    
    # Add timestamp
    from datetime import datetime
    output_parts.append(f"\n_Ultimo aggiornamento: {datetime.now().strftime('%d/%m/%Y %H:%M')}_")
    
    return "\n".join(output_parts)

def save_extracted_data(data: Dict[str, Any], filename: str) -> None:
    """
    Saves extracted data to a JSON file for later analysis or debugging.
    
    Args:
        data (Dict[str, Any]): The data to save.
        filename (str): Filename to save to.
    """
    try:
        # Create output directory if it doesn't exist
        os.makedirs("output", exist_ok=True)
        
        filepath = os.path.join("output", sanitize_filename(filename))
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Successfully saved extracted data to {filepath}")
    except Exception as e:
        logger.error(f"Error saving extracted data: {e}")

def extract_common_patterns(texts: List[str], min_occurrences: int = 2) -> List[str]:
    """
    Extracts common text patterns from a list of texts.
    Useful for finding recurring document requirements.
    
    Args:
        texts (List[str]): List of text strings to analyze.
        min_occurrences (int): Minimum number of occurrences to consider a pattern common.
        
    Returns:
        List[str]: List of common patterns found.
    """
    if not texts or len(texts) < min_occurrences:
        return []
    
    # Normalize and tokenize texts
    normalized_texts = [clean_text(text).lower() for text in texts]
    
    # Extract word sequences (3-5 words) from texts
    patterns = {}
    for text in normalized_texts:
        words = text.split()
        if len(words) < 3:
            continue
            
        # Generate 3-5 word sequences
        for n in range(3, min(6, len(words) + 1)):
            for i in range(len(words) - n + 1):
                pattern = " ".join(words[i:i+n])
                patterns[pattern] = patterns.get(pattern, 0) + 1
    
    # Filter patterns by occurrence and significance
    common_patterns = []
    for pattern, count in patterns.items():
        if count >= min_occurrences and len(pattern) > 10:
            # Check if this pattern is not just part of a longer common pattern
            is_unique = True
            for existing in common_patterns:
                if pattern in existing:
                    is_unique = False
                    break
            if is_unique:
                common_patterns.append(pattern)
    
    return common_patterns
# """
# Utility functions for the grant documentation crawler.
# """
# import logging
# import os
# import re
# import string
# from typing import Optional
# from urllib.parse import urlparse

# logger = logging.getLogger(__name__)

# def setup_logging(log_level: str = "INFO") -> None:
#     """
#     Set up logging configuration.
    
#     Args:
#         log_level (str): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
#     """
#     numeric_level = getattr(logging, log_level.upper(), None)
#     if not isinstance(numeric_level, int):
#         raise ValueError(f"Invalid log level: {log_level}")
    
#     logging.basicConfig(
#         level=numeric_level,
#         format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
#         datefmt="%Y-%m-%d %H:%M:%S",
#     )

# def clean_text(text: Optional[str]) -> str:
#     """
#     Cleans and normalizes text for documentation extraction.
    
#     Args:
#         text (Optional[str]): The text to clean.
        
#     Returns:
#         str: The cleaned text.
#     """
#     if text is None:
#         return ""
    
#     text = normalize_whitespace(text)
    
#     # Normalize unicode characters
#     text = text.replace("\u2018", "'").replace("\u2019", "'")
#     text = text.replace("\u201c", '"').replace("\u201d", '"')
#     text = text.replace("\u2013", "-").replace("\u2014", "-")
#     text = text.replace("\u00A0", " ")  # Non-breaking space
#     text = text.replace("\u2022", "•")  # Bullet point
    
#     # Clean up bullet points for better readability
#     text = re.sub(r'•\s*([•\-*])\s*', '• ', text)  # Remove double bullets
#     text = re.sub(r'([.!?])\s+([A-Z])', r'\1 \2', text)  # Fix sentence spacing
    
#     # Remove excessive punctuation
#     text = re.sub(r'([.!?,:;]){2,}', r'\1', text)
    
#     # Normalize Italian definite articles
#     text = re.sub(r'\b(l)\s+([aeiouAEIOU])', r"l'\2", text)
    
#     # Fix spacing around punctuation
#     text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    
#     # Remove any bullet-points or numbering at the beginning of the text
#     text = re.sub(r'^[•\-*\d]+[\.\)]*\s*', '', text)
    
#     return text

# def normalize_whitespace(text: Optional[str]) -> str:
#     """
#     Normalizes whitespace in text.
    
#     Args:
#         text (Optional[str]): The text to normalize.
        
#     Returns:
#         str: The text with normalized whitespace.
#     """
#     if text is None:
#         return ""
    
#     # Replace multiple whitespace with a single space
#     text = re.sub(r'\s+', ' ', text)
    
#     # Remove leading/trailing whitespace
#     return text.strip()

# def sanitize_filename(filename: str) -> str:
#     """
#     Sanitizes a filename to ensure it's valid across operating systems.
    
#     Args:
#         filename (str): The filename to sanitize.
        
#     Returns:
#         str: A sanitized filename.
#     """
#     valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
#     sanitized = ''.join(c for c in filename if c in valid_chars)
    
#     # Replace spaces with underscores
#     sanitized = sanitized.replace(' ', '_')
    
#     # Limit length
#     if len(sanitized) > 255:
#         base, ext = os.path.splitext(sanitized)
#         sanitized = base[:255 - len(ext)] + ext
    
#     # Ensure we have something
#     if not sanitized:
#         sanitized = "unnamed_file"
    
#     return sanitized

# def is_valid_url(url: str) -> bool:
#     """
#     Checks if a URL is valid.
    
#     Args:
#         url (str): The URL to check.
        
#     Returns:
#         bool: True if the URL is valid, False otherwise.
#     """
#     try:
#         result = urlparse(url)
#         return all([result.scheme, result.netloc])
#     except:
#         return False

# def truncate_text(text: str, max_length: int = 1000) -> str:
#     """
#     Truncates text to a maximum length while preserving complete sentences.
    
#     Args:
#         text (str): The text to truncate.
#         max_length (int): Maximum length of the truncated text.
        
#     Returns:
#         str: The truncated text.
#     """
#     if not text or len(text) <= max_length:
#         return text
    
#     # Find the last period before max_length
#     last_period = text[:max_length].rfind('.')
    
#     # If no period found, truncate at max_length
#     if last_period == -1:
#         return text[:max_length] + "..."
    
#     # Truncate at the last period before max_length
#     return text[:last_period + 1]