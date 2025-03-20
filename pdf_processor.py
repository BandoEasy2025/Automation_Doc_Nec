"""
Handles downloading and processing PDF files to extract relevant text.
Enhanced to better identify documentation requirements.
"""
#updated 11:51

import logging
import os
import re
import tempfile
from typing import Dict, List, Any, Optional, Tuple
import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from pdfminer.high_level import extract_text
from io import BytesIO

import config
from utils import clean_text, sanitize_filename, normalize_whitespace

logger = logging.getLogger(__name__)

class PDFProcessor:
    """Downloads and processes PDF files to extract relevant information."""
    
    def __init__(self):
        """Initialize the PDF processor."""
        self.session = requests.Session()
        self.session.headers.update(config.REQUEST_HEADERS)
        
        # Create download directory if it doesn't exist
        os.makedirs(config.PDF_DOWNLOAD_DIR, exist_ok=True)
        
        # Documentation-specific patterns for more targeted extraction
        self.doc_keywords = [
            'document', 'allegat', 'modulistic', 'certificaz', 
            'richiest', 'presentare', 'obbligo', 'necessari',
            'domanda', 'application', 'richiesta', 'presentazione',
            'firma', 'signature', 'digitale', 'copia', 'identity',
            'identità', 'dichiarazione', 'declaration', 'formulario',
            'modulo', 'form', 'attestazione', 'certification'
        ]
        
        # Specific section title patterns to look for in PDFs
        self.doc_section_patterns = [
            r'document[azio\-\s]+necessari[ao]',
            r'allegat[io][\s]+(?:richiest[io]|necessari[io])',
            r'documentazione[\s]+da[\s]+(?:presentare|allegare)',
            r'documenti[\s]+(?:da[\s]+)?(?:presentare|allegare)',
            r'(?:modalit[aà]|procedura)[\s]+(?:di[\s]+)?presentazione',
            r'(?:domanda|istanza)[\s]+di[\s]+partecipazione',
            r'modulistic[ao]',
            r'certificazion[ei][\s]+(?:necessari[ae]|richiest[ae])',
            r'prerequisiti[\s]+documentali'
        ]
    
    @retry(
        stop=stop_after_attempt(config.MAX_RETRIES),
        wait=wait_exponential(multiplier=config.RETRY_BACKOFF)
    )
    def download_pdf(self, url: str) -> Optional[str]:
        """
        Downloads a PDF file from a URL.
        
        Args:
            url (str): URL of the PDF to download.
            
        Returns:
            Optional[str]: Path to the downloaded file or None if download failed.
        """
        try:
            # Send a HEAD request first to check the file size
            head_response = self.session.head(url, timeout=config.REQUEST_TIMEOUT, allow_redirects=True)
            
            # Check if the URL is actually a PDF
            content_type = head_response.headers.get('Content-Type', '').lower()
            if 'application/pdf' not in content_type and not url.lower().endswith('.pdf'):
                logger.warning(f"URL {url} is not a PDF: {content_type}")
                return None
            
            # Check file size
            content_length = head_response.headers.get('Content-Length')
            if content_length and int(content_length) > config.MAX_PDF_SIZE:
                logger.warning(f"PDF at {url} is too large ({content_length} bytes)")
                return None
            
            # Download the PDF
            response = self.session.get(url, timeout=config.REQUEST_TIMEOUT, stream=True)
            response.raise_for_status()
            
            # Create a safe filename from the URL
            filename = sanitize_filename(os.path.basename(url))
            if not filename.lower().endswith('.pdf'):
                filename += '.pdf'
                
            # Save to file
            filepath = os.path.join(config.PDF_DOWNLOAD_DIR, filename)
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Successfully downloaded PDF from {url} to {filepath}")
            return filepath
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading PDF from {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading PDF from {url}: {e}")
            return None
    
    def extract_text_from_pdf(self, pdf_path: str) -> Optional[str]:
        """
        Extracts text content from a PDF file.
        
        Args:
            pdf_path (str): Path to the PDF file.
            
        Returns:
            Optional[str]: Extracted text content or None if extraction failed.
        """
        try:
            logger.info(f"Extracting text from {pdf_path}")
            text = extract_text(pdf_path)
            
            if not text:
                logger.warning(f"No text content extracted from {pdf_path}")
                return None
                
            # Clean and normalize the extracted text
            text = normalize_whitespace(text)
            logger.info(f"Successfully extracted {len(text)} characters from {pdf_path}")
            return text
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {e}")
            return None
    
    def process_pdf_content(self, pdf_text: str, context: str = "") -> Dict[str, Any]:
        """
        Processes PDF text to extract structured information.
        Enhanced to better identify documentation requirements.
        
        Args:
            pdf_text (str): The text content of the PDF.
            context (str): Context about the PDF from the link.
            
        Returns:
            Dict[str, Any]: Structured information extracted from the PDF.
        """
        if not pdf_text:
            return {}
        
        result = {
            'context': context,
            'main_content': pdf_text[:5000],  # First part of content
            'sections': {},
            'lists': [],
            'tables': []
        }
        
        # Extract documentation-specific content first
        self._extract_documentation_content(pdf_text, result)
        
        # Extract sections based on heading patterns
        section_pattern = re.compile(r'(?:\n|\r\n)([A-Z][A-Za-z0-9\s\-,]+)[\.\:]?(?:\n|\r\n)')
        sections = section_pattern.findall(pdf_text)
        
        for section in sections:
            section_title = section.strip()
            if not section_title or len(section_title) < 3 or len(section_title) > 100:
                continue
                
            # Find section content - from this section title to the next
            start_idx = pdf_text.find(section)
            if start_idx == -1:
                continue
                
            end_idx = pdf_text.find('\n', start_idx + len(section))
            if end_idx == -1:
                continue
                
            # Find the next section or the end of document
            next_section_idx = pdf_text.find('\n', end_idx + 1)
            if next_section_idx == -1:
                section_content = pdf_text[end_idx:].strip()
            else:
                section_content = pdf_text[end_idx:next_section_idx].strip()
            
            if section_content:
                result['sections'][section_title] = clean_text(section_content)
        
        # Extract lists (bullet points, numbered lists)
        list_patterns = [
            r'(?:\n|\r\n)(?:\s*[\•\-\*]\s*)([^\n]+)(?:\n|\r\n)(?:\s*[\•\-\*]\s*)([^\n]+)',  # Bullet lists
            r'(?:\n|\r\n)(?:\s*\d+[\.\)]\s*)([^\n]+)(?:\n|\r\n)(?:\s*\d+[\.\)]\s*)([^\n]+)'  # Numbered lists
        ]
        
        for pattern in list_patterns:
            list_matches = re.findall(pattern, pdf_text)
            if list_matches:
                items = [clean_text(item) for group in list_matches for item in group if clean_text(item)]
                if items:
                    result['lists'].append(items)
        
        # Extract table-like structures
        lines = pdf_text.split('\n')
        potential_table_rows = []
        
        # Look for repeated patterns of spaces or tabs that might indicate columns
        for i, line in enumerate(lines):
            if i > 0 and i < len(lines) - 1:
                if re.search(r'\s{2,}', line) and len(line.strip()) > 10:
                    potential_table_rows.append(line)
        
        if len(potential_table_rows) >= 3:  # At least 3 rows for a table
            result['tables'].append(potential_table_rows)
        
        # Extract information specifically related to grant requirements
        for term in config.SEARCH_TERMS:
            pattern = re.compile(r'(.{0,150}' + re.escape(term) + r'.{0,150})', re.IGNORECASE)
            matches = pattern.findall(pdf_text)
            
            if matches:
                term_key = term.capitalize()
                if term_key not in result:
                    result[term_key] = []
                
                for match in matches:
                    clean_match = clean_text(match)
                    if clean_match and clean_match not in result[term_key]:
                        result[term_key].append(clean_match)
        
        return result
    
    def _extract_documentation_content(self, pdf_text: str, result: Dict[str, Any]) -> None:
        """
        Specifically extracts documentation requirements from PDF text.
        
        Args:
            pdf_text (str): The PDF text content to analyze.
            result (Dict[str, Any]): The result dictionary to update.
        """
        # Initialize documentation collections if not present
        if "Documentazione" not in result:
            result["Documentazione"] = []
        
        # Try to find documentation sections
        for pattern in self.doc_section_patterns:
            # Create a regex pattern that looks for headers
            header_pattern = re.compile(r'(?:\n|\r\n)(' + pattern + r'[^\n\r]{0,50})(?:\n|\r\n)', re.IGNORECASE)
            headers = header_pattern.findall(pdf_text)
            
            for header in headers:
                header = header.strip()
                if header:
                    # Get content after the header
                    start_idx = pdf_text.find(header)
                    if start_idx == -1:
                        continue
                    
                    end_idx = start_idx + len(header)
                    
                    # Find the next section header or limit to a reasonable amount of text
                    next_header_match = re.search(r'(?:\n|\r\n)[A-Z][A-Za-z0-9\s\-,]+[\.\:]?(?:\n|\r\n)', pdf_text[end_idx:end_idx + 2000])
                    
                    if next_header_match:
                        section_content = pdf_text[end_idx:end_idx + next_header_match.start()]
                    else:
                        # Limit to a reasonable length if no next header found
                        section_content = pdf_text[end_idx:end_idx + 1500]
                    
                    # Clean and process the section content
                    section_content = clean_text(section_content)
                    
                    # Add to results
                    if section_content:
                        # Add header as a section
                        result['sections'][header] = section_content
                        
                        # Look for list-like patterns in the content
                        list_items = self._extract_list_items(section_content)
                        if list_items:
                            # Store both the raw list and add to documentation
                            result['lists'].append(list_items)
                            result["Documentazione"].extend(list_items)
                        else:
                            # Add relevant sentences to documentation
                            sentences = re.split(r'[.;]\s+', section_content)
                            for sentence in sentences:
                                if any(keyword in sentence.lower() for keyword in self.doc_keywords):
                                    clean_sentence = clean_text(sentence)
                                    if clean_sentence and len(clean_sentence) > 15:
                                        result["Documentazione"].append(clean_sentence)
        
        # Look for documentation keywords in the text even if no clear section is found
        if not result["Documentazione"]:
            # Get sentences containing documentation keywords
            for keyword in self.doc_keywords:
                pattern = re.compile(r'([^.;!?]{0,30}' + keyword + r'[^.;!?]{5,100}[.;!?])', re.IGNORECASE)
                matches = pattern.findall(pdf_text)
                
                for match in matches:
                    clean_match = clean_text(match)
                    if clean_match and len(clean_match) > 20:
                        result["Documentazione"].append(clean_match)
    
    def _extract_list_items(self, text: str) -> List[str]:
        """
        Extracts items that appear to be in a list format from text.
        
        Args:
            text (str): The text to analyze.
            
        Returns:
            List[str]: Extracted list items.
        """
        list_items = []
        
        # Look for bullet points
        bullet_pattern = re.compile(r'(?:^|\n|\s)[\•\-\*]\s+([^\n\•\-\*]+)', re.MULTILINE)
        bullet_matches = bullet_pattern.findall(text)
        if bullet_matches:
            list_items.extend([clean_text(item) for item in bullet_matches if clean_text(item)])
        
        # Look for numbered items
        numbered_pattern = re.compile(r'(?:^|\n|\s)(\d+[\.|\)])\s+([^\n]+)', re.MULTILINE)
        numbered_matches = numbered_pattern.findall(text)
        if numbered_matches:
            list_items.extend([clean_text(item[1]) for item in numbered_matches if clean_text(item[1])])
        
        # Look for dash-prefixed items
        dash_pattern = re.compile(r'(?:^|\n|\s)[-–—]\s+([^\n]+)', re.MULTILINE)
        dash_matches = dash_pattern.findall(text)
        if dash_matches:
            list_items.extend([clean_text(item) for item in dash_matches if clean_text(item)])
        
        return list_items
    
    def process_pdf(self, pdf_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Downloads and processes a PDF to extract comprehensive information.
        
        Args:
            pdf_info (Dict[str, Any]): Information about the PDF to process including URL.
            
        Returns:
            Dict[str, Any]: Extracted information from the PDF.
        """
        url = pdf_info['url']
        context = pdf_info.get('context', '')
        is_priority = pdf_info.get('priority', False)
        is_doc_related = pdf_info.get('is_doc_related', False)
        
        try:
            logger.info(f"Processing {'PRIORITY ' if is_priority else ''}{'DOC-RELATED ' if is_doc_related else ''}PDF: {url}")
            
            # Download the PDF
            pdf_path = self.download_pdf(url)
            if not pdf_path:
                return {}
                
            # Extract text from the PDF
            pdf_text = self.extract_text_from_pdf(pdf_path)
            if not pdf_text:
                return {}
            
            # Process the PDF content
            result = self.process_pdf_content(pdf_text, context)
            
            # Add metadata
            result['source'] = url
            result['filename'] = os.path.basename(pdf_path)
            result['is_priority'] = is_priority
            result['is_doc_related'] = is_doc_related
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing PDF from {url}: {e}")
            return {'source': url, 'error': str(e)}
    
    def close(self):
        """Close the session."""
        self.session.close()
        logger.info("PDF processor session closed")