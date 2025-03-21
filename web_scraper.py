
"""
Enhanced web scraping functions to extract content from grant websites.
Improved to better handle cases where PDFs can't be accessed and to extract more documentation requirements.
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
    """Scrapes web content from grant websites with enhanced documentation extraction."""
    
    def __init__(self):
        """Initialize the web scraper with enhanced patterns for documentation."""
        self.session = requests.Session()
        self.session.headers.update(config.REQUEST_HEADERS)
        
        # For SSL issues, allow the option to disable verification
        self.ssl_verify = True
        
        # Try to determine best available parser
        self.parser = self._get_best_parser()
        
        # Enhanced patterns to identify documentation sections - expanded for better coverage
        self.doc_section_patterns = [
            r'document[azio\-\s]+necessari[ao]',
            r'allegat[io]',
            r'modulistic[ao]',
            r'come[\s]+(?:presentare|compilare)',
            r'presentazione[\s]+(?:della[\s]+)?domanda',
            r'documenti[\s]+(?:da[\s]+)?(?:presentare|allegare)',
            r'requisiti[\s]+(?:di[\s]+)?partecipazione',
            r'certificazion[ei]',
            r'procedura[\s]+(?:di[\s]+)?(?:presentazione|domanda)',
            r'(?:carta|documenti)[\s]+(?:d\'identità|identità)',
            r'(?:curriculum|cv)[\s]+(?:vitae|professionale)',
            r'scheda[\s]+(?:progett|tecnica)',
            r'piano[\s]+(?:finanziario|economic|spese)',
            r'business[\s]+plan',
            r'visura[\s]+camerale',
            r'dichiaraz[\s]+(?:redditi|iva)',
            r'quietanz[ae]',
            r'domanda[\s]+di[\s]+(?:contributo|partecipazione|ammissione|finanziamento)',
            r'documentazione[\s]+(?:da[\s]+)?allegare',
            r'documenti[\s]+(?:a[\s]+)?corredo',
            r'elenco[\s]+documenti',
            r'documentazione[\s]+(?:tecnica|amministrativa|contabile)',
            r'allegati[\s]+al[\s]+bando',
            r'modulistica[\s]+(?:da[\s]+)?(?:compilare|presentare)',
            r'materiale[\s]+promozionale',
            r'dichiarazione[\s]+(?:sostitutiva|DNSH|d\'intenti|antimafia)',
            r'relazione[\s]+(?:finale|lavori|progetto)',
            r'DURC',
            r'fideiussione',
            r'compagine[\s]+sociale'
        ]
        
        # Additional terms to look for in links and content - expanded to match request
        self.doc_keywords = [
            # General documentation terms
            'document', 'allegat', 'modulistic', 'certificaz', 
            'richiest', 'presentare', 'obbligo', 'necessari',
            'domanda', 'application', 'richiesta', 'presentazione',
            
            # Project documentation
            'scheda progett', 'business plan', 'progetto imprenditor', 
            'pitch', 'gantt', 'relazione', 'report', 'piano',
            
            # Financial documentation
            'piano finanziar', 'budget', 'entrate e spese', 
            'costi', 'investiment', 'economic', 'finanziar',
            'dichiarazion redditi', 'dichiarazion iva', 'situazione economic',
            'conto economic', 'previsional', 'spese',
            
            # Identification and legal documents
            'firma', 'signature', 'digitale', 'copia', 'identity',
            'identità', 'dichiarazione', 'declaration', 'formulario',
            'modulo', 'form', 'attestazione', 'certification',
            'dichiarazione sostitutiva', 'atto notorietà', 'DSAN',
            
            # Company/personnel documents
            'visura', 'camerale', 'bilancio', 'curriculum', 
            'cv', 'team', 'compagine social', 'soci',
            'carta d\'identità', 'codice fiscale', 'partita iva',
            
            # Payment/expense documentation
            'fattur', 'quietanz', 'pagament', 'giustificativ',
            'ricevut', 'contribut', 'bonifico',
            
            # Compliance and certification
            'DNSH', 'DURC', 'regolarità contributiva', 'antimafia',
            'antiriciclaggio', 'casellario', 'giudizia', 
            'certificato conformità', 'certificazione qualità',
            'soa', 'attestato',
            
            # Property and location
            'localizzazione', 'ubicazione', 'assenso propriet', 
            'locazion', 'comodato', 'affitto', 'visura catastale',
            
            # Other specific documents
            'inizio attività', 'fine corso', 'frequenza',
            'self-assessment', 'sustainability', 'sostenibilit',
            'conferimento', 'delega', 'legale rappresentante',
            'brevetto', 'licenza', 'fideiussion', 'ANAC',
            'intestazione fiduciaria', 'regolarità fiscal',
            'registro imprese', 'sicurezza', 'attribuzione'
        ]
        
        # Create a mapping of document types to their variations for identification
        self.document_type_mapping = {
            "scheda progettuale": ["scheda progett", "scheda del progett", "progett", "piano di sviluppo"],
            "piano finanziario": ["piano finanziar", "budget", "entrate e spese", "piano delle spese", "previsione di spesa"],
            "programma di investimento": ["programma di invest", "piano di invest", "investiment"],
            "dichiarazione DNSH": ["DNSH", "Do No Significant Harm", "dichiarazione DNSH", "rispetto del DNSH"],
            "dichiarazioni dei redditi": ["dichiarazion", "redditi", "dichiarazione dei redditi", "modello unico", "modello 730"],
            "dichiarazioni IVA": ["IVA", "dichiarazione IVA", "dichiarazioni IVA", "imposta valore aggiunto"],
            "situazione economica": ["situazione economic", "situazione patrimonial", "stato patrimonial", "bilancio"],
            "conto economico previsionale": ["conto economic", "economic prevision", "prevision", "bilancio prevision"],
            "documenti giustificativi": ["giustificativ", "spesa", "document di spesa", "fattur", "quietanz"],
            "relazione lavori": ["relazione", "lavori eseguit", "relazione di esecuzione", "relazione tecnica"],
            "materiale promozionale": ["material promozional", "promozion", "marketing", "pubblicit"],
            "compagine sociale": ["compagine social", "assetto societari", "soc", "struttura societaria"],
            "agevolazioni pubbliche": ["agevolazion", "contribut", "finanziam", "aiuti di stato", "de minimis"],
            "dichiarazione inizio attività": ["inizio attività", "DIA", "SCIA", "dichiarazione di inizio", "avvio attivit"],
            "progetto imprenditoriale": ["progetto imprenditori", "business idea", "idea imprenditori", "proposta imprenditori"],
            "pitch": ["pitch", "presentazione", "elevator pitch", "pitch deck"],
            "curriculum": ["curriculum", "CV", "curriculum vitae", "esperienza", "competenze"],
            "curriculum team": ["curriculum team", "CV team", "team imprenditori", "soci", "fondatori"],
            "localizzazione": ["localizzazione", "ubicazione", "sede", "luogo", "dichiarazione localizzazione"],
            "assenso proprietario": ["assenso", "propriet", "autorizzazione propriet", "consenso propriet"],
            "contratto locazione": ["locazion", "affitto", "contratto di locazione", "contratto d'affitto"],
            "contratto comodato": ["comodato", "comodato d'uso", "contratto di comodato"],
            "certificazione qualità": ["certificazione qualit", "ISO", "certificato di qualit", "sistema qualit"],
            "fatture elettroniche": ["fattur", "fattura elettronic", "fatturazione elettronic", "e-fattura"],
            "quietanze": ["quietanz", "ricevut", "pagament", "bonifico", "pagamento effettuato"],
            "Business plan": ["business plan", "piano di business", "piano aziendale", "piano d'impresa"],
            "dichiarazione sostitutiva": ["dichiarazione sostitutiva", "autocertificazione", "DPR 445", "445/2000"],
            "pagamenti effettuati": ["pagament", "bonifico", "estratto conto", "ricevuta di pagamento"],
            "dichiarazione fine corso": ["fine corso", "completamento corso", "attestazione finale", "conclusione corso"],
            "attestato frequenza": ["attestato", "frequenza", "partecipazione", "certificato di frequenza"],
            "self-assessment": ["self-assessment", "sustainability", "sostenibilit", "valutazione sostenibilit"],
            "relazione finale": ["relazione final", "report final", "conclusione progett", "progetto concluso"],
            "atto conferimento": ["conferimento", "atto di conferimento", "conferimento incarico", "mandato"],
            "investitore esterno": ["investitor", "finanziator", "business angel", "venture capital", "investimento esterno"],
            "delega rappresentante": ["delega", "legale rappresentante", "rappresentanza", "procura"],
            "budget costi": ["budget", "costi", "preventivo", "piano dei costi", "previsione costi"],
            "codice fiscale": ["codice fiscale", "certificato attribuzione", "attribuzione codice", "agenzia entrate"],
            "analisi entrate": ["analisi entrate", "entrate", "ricavi", "introiti", "analisi ricavi"],
            "DURC": ["DURC", "regolarità contributiva", "documento unico", "contributi"],
            "dichiarazione antiriciclaggio": ["antiriciclaggio", "riciclaggio", "AML", "D.lgs 231"],
            "dichiarazioni antimafia": ["antimafia", "certificazione antimafia", "informativa antimafia", "D.lgs 159"],
            "fideiussione": ["fideiussion", "garanzia", "polizza fideiussoria", "garanzia bancaria"],
            "casellario giudiziale": ["casellario", "giudiziale", "certificato penale", "carichi pendenti"],
            "fideiussione provvisoria": ["fideiussione provvisoria", "garanzia provvisoria", "cauzione provvisoria"],
            "contributo ANAC": ["ANAC", "autorità anticorruzione", "contributo gara"],
            "dichiarazione intenti": ["intenti", "dichiarazione d'intenti", "lettera d'intenti", "manifestazione interesse"],
            "intestazione fiduciaria": ["intestazione fiduciaria", "fiduciari", "trustee", "fiduciante"],
            "regolarità fiscale": ["regolarità fiscal", "agenzia entrate", "debiti fiscali", "imposte"],
            "iscrizione registro imprese": ["registro imprese", "iscrizione camera", "CCIAA", "camera di commercio"],
            "piano sicurezza": ["sicurezza", "piano di sicurezza", "PSC", "coordinamento sicurezza"],
            "certificato conformità": ["conformità", "certificato conformità", "dichiarazione conformità", "attestazione conformità"],
            "attestazione professionista": ["attestazione professionist", "perizia", "relazione professionist", "relazione tecnica"],
            "GANTT progetto": ["gantt", "cronoprogramma", "tempistiche", "pianificazione temporale"],
            "atto nomina": ["nomina", "atto di nomina", "designazione", "incarico"],
            "visura catastale": ["visura catast", "catasto", "dati catastali", "estratto catastale"],
            "DSAN": ["DSAN", "dichiarazione sostitutiva atto notorietà", "atto notorio", "dichiarazione sostitutiva"],
            "partita IVA": ["partita IVA", "P.IVA", "attribuzione IVA", "certificato IVA"],
            "brevetto": ["brevett", "patent", "proprietà intellettuale", "invenzione"],
            "licenza brevettuale": ["licenza brevett", "licenza patent", "uso brevetto", "sfruttamento brevetto"],
            "certificazione libretto": ["libretto", "libretto di certificazione", "libretto formativo", "attestato libretto"],
            "visura camerale": ["visura", "visura camerale", "camera di commercio", "registro imprese"],
            "carta identità": ["carta d'identità", "documento identità", "carta identità", "ID"],
            "certificato SOA": ["SOA", "attestazione SOA", "qualificazione", "certificato SOA"]
        }
    
    def _get_best_parser(self) -> str:
        """
        Determine the best available HTML parser.
        
        Returns:
            str: Name of the best available parser
        """
        # Try available parsers in order of preference
        parsers = ['lxml', 'html.parser', 'html5lib']
        for parser in parsers:
            try:
                BeautifulSoup("<html></html>", parser)
                return parser
            except:
                continue
        
        # If we get here, fall back to the built-in parser
        logger.warning("No optimal HTML parsers found, using built-in parser")
        return 'html.parser'
    
    @retry(
        stop=stop_after_attempt(config.MAX_RETRIES),
        wait=wait_exponential(multiplier=config.RETRY_BACKOFF)
    )
    def get_page_content(self, url: str) -> Optional[str]:
        """
        Fetches the HTML content of a webpage with enhanced error handling.
        
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
                allow_redirects=True,
                verify=self.ssl_verify
            )
            response.raise_for_status()
            
            content_type = response.headers.get('Content-Type', '').lower()
            if 'text/html' not in content_type and 'application/xhtml+xml' not in content_type:
                logger.warning(f"URL {url} is not an HTML page: {content_type}")
                return None
                
            logger.info(f"Successfully fetched content from {url}")
            return response.text
        except requests.exceptions.SSLError as e:
            logger.error(f"SSL error fetching {url}: {e}")
            
            # If SSL verification is already disabled, don't try again
            if not self.ssl_verify:
                return None
                
            # Try again with SSL verification disabled as a last resort
            logger.warning(f"Retrying {url} with SSL verification disabled")
            try:
                self.ssl_verify = False
                response = self.session.get(
                    url, 
                    timeout=config.REQUEST_TIMEOUT,
                    allow_redirects=True,
                    verify=False
                )
                response.raise_for_status()
                return response.text
            except requests.exceptions.RequestException as e:
                logger.error(f"Still failed after disabling SSL verification for {url}: {e}")
                return None
            finally:
                # Reset SSL verification for future requests
                self.ssl_verify = True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def extract_grant_information(self, html_content: str, url: str) -> Dict[str, Any]:
        """
        Extracts comprehensive grant information from HTML content.
        Enhanced to better identify documentation requirements.
        
        Args:
            html_content (str): The HTML content to parse.
            url (str): The URL of the page.
            
        Returns:
            Dict[str, Any]: Structured grant information.
        """
        if not html_content:
            return {}
            
        try:
            soup = BeautifulSoup(html_content, self.parser)
            
            # Extract page title
            title = None
            title_tag = soup.find('title')
            if title_tag:
                title = normalize_whitespace(title_tag.get_text())
            
            # Try to find a more specific grant name in headings
            if not title or 'home' in title.lower() or len(title) < 10:
                for heading in soup.find_all(['h1', 'h2'], limit=3):
                    heading_text = normalize_whitespace(heading.get_text())
                    if heading_text and 10 < len(heading_text) < 200 and ('bando' in heading_text.lower() or 'grant' in heading_text.lower()):
                        title = heading_text
                        break
            
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
            
            # Look for documentation-specific sections
            self._extract_documentation_sections(soup, structured_info)
            
            # Extract specific document types from the entire page
            self._extract_specific_document_types(soup, structured_info)
            
            # Important sections extraction - with enhanced patterns for documentation
            for section_term in config.IMPORTANT_SECTIONS + self.doc_keywords:
                # Look for headings containing the section term
                section_headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'], string=lambda s: s and section_term.lower() in s.lower())
                
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
            
            # Extract information based on search terms - more aggressive for documentation
            for term in config.SEARCH_TERMS + self.doc_keywords:
                # Create a pattern to find larger blocks of text containing this term
                pattern = re.compile(r'(.{0,200}' + re.escape(term) + r'.{0,200})', re.IGNORECASE)
                matches = pattern.findall(main_content)
                
                if matches:
                    term_key = term.capitalize()
                    if term_key not in structured_info:
                        structured_info[term_key] = []
                    
                    for match in matches:
                        clean_match = clean_text(match)
                        if clean_match and clean_match not in structured_info[term_key]:
                            structured_info[term_key].append(clean_match)
            
            # Extract lists, which often contain important information
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
                    # Give a generic title if none found
                    list_title = "Elenco Informazioni"
                    
                # Extract list items
                list_items = []
                for li in ul.find_all('li'):
                    item_text = clean_text(li.get_text())
                    if item_text:
                        list_items.append(item_text)
                
                if list_items:
                    lists[list_title] = list_items
                    
                    # Check if this list contains documentation items
                    list_text = ' '.join(item_text.lower() for item_text in list_items)
                    for doc_type, keywords in self.document_type_mapping.items():
                        if any(keyword in list_text for keyword in keywords):
                            # Store specific document requirements found in lists
                            if "Documentazione_Specifica" not in structured_info:
                                structured_info["Documentazione_Specifica"] = {}
                            
                            if doc_type not in structured_info["Documentazione_Specifica"]:
                                structured_info["Documentazione_Specifica"][doc_type] = []
                            
                            # Find the specific items that matched
                            for item in list_items:
                                item_lower = item.lower()
                                if any(keyword in item_lower for keyword in keywords):
                                    if item not in structured_info["Documentazione_Specifica"][doc_type]:
                                        structured_info["Documentazione_Specifica"][doc_type].append(item)
            
            # Look for documentation section in lists
            for title, items in lists.items():
                title_lower = title.lower()
                # Check against all documentation patterns
                if any(re.search(pattern, title_lower) for pattern in self.doc_section_patterns):
                    structured_info["Documentazione_Necessaria"] = items
                    
                # Also check for specific documentation items in the list title
                for keyword in self.doc_keywords:
                    if keyword in title_lower:
                        if "Documentazione_Items" not in structured_info:
                            structured_info["Documentazione_Items"] = []
                        structured_info["Documentazione_Items"].extend([
                            f"{title}: {item}" for item in items
                        ])
                        break
            
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
                
                # Extract table data
                table_data = []
                
                # Extract header row if it exists
                headers = []
                thead = table.find('thead')
                if thead:
                    header_row = thead.find('tr')
                    if header_row:
                        headers = [clean_text(th.get_text()) for th in header_row.find_all(['th', 'td'])]
                
                # If no thead, use the first row as header
                if not headers:
                    first_row = table.find('tr')
                    if first_row:
                        headers = [clean_text(th.get_text()) for th in first_row.find_all(['th', 'td'])]
                
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
                    tables[table_title] = table_data
                    
                    # Check if table contains documentation information
                    table_title_lower = table_title.lower()
                    
                    is_doc_table = False
                    # Check against all documentation patterns
                    if any(re.search(pattern, table_title_lower) for pattern in self.doc_section_patterns):
                        is_doc_table = True
                    
                    # Also check column headers for documentation keywords
                    if headers and any(any(keyword in header.lower() for keyword in self.doc_keywords) for header in headers):
                        is_doc_table = True
                    
                    if is_doc_table:
                        # Convert table to useful text format
                        doc_items = []
                        for row in table_data:
                            if isinstance(row, dict):
                                doc_items.append(" - ".join(str(v) for v in row.values() if v))
                            else:
                                doc_items.append(" - ".join(str(cell) for cell in row if cell))
                        
                        if "Documentazione_Tabella" not in structured_info:
                            structured_info["Documentazione_Tabella"] = []
                        structured_info["Documentazione_Tabella"].extend(doc_items)
                        
                        # Check for specific document types in the table
                        table_text = ' '.join(doc_items).lower()
                        for doc_type, keywords in self.document_type_mapping.items():
                            if any(keyword in table_text for keyword in keywords):
                                # Add to specific document requirements
                                if "Documentazione_Specifica" not in structured_info:
                                    structured_info["Documentazione_Specifica"] = {}
                                
                                if doc_type not in structured_info["Documentazione_Specifica"]:
                                    structured_info["Documentazione_Specifica"][doc_type] = []
                                
                                structured_info["Documentazione_Specifica"][doc_type].append(
                                    f"Trovato nella tabella '{table_title}'"
                                )
            
            # Check for surface-level information about the grant (deadlines, eligibility)
            grant_info = self._extract_surface_information(soup)
            if grant_info:
                for key, value in grant_info.items():
                    structured_info[key] = value
            
            # Fallback if no documentation was found in dedicated sections
            if not any(key.startswith("Documentazione") for key in structured_info):
                self._extract_documentation_fallback(soup, main_content, structured_info)
            
            # Combine all extracted information
            return {
                'title': title,
                'url': url,
                'main_content': main_content,
                'structured_info': structured_info,
                'lists': lists,
                'tables': tables
            }
        except Exception as e:
            logger.error(f"Error extracting information from {url}: {e}")
            # Return minimal data rather than crashing
            return {
                'title': "Error processing page",
                'url': url,
                'main_content': "",
                'error': str(e)
            }
    
    def _extract_specific_document_types(self, soup: BeautifulSoup, structured_info: Dict[str, Any]) -> None:
        """
        Extracts information about specific document types requested.
        
        Args:
            soup (BeautifulSoup): The parsed HTML content.
            structured_info (Dict[str, Any]): The dictionary to update with findings.
        """
        # Ensure we have a place to store document-specific information
        if "Documentazione_Specifica" not in structured_info:
            structured_info["Documentazione_Specifica"] = {}
        
        # Go through all text content of the page
        full_text = soup.get_text().lower()
        
        # Check for each specific document type
        for doc_type, keywords in self.document_type_mapping.items():
            if any(keyword in full_text for keyword in keywords):
                # Found a potential match, now extract surrounding context
                for keyword in keywords:
                    if keyword in full_text:
                        # Look for elements containing this keyword
                        elements = soup.find_all(string=lambda text: text and keyword.lower() in text.lower())
                        
                        for element in elements:
                            if hasattr(element, 'parent'):
                                # Get parent element for better context
                                parent = element.parent
                                if parent.name in ['p', 'li', 'td', 'div', 'span']:
                                    # Extract text from this element
                                    context = clean_text(parent.get_text())
                                    
                                    # Only add if it has substantial content
                                    if context and len(context) > 20:
                                        if doc_type not in structured_info["Documentazione_Specifica"]:
                                            structured_info["Documentazione_Specifica"][doc_type] = []
                                        
                                        if context not in structured_info["Documentazione_Specifica"][doc_type]:
                                            structured_info["Documentazione_Specifica"][doc_type].append(context)
    
    def _extract_documentation_sections(self, soup: BeautifulSoup, structured_info: Dict[str, Any]) -> None:
        """
        Specifically targets sections likely to contain documentation requirements.
        Enhanced to capture more documentation mentions.
        
        Args:
            soup (BeautifulSoup): The parsed HTML content.
            structured_info (Dict[str, Any]): The dictionary to update with findings.
        """
        try:
            # Look for headers/sections containing documentation-related terms
            for pattern in self.doc_section_patterns:
                # Find headings matching the pattern
                doc_headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'], 
                                           string=lambda s: s and re.search(pattern, s.lower()))
                
                for heading in doc_headings:
                    # Get section title
                    section_title = normalize_whitespace(heading.get_text())
                    
                    # Determine what follows the heading
                    next_element = heading.find_next_sibling()
                    
                    if next_element and next_element.name in ['ul', 'ol']:
                        # If it's a list, extract list items
                        list_items = []
                        for li in next_element.find_all('li'):
                            item_text = clean_text(li.get_text())
                            if item_text:
                                list_items.append(item_text)
                        
                        if list_items:
                            if "Documentazione_Necessaria" not in structured_info:
                                structured_info["Documentazione_Necessaria"] = []
                            structured_info["Documentazione_Necessaria"].extend(list_items)
                            
                            # Also store the section title with items for context
                            if "Documentazione_Sezioni" not in structured_info:
                                structured_info["Documentazione_Sezioni"] = []
                            structured_info["Documentazione_Sezioni"].append(f"{section_title}: {', '.join(list_items)}")
                            
                            # Try to identify specific document types in these list items
                            for item in list_items:
                                item_lower = item.lower()
                                for doc_type, keywords in self.document_type_mapping.items():
                                    if any(keyword in item_lower for keyword in keywords):
                                        if "Documentazione_Specifica" not in structured_info:
                                            structured_info["Documentazione_Specifica"] = {}
                                        
                                        if doc_type not in structured_info["Documentazione_Specifica"]:
                                            structured_info["Documentazione_Specifica"][doc_type] = []
                                        
                                        if item not in structured_info["Documentazione_Specifica"][doc_type]:
                                            structured_info["Documentazione_Specifica"][doc_type].append(item)
                    else:
                        # Otherwise, extract content until the next heading
                        section_content = ""
                        current = heading.next_sibling
                        
                        # Continue until we hit another heading or run out of siblings
                        while current and not (hasattr(current, 'name') and current.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                            if hasattr(current, 'get_text'):
                                text = clean_text(current.get_text())
                                if text:
                                    section_content += text + " "
                            current = current.next_sibling
                        
                        if section_content:
                            if "Documentazione_Sezioni" not in structured_info:
                                structured_info["Documentazione_Sezioni"] = []
                            structured_info["Documentazione_Sezioni"].append(f"{section_title}: {section_content}")
                            
                            # Check if the section contains list-like content
                            bullet_items = re.findall(r'(?:^|\s)[\•\-\*]\s+([^\n\•\-\*]+)', section_content)
                            numbered_items = re.findall(r'(?:^|\s)(\d+[\.|\)])\s+([^\n]+)', section_content)
                            
                            if bullet_items or numbered_items:
                                if "Documentazione_Necessaria" not in structured_info:
                                    structured_info["Documentazione_Necessaria"] = []
                                
                                for item in bullet_items:
                                    clean_item = clean_text(item)
                                    if clean_item:
                                        structured_info["Documentazione_Necessaria"].append(clean_item)
                                        
                                        # Check for specific document types
                                        item_lower = clean_item.lower()
                                        for doc_type, keywords in self.document_type_mapping.items():
                                            if any(keyword in item_lower for keyword in keywords):
                                                if "Documentazione_Specifica" not in structured_info:
                                                    structured_info["Documentazione_Specifica"] = {}
                                                
                                                if doc_type not in structured_info["Documentazione_Specifica"]:
                                                    structured_info["Documentazione_Specifica"][doc_type] = []
                                                
                                                if clean_item not in structured_info["Documentazione_Specifica"][doc_type]:
                                                    structured_info["Documentazione_Specifica"][doc_type].append(clean_item)
                                
                                for num, item in numbered_items:
                                    clean_item = clean_text(item)
                                    if clean_item:
                                        full_item = f"{num} {clean_item}"
                                        structured_info["Documentazione_Necessaria"].append(full_item)
                                        
                                        # Check for specific document types
                                        item_lower = clean_item.lower()
                                        for doc_type, keywords in self.document_type_mapping.items():
                                            if any(keyword in item_lower for keyword in keywords):
                                                if "Documentazione_Specifica" not in structured_info:
                                                    structured_info["Documentazione_Specifica"] = {}
                                                
                                                if doc_type not in structured_info["Documentazione_Specifica"]:
                                                    structured_info["Documentazione_Specifica"][doc_type] = []
                                                
                                                if full_item not in structured_info["Documentazione_Specifica"][doc_type]:
                                                    structured_info["Documentazione_Specifica"][doc_type].append(full_item)
                            else:
                                # Check for specific document types in this section content
                                section_lower = section_content.lower()
                                for doc_type, keywords in self.document_type_mapping.items():
                                    if any(keyword in section_lower for keyword in keywords):
                                        if "Documentazione_Specifica" not in structured_info:
                                            structured_info["Documentazione_Specifica"] = {}
                                        
                                        if doc_type not in structured_info["Documentazione_Specifica"]:
                                            structured_info["Documentazione_Specifica"][doc_type] = []
                                        
                                        # Extract sentences containing keywords
                                        sentences = re.split(r'[.;!?]\s+', section_content)
                                        for sentence in sentences:
                                            sentence_lower = sentence.lower()
                                            if any(keyword in sentence_lower for keyword in keywords):
                                                clean_sentence = clean_text(sentence)
                                                if clean_sentence and len(clean_sentence) > 15:
                                                    if clean_sentence not in structured_info["Documentazione_Specifica"][doc_type]:
                                                        structured_info["Documentazione_Specifica"][doc_type].append(clean_sentence)
            
            # Look for paragraphs containing documentation keywords
            doc_paragraphs = []
            for p in soup.find_all('p'):
                p_text = p.get_text().lower()
                if any(keyword in p_text for keyword in self.doc_keywords):
                    clean_p = clean_text(p.get_text())
                    if clean_p and len(clean_p) > 30:  # Only include substantive paragraphs
                        doc_paragraphs.append(clean_p)
                        
                        # Check for specific document types
                        for doc_type, keywords in self.document_type_mapping.items():
                            if any(keyword in p_text for keyword in keywords):
                                if "Documentazione_Specifica" not in structured_info:
                                    structured_info["Documentazione_Specifica"] = {}
                                
                                if doc_type not in structured_info["Documentazione_Specifica"]:
                                    structured_info["Documentazione_Specifica"][doc_type] = []
                                
                                if clean_p not in structured_info["Documentazione_Specifica"][doc_type]:
                                    structured_info["Documentazione_Specifica"][doc_type].append(clean_p)
            
            if doc_paragraphs:
                if "Documentazione_Paragrafi" not in structured_info:
                    structured_info["Documentazione_Paragrafi"] = []
                structured_info["Documentazione_Paragrafi"].extend(doc_paragraphs)
            
            # Check sections with standard names for documentation requirements
            standard_doc_section_names = [
                "Documentazione", "Allegati", "Documenti da presentare", "Presentazione della domanda",
                "Modalità di presentazione", "Documenti richiesti", "Modulistica", "Domanda di contributo"
            ]
            
            for section_name in standard_doc_section_names:
                # Look for sections with these exact names
                section_elements = soup.find_all(['div', 'section'], id=lambda x: x and section_name.lower() in x.lower())
                section_elements.extend(soup.find_all(['div', 'section'], class_=lambda x: x and section_name.lower() in x.lower()))
                
                for section in section_elements:
                    section_text = clean_text(section.get_text())
                    if section_text:
                        # Store the entire section text
                        if "Documentazione_Sezioni" not in structured_info:
                            structured_info["Documentazione_Sezioni"] = []
                        structured_info["Documentazione_Sezioni"].append(f"{section_name}: {section_text}")
                        
                        # Extract list items if present
                        list_items = []
                        for ul in section.find_all(['ul', 'ol']):
                            for li in ul.find_all('li'):
                                item_text = clean_text(li.get_text())
                                if item_text:
                                    list_items.append(item_text)
                        
                        if list_items:
                            if "Documentazione_Necessaria" not in structured_info:
                                structured_info["Documentazione_Necessaria"] = []
                            structured_info["Documentazione_Necessaria"].extend(list_items)
                            
                            # Check for specific document types in list items
                            for item in list_items:
                                item_lower = item.lower()
                                for doc_type, keywords in self.document_type_mapping.items():
                                    if any(keyword in item_lower for keyword in keywords):
                                        if "Documentazione_Specifica" not in structured_info:
                                            structured_info["Documentazione_Specifica"] = {}
                                        
                                        if doc_type not in structured_info["Documentazione_Specifica"]:
                                            structured_info["Documentazione_Specifica"][doc_type] = []
                                        
                                        if item not in structured_info["Documentazione_Specifica"][doc_type]:
                                            structured_info["Documentazione_Specifica"][doc_type].append(item)
        
        except Exception as e:
            logger.error(f"Error extracting documentation sections: {e}")
            # Don't crash - just add an error note
            structured_info["Documentazione_Error"] = f"Error processing documentation sections: {str(e)}"
    
    def _extract_documentation_fallback(self, soup: BeautifulSoup, main_content: str, structured_info: Dict[str, Any]) -> None:
        """
        Fallback method to extract documentation even when no dedicated sections are found.
        Aggressively searches for any mention of documentation requirements.
        
        Args:
            soup (BeautifulSoup): The parsed HTML content.
            main_content (str): Main content of the page.
            structured_info (Dict[str, Any]): The dictionary to update with findings.
        """
        # Search for sentences containing documentation keywords
        sentences = re.split(r'[.!?]\s+', main_content)
        doc_sentences = []
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(keyword in sentence_lower for keyword in self.doc_keywords):
                clean_sentence = clean_text(sentence)
                if clean_sentence and len(clean_sentence) > 20:
                    doc_sentences.append(clean_sentence)
                    
                    # Check for specific document types
                    for doc_type, keywords in self.document_type_mapping.items():
                        if any(keyword in sentence_lower for keyword in keywords):
                            if "Documentazione_Specifica" not in structured_info:
                                structured_info["Documentazione_Specifica"] = {}
                            
                            if doc_type not in structured_info["Documentazione_Specifica"]:
                                structured_info["Documentazione_Specifica"][doc_type] = []
                            
                            if clean_sentence not in structured_info["Documentazione_Specifica"][doc_type]:
                                structured_info["Documentazione_Specifica"][doc_type].append(clean_sentence)
        
        if doc_sentences:
            structured_info["Documentazione_Fallback"] = doc_sentences
        
        # Look for buttons or links related to documentation
        doc_links = []
        for a in soup.find_all('a', href=True):
            a_text = a.get_text().lower()
            a_href = a['href'].lower()
            
            # Check if link text or URL contains documentation keywords
            if any(keyword in a_text for keyword in self.doc_keywords) or any(keyword in a_href for keyword in self.doc_keywords):
                link_text = clean_text(a.get_text())
                if link_text:
                    doc_links.append(f"{link_text} - {a['href']}")
        
        if doc_links:
            structured_info["Documentazione_Links"] = doc_links
    
    def _extract_surface_information(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extracts surface-level information about the grant.
        Enhanced to look for deadlines, funding amounts, and eligibility criteria.
        
        Args:
            soup (BeautifulSoup): The parsed HTML content.
            
        Returns:
            Dict[str, Any]: Extracted surface information.
        """
        try:
            surface_info = {}
            
            # Try to extract common grant details that are often displayed prominently
            
            # Look for deadlines
            deadline_patterns = ['scadenz', 'termin', 'deadline', 'entro il', 'fino al']
            for pattern in deadline_patterns:
                # Look in headings and strong text
                for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'b']):
                    if pattern in element.get_text().lower():
                        # Get the full sentence containing the deadline
                        parent = element.parent
                        if parent:
                            parent_text = clean_text(parent.get_text())
                            if parent_text and len(parent_text) < 200:  # Only reasonable-length content
                                if "Scadenza" not in surface_info:
                                    surface_info["Scadenza"] = []
                                surface_info["Scadenza"].append(parent_text)
                                break
            
            # Look for funding amounts
            funding_patterns = [r'€\s*[\d.,]+', r'\d+(?:\.\d+)?\s*(?:mila|milioni|mln)?(?:\s*di)?\s*euro', 
                               r'contributo\s+(?:massimo|minimo|fino a)', r'finanziamento\s+(?:massimo|minimo|fino a)']
            
            for element in soup.find_all(['p', 'li', 'td', 'strong', 'b']):
                element_text = element.get_text()
                for pattern in funding_patterns:
                    if re.search(pattern, element_text, re.IGNORECASE):
                        clean_text_value = clean_text(element_text)
                        if clean_text_value and len(clean_text_value) < 300:
                            if "Finanziamento" not in surface_info:
                                surface_info["Finanziamento"] = []
                            surface_info["Finanziamento"].append(clean_text_value)
                            break
            
            # Look for beneficiaries/eligibility
            eligibility_patterns = ['beneficiari', 'destinatari', 'possono partecipare', 'possono presentare',
                                  'requisiti', 'ammissibili', 'ammissibilità']
            
            for pattern in eligibility_patterns:
                # Look in headings
                for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                    if pattern in heading.get_text().lower():
                        # Get content following the heading
                        content = ""
                        current = heading.next_sibling
                        
                        while current and not (hasattr(current, 'name') and current.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                            if hasattr(current, 'get_text'):
                                text = clean_text(current.get_text())
                                if text:
                                    content += text + " "
                            current = current.next_sibling
                        
                        if content:
                            if "Beneficiari" not in surface_info:
                                surface_info["Beneficiari"] = []
                            
                            # Check if there's a list following
                            list_items = re.findall(r'(?:^|\s)[\•\-\*]\s+([^\n\•\-\*]+)', content)
                            if list_items:
                                surface_info["Beneficiari"].extend([clean_text(item) for item in list_items if clean_text(item)])
                            else:
                                # Just add the content if it's reasonably sized
                                if len(content) < 500:
                                    surface_info["Beneficiari"].append(content)
                                else:
                                    # Extract first 2 sentences if too long
                                    sentences = re.split(r'[.!?]+', content)
                                    if sentences:
                                        summary = '. '.join(sentences[:2]) + '.'
                                        surface_info["Beneficiari"].append(summary)
                            break
            
            # Also look for important dates
            date_patterns = [
                r'\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}',  # DD/MM/YYYY or DD-MM-YYYY
                r'\d{1,2}\s+(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+\d{4}'  # DD Month YYYY
            ]
            
            for pattern in date_patterns:
                for element in soup.find_all(['p', 'li', 'td', 'strong', 'b']):
                    element_text = element.get_text()
                    if re.search(pattern, element_text, re.IGNORECASE):
                        # Only include if it also mentions a grant-related term
                        if any(term in element_text.lower() for term in ['scadenz', 'apertura', 'chiusura', 'bando', 'domanda', 'presentazione']):
                            clean_text_value = clean_text(element_text)
                            if clean_text_value and len(clean_text_value) < 300:
                                if "Date_Importanti" not in surface_info:
                                    surface_info["Date_Importanti"] = []
                                surface_info["Date_Importanti"].append(clean_text_value)
                                break
            
            return surface_info
        except Exception as e:
            logger.error(f"Error extracting surface information: {e}")
            return {}
    
    def extract_pdf_links(self, html_content: str, base_url: str) -> List[Dict[str, Any]]:
        """
        Extracts links to PDF files from HTML content with contextual information.
        Enhanced to better identify documentation PDFs.
        
        Args:
            html_content (str): The HTML content to parse.
            base_url (str): The base URL for resolving relative links.
            
        Returns:
            List[Dict[str, Any]]: A list of PDF information with URL and context.
        """
        if not html_content:
            return []
            
        try:
            soup = BeautifulSoup(html_content, self.parser)
            pdf_links = []
            
            # First pass: look for PDFs with documentation-related context
            doc_pdfs = []
            
            # Try to get the grant name if available
            grant_name = ""
            title_tag = soup.find('title')
            if title_tag:
                grant_name = title_tag.get_text().strip()
            
            # Extended search for PDF links
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href'].strip()
                
                # Check if it's a PDF by extension or content type
                is_pdf = False
                for pattern in config.PDF_LINK_PATTERNS:
                    if re.search(pattern, href, re.IGNORECASE):
                        is_pdf = True
                        break
                
                # Also check link text for PDF indicators
                if not is_pdf and a_tag.text:
                    if re.search(r'\.pdf|documento|allegato|modulistic', a_tag.text, re.IGNORECASE):
                        is_pdf = True
                
                if is_pdf:
                    absolute_url = urljoin(base_url, href)
                    
                    # Extract context from surrounding elements
                    context = ""
                    
                    # Check for documentation-specific keywords in link text or parent elements
                    link_text = a_tag.get_text().strip().lower()
                    is_doc_related = False
                    
                    # Look for documentation keywords in the link text
                    if any(keyword in link_text for keyword in self.doc_keywords):
                        is_doc_related = True
                    
                    # Build a more comprehensive context
                    context_elements = []
                    
                    # Get text from the link itself
                    if a_tag.get_text().strip():
                        context_elements.append(a_tag.get_text().strip())
                    
                    # Look for heading or label above the link
                    prev_heading = a_tag.find_previous(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'label', 'strong', 'b'])
                    if prev_heading and prev_heading.get_text().strip():
                        heading_text = prev_heading.get_text().strip().lower()
                        context_elements.append(prev_heading.get_text().strip())
                        
                        # Check if the heading contains documentation keywords
                        if any(keyword in heading_text for keyword in self.doc_keywords):
                            is_doc_related = True
                    
                    # Get parent element context
                    parent = a_tag.parent
                    if parent and parent.name in ['li', 'td', 'div', 'p']:
                        parent_text = parent.get_text().strip()
                        # Only include reasonably sized context
                        if 10 < len(parent_text) < 300 and parent_text not in context_elements:
                            context_elements.append(parent_text)
                            
                            # Check parent text for documentation keywords
                            if any(keyword in parent_text.lower() for keyword in self.doc_keywords):
                                is_doc_related = True
                    
                    # Use filename as last resort
                    if not context_elements:
                        filename = os.path.basename(href)
                        if filename:
                            context_elements.append(filename)
                    
                    # Combine all context elements
                    context = " - ".join(context_elements)
                    
                    # If we have a grant name and no proper context, include the grant name
                    if grant_name and not context:
                        context = f"PDF dal bando: {grant_name}"
                    
                    # Determine priority based on filename, context, and if it's documentation-related
                    is_priority = any(pattern in href.lower() or pattern in context.lower() 
                                    for pattern in config.PRIORITY_PDF_PATTERNS)
                    
                    # Check filename for documentation keywords
                    filename_lower = os.path.basename(href).lower()
                    for doc_pattern in self.doc_section_patterns:
                        if re.search(doc_pattern, filename_lower):
                            is_doc_related = True
                            is_priority = True
                            break
                    
                    # Check for specific document type keywords in the filename or context
                    for doc_type, keywords in self.document_type_mapping.items():
                        if any(keyword in filename_lower for keyword in keywords) or \
                           any(keyword in context.lower() for keyword in keywords):
                            is_doc_related = True
                            is_priority = True
                            break
                    
                    # If it's documentation-related, boost priority
                    if is_doc_related:
                        is_priority = True
                        
                    pdf_info = {
                        'url': absolute_url,
                        'context': normalize_whitespace(context),
                        'text': normalize_whitespace(a_tag.get_text()),
                        'priority': is_priority,
                        'is_doc_related': is_doc_related
                    }
                    
                    # Add to appropriate list
                    if is_doc_related:
                        doc_pdfs.append(pdf_info)
                    else:
                        pdf_links.append(pdf_info)
            
            # Special search for "documentazione" section links
            for section in soup.find_all(['div', 'section']):
                section_text = section.get_text().lower()
                if any(re.search(pattern, section_text) for pattern in self.doc_section_patterns):
                    # Found a documentation section, extract all links
                    for a_tag in section.find_all('a', href=True):
                        href = a_tag['href'].strip()
                        if any(href.lower().endswith(ext) for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip']):
                            absolute_url = urljoin(base_url, href)
                            
                            # Skip if we already have this URL
                            if any(pdf['url'] == absolute_url for pdf in doc_pdfs + pdf_links):
                                continue
                            
                            context = a_tag.get_text().strip()
                            if not context:
                                prev_heading = section.find_previous(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                                if prev_heading:
                                    context = f"Documento dalla sezione: {prev_heading.get_text()}"
                                else:
                                    context = "Documento dalla sezione documentazione"
                            
                            pdf_info = {
                                'url': absolute_url,
                                'context': normalize_whitespace(context),
                                'text': normalize_whitespace(a_tag.get_text()),
                                'priority': True,
                                'is_doc_related': True
                            }
                            
                            doc_pdfs.append(pdf_info)
            
            # Combine lists, prioritizing documentation PDFs
            combined_links = doc_pdfs + pdf_links
            
            logger.info(f"Found {len(combined_links)} document links on {base_url} ({len(doc_pdfs)} documentation-related)")
            return combined_links
        except Exception as e:
            logger.error(f"Error extracting PDF links from {base_url}: {e}")
            # Return empty list on error rather than crashing
            return []
    
    def close(self):
        """Close the session."""
        self.session.close()
        logger.info("Web scraper session closed")
