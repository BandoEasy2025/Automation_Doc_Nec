import logging
import os
import re
import tempfile
import io
from typing import Dict, List, Any, Optional, Tuple
import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from urllib.parse import urlparse
import chardet

# Try to import pdfminer, but have fallback options
PDF_EXTRACTOR = 'pdfminer'
try:
    from pdfminer.high_level import extract_text
except ImportError:
    try:
        # Try PyPDF2 as fallback
        import PyPDF2
        PDF_EXTRACTOR = 'pypdf2'
        logging.warning("Using PyPDF2 as fallback for PDF extraction")
    except ImportError:
        # If neither is available, we'll handle this in the methods
        PDF_EXTRACTOR = 'none'
        logging.error("No PDF extraction library available. Install pdfminer.six or PyPDF2.")

import config
from utils import clean_text, sanitize_filename, normalize_whitespace

logger = logging.getLogger(__name__)

class PDFProcessor:
    """Downloads and processes PDF files to extract relevant information."""
    
    def __init__(self):
        """Initialize the PDF processor."""
        self.session = requests.Session()
        self.session.headers.update(config.REQUEST_HEADERS)
        
        # For SSL issues, allow the option to disable verification
        # ONLY USE THIS IF ABSOLUTELY NECESSARY - it's a security risk
        self.ssl_verify = True
        
        # Create download directory if it doesn't exist
        os.makedirs(config.PDF_DOWNLOAD_DIR, exist_ok=True)
        
        # Use documentation items from config
        self.target_documentation = config.DOCUMENTATION_ITEMS
        
        logger.info("PDF processor initialized with target document types")
    
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
            # Parse URL to get better filename
            parsed_url = urlparse(url)
            path = parsed_url.path
            
            # First try a HEAD request to check if it's a PDF
            try:
                head_response = self.session.head(url, timeout=config.REQUEST_TIMEOUT, allow_redirects=True, verify=self.ssl_verify)
                
                # Check if the URL is actually a PDF
                content_type = head_response.headers.get('Content-Type', '').lower()
                if 'application/pdf' not in content_type and not url.lower().endswith('.pdf'):
                    # Try again with SSL verification disabled if needed
                    if self.ssl_verify and ('certificate' in str(head_response) or 'SSL' in str(head_response)):
                        head_response = self.session.head(url, timeout=config.REQUEST_TIMEOUT, 
                                                       allow_redirects=True, verify=False)
                        content_type = head_response.headers.get('Content-Type', '').lower()
                    
                    # If still not a PDF, skip
                    if 'application/pdf' not in content_type and not url.lower().endswith('.pdf'):
                        logger.warning(f"URL {url} is not a PDF: {content_type}")
                        return None
                
                # Check file size
                content_length = head_response.headers.get('Content-Length')
                if content_length and int(content_length) > config.MAX_PDF_SIZE:
                    logger.warning(f"PDF at {url} is too large ({content_length} bytes)")
                    return None
            except requests.exceptions.SSLError:
                # Try again with SSL verification disabled
                logger.warning(f"SSL error during HEAD request for {url}, trying without verification")
                self.ssl_verify = False
            except Exception as e:
                # If HEAD fails, we'll still try GET
                logger.warning(f"HEAD request failed for {url}: {e}, trying GET")
            
            # Download the PDF
            response = self.session.get(url, timeout=config.REQUEST_TIMEOUT, stream=True, verify=self.ssl_verify)
            response.raise_for_status()
            
            # Check content type from actual response
            content_type = response.headers.get('Content-Type', '').lower()
            if 'application/pdf' not in content_type and not url.lower().endswith('.pdf'):
                logger.warning(f"URL {url} is not a PDF: {content_type}")
                return None
            
            # Create a safe filename from the URL
            filename = sanitize_filename(os.path.basename(path) or "downloaded_pdf")
            if not filename.lower().endswith('.pdf'):
                filename += '.pdf'
                
            # Save to file
            filepath = os.path.join(config.PDF_DOWNLOAD_DIR, filename)
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Successfully downloaded PDF from {url} to {filepath}")
            return filepath
        except requests.exceptions.SSLError as e:
            logger.error(f"SSL error downloading PDF from {url}: {e}")
            if self.ssl_verify:
                # Try again with SSL verification disabled
                logger.warning(f"Retrying {url} with SSL verification disabled")
                self.ssl_verify = False
                try:
                    response = self.session.get(url, timeout=config.REQUEST_TIMEOUT, stream=True, verify=False)
                    response.raise_for_status()
                    
                    # Save to file
                    filename = sanitize_filename(os.path.basename(url))
                    if not filename.lower().endswith('.pdf'):
                        filename += '.pdf'
                    
                    filepath = os.path.join(config.PDF_DOWNLOAD_DIR, filename)
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    logger.info(f"Successfully downloaded PDF (without SSL verification) from {url} to {filepath}")
                    return filepath
                except Exception as e:
                    logger.error(f"Still failed to download PDF from {url} even with SSL verification disabled: {e}")
                    return None
                finally:
                    # Reset SSL verification for future requests
                    self.ssl_verify = True
            return None
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
            
            if PDF_EXTRACTOR == 'pdfminer':
                # Try with pdfminer
                text = extract_text(pdf_path)
            elif PDF_EXTRACTOR == 'pypdf2':
                # Use PyPDF2 as fallback
                text = ""
                with open(pdf_path, 'rb') as file:
                    reader = PyPDF2.PdfFileReader(file)
                    for page_num in range(reader.numPages):
                        text += reader.getPage(page_num).extractText()
            else:
                # No PDF library available
                logger.error("No PDF extraction library available. Install pdfminer.six or PyPDF2.")
                return "No PDF extraction library available. This PDF could not be processed."
            
            # Check if we got any text
            if not text:
                logger.warning(f"No text content extracted from {pdf_path}")
                # Try a basic check to see if the file is a PDF
                with open(pdf_path, 'rb') as f:
                    header = f.read(5)
                    if header != b'%PDF-':
                        logger.error(f"File {pdf_path} is not a valid PDF (wrong header)")
                        return None
                return "PDF appears to be valid but no text could be extracted. It may be a scanned document or contain only images."
                
            # Clean and normalize the extracted text
            text = normalize_whitespace(text)
            logger.info(f"Successfully extracted {len(text)} characters from {pdf_path}")
            return text
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {e}")
            return f"Error extracting text: {str(e)}"
    
    def process_pdf_content(self, pdf_text: str, context: str = "") -> Dict[str, Any]:
        """
        Processes PDF text to extract structured information.
        Enhanced to better identify documentation requirements based on target keywords.
        
        Args:
            pdf_text (str): The text content of the PDF.
            context (str): Context about the PDF from the link.
            
        Returns:
            Dict[str, Any]: Structured information extracted from the PDF.
        """
        if not pdf_text:
            return {'error': 'No PDF text content available'}
        
        try:
            result = {
                'context': context,
                'main_content': pdf_text[:10000],  # Include more content for better analysis
                'sections': {},
                'lists': [],
                'tables': [],
                'Documentazione': []  # Special key for documentation items
            }
            
            # Extract documentation-specific content first - focus on target keywords
            self._extract_documentation_content(pdf_text, result)
            
            # Look for specific documentation items from our target list
            self._extract_target_documentation_items(pdf_text, result)
            
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
                    
                    # Check if this section is related to any target documentation item
                    section_lower = section_title.lower() + " " + section_content.lower()
                    
                    for doc_item in self.target_documentation:
                        if doc_item["name"].lower() in section_lower or any(kw.lower() in section_lower for kw in doc_item["keywords"]):
                            result['Documentazione'].append(f"{section_title}: {clean_text(section_content)}")
                            break
            
            # Extract lists (bullet points, numbered lists)
            list_patterns = [
                r'(?:\n|\r\n)(?:\s*[\•\-\*]\s*)([^\n]+)(?:\n|\r\n)(?:\s*[\•\-\*]\s*)([^\n]+)',  # Bullet lists
                r'(?:\n|\r\n)(?:\s*\d+[\.\)]\s*)([^\n]+)(?:\n|\r\n)(?:\s*\d+[\.\)]\s*)([^\n]+)',  # Numbered lists
                r'(?:\n|\r\n)(?:\s*[a-z][\.\)]\s*)([^\n]+)(?:\n|\r\n)(?:\s*[a-z][\.\)]\s*)([^\n]+)'  # Alphabetical lists
            ]
            
            for pattern in list_patterns:
                list_matches = re.findall(pattern, pdf_text)
                if list_matches:
                    items = [clean_text(item) for group in list_matches for item in group if clean_text(item)]
                    if items:
                        result['lists'].append(items)
                        
                        # Check if list items are related to documentation
                        doc_related_items = []
                        for item in items:
                            item_lower = item.lower()
                            # Check against all target documentation items
                            for doc_item in self.target_documentation:
                                if doc_item["name"].lower() in item_lower or any(kw.lower() in item_lower for kw in doc_item["keywords"]):
                                    doc_related_items.append(item)
                                    break
                        
                        if doc_related_items:
                            result['Documentazione'].extend(doc_related_items)
            
            # Remove duplicates in Documentazione
            if result['Documentazione']:
                result['Documentazione'] = list(dict.fromkeys(result['Documentazione']))
                
            return result
        except Exception as e:
            logger.error(f"Error processing PDF content: {e}")
            return {
                'context': context,
                'error': f"Error processing PDF content: {str(e)}",
                'main_content': pdf_text[:1000]  # Include some content to have something
            }
    
    def _extract_documentation_content(self, pdf_text: str, result: Dict[str, Any]) -> None:
        """
        Specifically extracts documentation requirements from PDF text.
        Enhanced to focus on target documentation keywords.
        
        Args:
            pdf_text (str): The PDF text content to analyze.
            result (Dict[str, Any]): The result dictionary to update.
        """
        try:
            # Tokenize text into sentences for better analysis
            sentences = re.split(r'[.;!?]\s+', pdf_text)
            
            # Look for sentences containing target documentation keywords
            for sentence in sentences:
                sentence_lower = sentence.lower()
                
                # Check against all target documentation items
                for doc_item in self.target_documentation:
                    if doc_item["name"].lower() in sentence_lower or any(kw.lower() in sentence_lower for kw in doc_item["keywords"]):
                        clean_sentence = clean_text(sentence)
                        if clean_sentence and len(clean_sentence) > 15 and clean_sentence not in result["Documentazione"]:
                            result["Documentazione"].append(clean_sentence)
                            break
            
            # Look for sections with documentation-related headers
            doc_section_headers = [
                'documenti', 'documentazione', 'allegati', 'modulistica', 'certificazioni',
                'documenti necessari', 'documenti richiesti', 'documentazione necessaria',
                'documentazione richiesta', 'allegati necessari', 'allegati richiesti'
            ]
            
            for header in doc_section_headers:
                # Find instances of the header
                header_positions = [m.start() for m in re.finditer(r'\b' + re.escape(header) + r'\b', pdf_text.lower())]
                
                for pos in header_positions:
                    # Get the surrounding text (up to 1000 characters after the header)
                    context_text = pdf_text[pos:pos+1000]
                    
                    # Look for list items in the context text
                    list_items = self._extract_list_items(context_text)
                    
                    if list_items:
                        for item in list_items:
                            if item and item not in result["Documentazione"]:
                                result["Documentazione"].append(item)
        except Exception as e:
            logger.error(f"Error extracting documentation content: {e}")
            result["Documentazione"].append(f"Errore nell'elaborazione della documentazione: {str(e)}")
    
    def _extract_target_documentation_items(self, pdf_text: str, result: Dict[str, Any]) -> None:
        """
        Looks for specific target documentation items in the PDF text.
        
        Args:
            pdf_text (str): The PDF text to analyze.
            result (Dict[str, Any]): The result dictionary to update.
        """
        try:
            pdf_text_lower = pdf_text.lower()
            sentences = re.split(r'[.;!?]\s+', pdf_text)
            
            # Check for each target documentation item
            for doc_item in self.target_documentation:
                item_found = False
                for keyword in doc_item['keywords']:
                    if keyword.lower() in pdf_text_lower:
                        item_found = True
                        # Find sentences containing this keyword
                        for sentence in sentences:
                            sentence_lower = sentence.lower()
                            if keyword.lower() in sentence_lower:
                                clean_sentence = clean_text(sentence)
                                if clean_sentence and len(clean_sentence) > 15 and clean_sentence not in result["Documentazione"]:
                                    result["Documentazione"].append(f"{doc_item['name']}: {clean_sentence}")
                
                # If item name itself appears in the text
                if not item_found and doc_item['name'].lower() in pdf_text_lower:
                    # Find sentences containing this item name
                    for sentence in sentences:
                        sentence_lower = sentence.lower()
                        if doc_item['name'].lower() in sentence_lower:
                            clean_sentence = clean_text(sentence)
                            if clean_sentence and len(clean_sentence) > 15 and clean_sentence not in result["Documentazione"]:
                                result["Documentazione"].append(clean_sentence)
        except Exception as e:
            logger.error(f"Error extracting target documentation items: {e}")
            result["Documentazione"].append(f"Errore nell'identificazione degli elementi di documentazione: {str(e)}")
    
    def _extract_list_items(self, text: str) -> List[str]:
        """
        Extracts items that appear to be in a list format from text.
        Enhanced with additional patterns to catch more list formats.
        
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
        
        # Look for lettered list items
        letter_pattern = re.compile(r'(?:^|\n|\s)([a-z][\.|\)])\s+([^\n]+)', re.MULTILINE)
        letter_matches = letter_pattern.findall(text)
        if letter_matches:
            list_items.extend([clean_text(item[1]) for item in letter_matches if clean_text(item[1])])
        
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
                return {
                    'source': url, 
                    'context': context,
                    'error': 'Failed to download PDF',
                    'is_priority': is_priority,
                    'is_doc_related': is_doc_related,
                    'filename': os.path.basename(url),
                    'Documentazione': [f"Non è stato possibile scaricare il PDF dall'URL {url}."]
                }
                
            # Extract text from the PDF
            pdf_text = self.extract_text_from_pdf(pdf_path)
            if not pdf_text:
                return {
                    'source': url, 
                    'context': context,
                    'error': 'Failed to extract text from PDF',
                    'is_priority': is_priority,
                    'is_doc_related': is_doc_related,
                    'filename': os.path.basename(pdf_path),
                    'Documentazione': [f"Non è stato possibile estrarre il testo dal PDF scaricato: {os.path.basename(pdf_path)}."]
                }
            
            # Process the PDF content
            result = self.process_pdf_content(pdf_text, context)
            
            # Add metadata
            result['source'] = url
            result['filename'] = os.path.basename(pdf_path)
            result['is_priority'] = is_priority
            result['is_doc_related'] = is_doc_related
            
            # If this PDF was marked as documentation-related, add a note to ensure it's captured
            if is_doc_related and context and not result.get('error'):
                if 'Documentazione' not in result:
                    result['Documentazione'] = []
                result['Documentazione'].append(f"PDF rilevante per la documentazione: {context}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing PDF from {url}: {e}")
            return {
                'source': url, 
                'context': context,
                'error': str(e),
                'is_priority': is_priority,
                'is_doc_related': is_doc_related,
                'filename': os.path.basename(url) if '/' in url else 'unknown.pdf',
                'Documentazione': [f"Errore nell'elaborazione del PDF: {str(e)}"]
            }
    
    def close(self):
        """Close the session."""
        self.session.close()
        logger.info("PDF processor session closed")