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

def filter_documentation_sentences(sentences: List[str], target_keywords: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """
    Filter sentences to only keep those matching target documentation keywords.
    Group results by document type.
    
    Args:
        sentences (List[str]): List of extracted sentences
        target_keywords (List[Dict[str, Any]]): List of target documentation items with their keywords
        
    Returns:
        Dict[str, List[str]]: Filtered sentences grouped by document type
    """
    result = {}
    
    for sentence in sentences:
        if not sentence or len(sentence) < 15:
            continue
            
        sentence_lower = sentence.lower()
        
        # Check against all target documentation items
        for doc_item in target_keywords:
            item_name = doc_item["name"]
            if item_name.lower() in sentence_lower or any(kw.lower() in sentence_lower for kw in doc_item["keywords"]):
                if item_name not in result:
                    result[item_name] = []
                
                # Don't add duplicates
                if sentence not in result[item_name]:
                    result[item_name].append(sentence)
    
    return result

def contains_target_document_keyword(text: str, target_keywords: List[Dict[str, Any]]) -> bool:
    """
    Checks if text contains any of the target documentation keywords.
    
    Args:
        text (str): The text to check.
        target_keywords (List[Dict[str, Any]]): List of target documentation items with their keywords.
        
    Returns:
        bool: True if text contains any target keyword, False otherwise.
    """
    if not text:
        return False
    
    text_lower = text.lower()
    
    for item in target_keywords:
        if item["name"].lower() in text_lower:
            return True
        
        if any(keyword.lower() in text_lower for keyword in item["keywords"]):
            return True
    
    return False

def extract_sentences_with_keywords(text: str, target_keywords: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """
    Extracts sentences containing target documentation keywords.
    
    Args:
        text (str): The text to analyze.
        target_keywords (List[Dict[str, Any]]): List of target documentation items with their keywords.
        
    Returns:
        Dict[str, List[str]]: Dictionary mapping document types to sentences.
    """
    if not text:
        return {}
    
    # Extract sentences
    sentences = re.split(r'[.!?]\s+', text)
    results = {}
    
    # Check each sentence for target keywords
    for sentence in sentences:
        sentence_lower = sentence.lower()
        
        for item in target_keywords:
            item_name = item["name"]
            
            # Check if sentence contains the item name or any of its keywords
            if item_name.lower() in sentence_lower or any(kw.lower() in sentence_lower for kw in item["keywords"]):
                clean_sentence = clean_text(sentence)
                
                if clean_sentence and len(clean_sentence) > 10:
                    if item_name not in results:
                        results[item_name] = []
                    
                    if clean_sentence not in results[item_name]:
                        results[item_name].append(clean_sentence)
    
    return results

def format_bullet_points(items: List[str]) -> str:
    """
    Formats a list of items as bullet points.
    
    Args:
        items (List[str]): The items to format.
        
    Returns:
        str: Formatted bullet point list.
    """
    return "\n".join(f"• {item}" for item in items)

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

def find_matching_document_type(text: str, target_keywords: List[Dict[str, Any]]) -> Optional[str]:
    """
    Finds the matching document type for a given text.
    
    Args:
        text (str): The text to check.
        target_keywords (List[Dict[str, Any]]): List of target documentation items with their keywords.
        
    Returns:
        Optional[str]: Matching document type name or None.
    """
    if not text:
        return None
    
    text_lower = text.lower()
    
    for item in target_keywords:
        if item["name"].lower() in text_lower:
            return item["name"]
        
        for keyword in item["keywords"]:
            if keyword.lower() in text_lower:
                return item["name"]
    
    return None