"""
Handles web scraping functions to extract content from grant websites,
with enhanced focus on documentation requirements.
"""
import logging
import re
from typing import List, Dict, Any, Set, Tuple, Optional
import os
import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
from urllib.parse import urljoin, urlparse

import config
from utils import clean_text, is_valid_url, normalize_whitespace

logger = logging.getLogger(__name__)

class WebScraper:
    """Scrapes web content from grant websites with focus on documentation requirements."""
    
    def __init__(self):
        """Initialize the web scraper."""
        self.session = requests.Session()
        self.session.headers.update(config.REQUEST_HEADERS)
        
        # Documentation-related terms (expanded)
        self.doc_terms = [
            'document', 'allegat', 'modulistic', 'certificaz', 'modulo', 'moduli',
            'domanda', 'presentazione', 'istanza', 'dichiaraz', 'autocertificaz',
            'documentazione', 'necessaria', 'richiesta', 'obbligatoria', 'presentare',
            'compilare', 'carta', 'identità', 'visura', 'bilancio', 'fascicolo',
            'firma', 'digitale', 'pec', 'spid', 'bollo'
        ]
    
    @retry(
        stop=stop_after_attempt(config.MAX_RETRIES),
        wait=wait_exponential(multiplier=config.RETRY_BACKOFF)
    )
    def get_page_content(self, url: str) -> Optional[str]:
        """
        Fetches the HTML content of a webpage.
        
        Args:
            url (str): The URL to fetch.
            
        Returns:
            Optional[str]: The HTML content of the page, or None if the request failed.
        """
        if not is_valid_url(url):
            logger.warning(f"Invalid URL: {url}")
            return None
            
        try:
            response = self.session.get(
                url, 
                timeout=config.REQUEST_TIMEOUT,
                allow_redirects=True
            )
            response.raise_for_status()
            
            content_type = response.headers.get('Content-Type', '').lower()
            if 'text/html' not in content_type and 'application/xhtml+xml' not in content_type:
                logger.warning(f"URL {url} is not an HTML page: {content_type}")
                return None
                
            logger.info(f"Successfully fetched content from {url}")
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def extract_pdf_links(self, html_content: str, base_url: str) -> List[Dict[str, Any]]:
        """
        Extracts links to PDF files from HTML content with contextual information.
        Prioritizes PDFs that are likely to contain documentation requirements.
        
        Args:
            html_content (str): The HTML content to parse.
            base_url (str): The base URL for resolving relative links.
            
        Returns:
            List[Dict[str, Any]]: A list of PDF information with URL and context.
        """
        if not html_content:
            return []
            
        soup = BeautifulSoup(html_content, 'lxml')
        pdf_links = []
        
        # Find links specifically about documentation or forms
        doc_sections = []
        for term in self.doc_terms:
            sections = soup.find_all(['div', 'section', 'article'], 
                                    class_=lambda x: x and term in x.lower())
            doc_sections.extend(sections)
            
            headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'], 
                                    string=lambda s: s and term in s.lower())
            for heading in headings:
                next_elem = heading.find_next_sibling()
                if next_elem:
                    doc_sections.append(next_elem)
        
        # First find PDF links in documentation-specific areas
        for section in doc_sections:
            for a_tag in section.find_all('a', href=True):
                href = a_tag['href'].strip()
                
                is_pdf = False
                for pattern in config.PDF_LINK_PATTERNS:
                    if re.search(pattern, href, re.IGNORECASE):
                        is_pdf = True
                        break
                        
                if not is_pdf and a_tag.text:
                    if re.search(r'\.pdf|documento|allegato|modulistic', a_tag.text, re.IGNORECASE):
                        is_pdf = True
                
                if is_pdf:
                    absolute_url = urljoin(base_url, href)
                    
                    # Extract context from surrounding elements
                    parent = a_tag.parent
                    context = a_tag.get_text().strip()
                    
                    # Look for heading or label above the link
                    prev_heading = a_tag.find_previous(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'label', 'strong'])
                    if prev_heading:
                        context = prev_heading.get_text().strip() + " - " + context
                    
                    # Use filename as last resort
                    if not context:
                        context = os.path.basename(href)
                    
                    # High priority for PDFs in documentation sections
                    pdf_links.append({
                        'url': absolute_url,
                        'context': normalize_whitespace(context),
                        'text': normalize_whitespace(a_tag.get_text()),
                        'priority': True  # Always high priority in doc sections
                    })
        
        # Then find all other PDF links
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].strip()
            
            is_pdf = False
            for pattern in config.PDF_LINK_PATTERNS:
                if re.search(pattern, href, re.IGNORECASE):
                    is_pdf = True
                    break
                    
            if not is_pdf and a_tag.text:
                if re.search(r'\.pdf|documento|allegato|modulistic', a_tag.text, re.IGNORECASE):
                    is_pdf = True
            
            if is_pdf:
                absolute_url = urljoin(base_url, href)
                
                # Skip if already added from doc sections
                if any(link['url'] == absolute_url for link in pdf_links):
                    continue
                
                # Extract context from surrounding elements
                context = ""
                parent = a_tag.parent
                
                # Look for heading or label above the link
                prev_heading = a_tag.find_previous(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'label', 'strong'])
                if prev_heading:
                    context += prev_heading.get_text().strip() + " - "
                
                # Add immediate parent container text if it exists and is short enough
                if parent and parent.name in ['li', 'td', 'div', 'p']:
                    parent_text = parent.get_text().strip()
                    if 10 < len(parent_text) < 200:  # Only include reasonably sized context
                        context += parent_text
                
                # Use link text as context if no better context is found
                if not context:
                    context = a_tag.get_text().strip()
                
                # Use filename as last resort
                if not context:
                    context = os.path.basename(href)
                
                # Determine priority based on filename and context
                # Higher priority for documentation-related PDFs
                is_priority = any(term in href.lower() or term in context.lower() 
                                for term in self.doc_terms)
                if not is_priority:  # If not already prioritized by doc terms
                    is_priority = any(pattern in href.lower() or pattern in context.lower() 
                                    for pattern in config.PRIORITY_PDF_PATTERNS)
                
                pdf_links.append({
                    'url': absolute_url,
                    'context': normalize_whitespace(context),
                    'text': normalize_whitespace(a_tag.get_text()),
                    'priority': is_priority
                })
        
        logger.info(f"Found {len(pdf_links)} PDF links on {base_url}")
        return pdf_links
    
    def extract_grant_information(self, html_content: str, url: str) -> Dict[str, Any]:
        """
        Extracts comprehensive grant information from HTML content,
        with special focus on documentation requirements.
        
        Args:
            html_content (str): The HTML content to parse.
            url (str): The URL of the page.
            
        Returns:
            Dict[str, Any]: Structured grant information.
        """
        if not html_content:
            return {}
            
        soup = BeautifulSoup(html_content, 'lxml')
        
        # Extract page title
        title = None
        title_tag = soup.find('title')
        if title_tag:
            title = normalize_whitespace(title_tag.get_text())
        
        # Extract main content
        main_content = ""
        
        # First look for key tags that typically contain the main content
        main_tags = soup.find_all(['main', 'article', 'div', 'section'], class_=lambda x: x and any(term in x.lower() for term in ['content', 'main', 'body', 'article']))
        
        # If no specific content tags found, fall back to basic content extraction
        if not main_tags:
            # Get content from paragraphs, list items, and table cells
            for element in soup.find_all(['p', 'li', 'td', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                text = clean_text(element.get_text())
                if text:
                    main_content += text + " "
        else:
            # Process the most relevant content container
            for container in main_tags:
                container_text = clean_text(container.get_text())
                if len(container_text) > len(main_content):
                    main_content = container_text
        
        # Extract structured information
        structured_info = {}
        
        # Look specifically for documentation sections - this is our main focus
        for doc_term in self.doc_terms:
            # Look for headings containing documentation terms
            doc_headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'], 
                                      string=lambda s: s and doc_term in s.lower())
            
            for heading in doc_headings:
                # Get section title
                section_title = normalize_whitespace(heading.get_text())
                
                # Extract content following the heading
                section_content = ""
                content_elements = []
                
                # Continue until we hit another heading or run out of siblings
                current = heading.next_sibling
                while current and not (hasattr(current, 'name') and current.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                    if hasattr(current, 'get_text'):
                        content_elements.append(current)
                    current = current.next_sibling
                
                # Process accumulated content
                if content_elements:
                    # Check if it contains a list, which is common for documentation requirements
                    list_items = []
                    for elem in content_elements:
                        if elem.name in ['ul', 'ol']:
                            for li in elem.find_all('li'):
                                list_items.append(clean_text(li.get_text()))
                        else:
                            text = clean_text(elem.get_text())
                            if text:
                                section_content += text + " "
                    
                    if list_items:
                        structured_info[section_title] = list_items
                    elif section_content:
                        structured_info[section_title] = section_content
        
        # Important sections extraction (for context)
        for section_term in config.IMPORTANT_SECTIONS:
            # Skip if already processed as documentation section
            if any(section_term in key.lower() for key in structured_info.keys()):
                continue
                
            # Look for headings containing the section term
            section_headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'], 
                                           string=lambda s: s and section_term in s.lower())
            
            for heading in section_headings:
                # Get section title
                section_title = normalize_whitespace(heading.get_text())
                
                # Extract content following the heading
                section_content = ""
                current = heading.next_sibling
                
                # Continue until we hit another heading or run out of siblings
                while current and not (hasattr(current, 'name') and current.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                    if hasattr(current, 'get_text'):
                        text = clean_text(current.get_text())
                        if text:
                            section_content += text + " "
                    current = current.next_sibling
                
                if section_title and section_content:
                    structured_info[section_title] = section_content
        
        # Extract information based on documentation search terms
        for term in self.doc_terms:
            # Create a pattern to find larger blocks of text containing this term
            pattern = re.compile(r'(.{0,200}' + re.escape(term) + r'.{0,200})', re.IGNORECASE)
            matches = pattern.findall(main_content)
            
            if matches:
                term_key = "Documentazione - " + term.capitalize()
                if term_key not in structured_info:
                    structured_info[term_key] = []
                
                for match in matches:
                    clean_match = clean_text(match)
                    if clean_match and clean_match not in structured_info[term_key]:
                        structured_info[term_key].append(clean_match)
        
        # Extract lists, which often contain documentation requirements
        lists = {}
        for ul in soup.find_all(['ul', 'ol']):
            list_title = ""
            
            # Find preceding heading for context
            prev_heading = ul.find_previous(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            if prev_heading:
                list_title = normalize_whitespace(prev_heading.get_text())
            else:
                # Look for a preceding paragraph that might be a label
                prev_para = ul.find_previous('p')
                if prev_para and len(prev_para.get_text()) < 150:
                    list_title = normalize_whitespace(prev_para.get_text())
            
            if not list_title:
                continue
                
            # Extract list items
            list_items = []
            for li in ul.find_all('li'):
                item_text = clean_text(li.get_text())
                if item_text:
                    list_items.append(item_text)
            
            if list_items:
                lists[list_title] = list_items
        
        # Extract tables, which often contain structured information
        tables = {}
        for table_idx, table in enumerate(soup.find_all('table')):
            # Find table caption or preceding heading
            table_title = f"Tabella {table_idx+1}"
            
            caption = table.find('caption')
            if caption:
                table_title = normalize_whitespace(caption.get_text())
            else:
                prev_heading = table.find_previous(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                if prev_heading:
                    table_title = normalize_whitespace(prev_heading.get_text())
            
            # Check if table might contain documentation info
            is_doc_table = any(term in table_title.lower() for term in self.doc_terms)
            
            # Extract table data
            table_data = []
            
            # Extract header row if it exists
            headers = []
            thead = table.find('thead')
            if thead:
                header_row = thead.find('tr')
                if header_row:
                    headers = [clean_text(th.get_text()) for th in header_row.find_all(['th', 'td'])]
                    # Check headers for documentation terms
                    is_doc_table = is_doc_table or any(
                        any(term in header.lower() for term in self.doc_terms) 
                        for header in headers if header
                    )
            
            # If no thead, use the first row as header
            if not headers:
                first_row = table.find('tr')
                if first_row:
                    headers = [clean_text(th.get_text()) for th in first_row.find_all(['th', 'td'])]
                    # Check headers for documentation terms
                    is_doc_table = is_doc_table or any(
                        any(term in header.lower() for term in self.doc_terms) 
                        for header in headers if header
                    )
            
            # Process data rows
            for tr in table.find_all('tr')[1:] if headers else table.find_all('tr'):
                row_data = [clean_text(td.get_text()) for td in tr.find_all(['td', 'th'])]
                if row_data and any(cell for cell in row_data):
                    if headers and len(row_data) == len(headers):
                        row_dict = dict(zip(headers, row_data))
                        table_data.append(row_dict)
                    else:
                        table_data.append(row_data)
            
            if table_data:
                # Priority for documentation tables
                if is_doc_table:
                    table_title = "DOCUMENTAZIONE - " + table_title
                
                tables[table_title] = table_data
        
        # Combine all extracted information
        return {
            'title': title,
            'url': url,
            'main_content': main_content,
            'structured_info': structured_info,
            'lists': lists,
            'tables': tables
        }
    
    def close(self):
        """Close the session."""
        self.session.close()
        logger.info("Web scraper session closed")