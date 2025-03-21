"""
Handles downloading and processing PDF files to extract relevant text.
Enhanced to better identify documentation requirements and handle errors gracefully.
"""
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
        
        # Documentation-specific patterns for more targeted extraction
        self.doc_keywords = [
            'document', 'allegat', 'modulistic', 'certificaz', 
            'richiest', 'presentare', 'obbligo', 'necessari',
            'domanda', 'application', 'richiesta', 'presentazione',
            'firma', 'signature', 'digitale', 'copia', 'identity',
            'identità', 'dichiarazione', 'declaration', 'formulario',
            'modulo', 'form', 'attestazione', 'certification',
            'visura', 'camerale', 'bilancio', 'curriculum', 'fattur',
            'quietanz', 'business plan', 'contribut', 'report', 'relazion'
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
            r'prerequisiti[\s]+documentali',
            r'(?:carta|documenti)[\s]+(?:d\'identità|identità)',
            r'(?:curriculum|cv)[\s]+(?:vitae|professionale)',
            r'scheda[\s]+(?:progett|tecnica)',
            r'piano[\s]+(?:finanziario|economic|spese)',
            r'business[\s]+plan',
            r'visura[\s]+camerale',
            r'dichiaraz[\s]+(?:redditi|iva)',
            r'quietanz[ae]'
        ]
        
        # Define target documentation items to look for - matches the analyzer
        self.target_documentation = [
            {"name": "scheda progettuale", "keywords": ["scheda progett", "scheda del progett", "progett", "piano di sviluppo"]},
            {"name": "piano finanziario delle entrate e delle spese", "keywords": ["piano finanziar", "budget", "entrate e spese", "piano delle spese", "previsione di spesa"]},
            {"name": "programma di investimento", "keywords": ["programma di invest", "piano di invest", "investiment"]},
            {"name": "dichiarazione sul rispetto del DNSH", "keywords": ["DNSH", "Do No Significant Harm", "dichiarazione DNSH", "rispetto del DNSH"]},
            {"name": "copia delle ultime due dichiarazioni dei redditi", "keywords": ["dichiarazion", "redditi", "dichiarazione dei redditi", "modello unico", "modello 730"]},
            {"name": "dichiarazioni IVA", "keywords": ["IVA", "dichiarazione IVA", "dichiarazioni IVA", "imposta valore aggiunto"]},
            {"name": "situazione economica e patrimoniale", "keywords": ["situazione economic", "situazione patrimonial", "stato patrimonial", "bilancio", "conto economic"]},
            {"name": "conto economico previsionale", "keywords": ["conto economic", "economic prevision", "prevision", "bilancio prevision"]},
            {"name": "documenti giustificativi di spesa", "keywords": ["giustificativ", "spesa", "document di spesa", "fattur", "quietanz"]},
            {"name": "relazione dei lavori eseguiti", "keywords": ["relazione", "lavori eseguit", "relazione di esecuzione", "relazione tecnica"]},
            {"name": "materiale promozionale", "keywords": ["material promozional", "promozion", "marketing", "pubblicit"]},
            {"name": "informazioni su compagine sociale", "keywords": ["compagine social", "assetto societari", "soc", "struttura societaria"]},
            {"name": "elenco delle agevolazioni pubbliche", "keywords": ["agevolazion", "contribut", "finanziam", "aiuti di stato", "de minimis"]},
            {"name": "dichiarazione di inizio attività", "keywords": ["inizio attività", "DIA", "SCIA", "dichiarazione di inizio", "avvio attivit"]},
            {"name": "progetto imprenditoriale", "keywords": ["progetto imprenditori", "business idea", "idea imprenditori", "proposta imprenditori"]},
            {"name": "pitch", "keywords": ["pitch", "presentazione", "elevator pitch", "pitch deck"]},
            {"name": "curriculum vitae", "keywords": ["curriculum", "CV", "curriculum vitae", "esperienza", "competenze"]},
            {"name": "curriculum vitae team imprenditoriale", "keywords": ["curriculum team", "CV team", "team imprenditori", "soci", "fondatori"]},
            {"name": "dichiarazione sulla localizzazione", "keywords": ["localizzazione", "ubicazione", "sede", "luogo", "dichiarazione localizzazione"]},
            {"name": "atto di assenso del proprietario", "keywords": ["assenso", "propriet", "autorizzazione propriet", "consenso propriet"]},
            {"name": "contratto di locazione", "keywords": ["locazion", "affitto", "contratto di locazione", "contratto d'affitto"]},
            {"name": "contratto di comodato", "keywords": ["comodato", "comodato d'uso", "contratto di comodato"]},
            {"name": "certificazione qualità", "keywords": ["certificazione qualit", "ISO", "certificato di qualit", "sistema qualit"]},
            {"name": "fatture elettroniche", "keywords": ["fattur", "fattura elettronic", "fatturazione elettronic", "e-fattura"]},
            {"name": "quietanze originali", "keywords": ["quietanz", "ricevut", "pagament", "bonifico", "pagamento effettuato"]},
            {"name": "Business plan", "keywords": ["business plan", "piano di business", "piano aziendale", "piano d'impresa"]},
            {"name": "dichiarazione sostitutiva", "keywords": ["dichiarazione sostitutiva", "autocertificazione", "DPR 445", "445/2000"]},
            {"name": "copia dei pagamenti effettuati", "keywords": ["pagament", "bonifico", "estratto conto", "ricevuta di pagamento"]},
            {"name": "dichiarazione di fine corso", "keywords": ["fine corso", "completamento corso", "attestazione finale", "conclusione corso"]},
            {"name": "attestato di frequenza", "keywords": ["attestato", "frequenza", "partecipazione", "certificato di frequenza"]},
            {"name": "report di self-assessment SUSTAINability", "keywords": ["self-assessment", "sustainability", "sostenibilit", "valutazione sostenibilit"]},
            {"name": "relazione finale di progetto", "keywords": ["relazione final", "report final", "conclusione progett", "progetto concluso"]},
            {"name": "Atto di conferimento", "keywords": ["conferimento", "atto di conferimento", "conferimento incarico", "mandato"]},
            {"name": "investitore esterno", "keywords": ["investitor", "finanziator", "business angel", "venture capital", "investimento esterno"]},
            {"name": "Delega del Legale rappresentante", "keywords": ["delega", "legale rappresentante", "rappresentanza", "procura"]},
            {"name": "Budget dei costi", "keywords": ["budget", "costi", "preventivo", "piano dei costi", "previsione costi"]},
            {"name": "Certificato di attribuzione del codice fiscale", "keywords": ["codice fiscale", "certificato attribuzione", "attribuzione codice", "agenzia entrate"]},
            {"name": "Analisi delle entrate", "keywords": ["analisi entrate", "entrate", "ricavi", "introiti", "analisi ricavi"]},
            {"name": "DURC", "keywords": ["DURC", "regolarità contributiva", "documento unico", "contributi"]},
            {"name": "Dichiarazione antiriciclaggio", "keywords": ["antiriciclaggio", "riciclaggio", "AML", "D.lgs 231"]},
            {"name": "Dichiarazioni antimafia", "keywords": ["antimafia", "certificazione antimafia", "informativa antimafia", "D.lgs 159"]},
            {"name": "fideiussione", "keywords": ["fideiussion", "garanzia", "polizza fideiussoria", "garanzia bancaria"]},
            {"name": "Casellario Giudiziale", "keywords": ["casellario", "giudiziale", "certificato penale", "carichi pendenti"]},
            {"name": "Fideiussione Provvisoria", "keywords": ["fideiussione provvisoria", "garanzia provvisoria", "cauzione provvisoria"]},
            {"name": "contributo ANAC", "keywords": ["ANAC", "autorità anticorruzione", "contributo gara"]},
            {"name": "DICHIARAZIONE D'INTENTI", "keywords": ["intenti", "dichiarazione d'intenti", "lettera d'intenti", "manifestazione interesse"]},
            {"name": "DICHIARAZIONE INTESTAZIONE FIDUCIARIA", "keywords": ["intestazione fiduciaria", "fiduciari", "trustee", "fiduciante"]},
            {"name": "certificato di regolarità fiscale", "keywords": ["regolarità fiscal", "agenzia entrate", "debiti fiscali", "imposte"]},
            {"name": "certificato di iscrizione al registro delle imprese", "keywords": ["registro imprese", "iscrizione camera", "CCIAA", "camera di commercio"]},
            {"name": "piano di sicurezza", "keywords": ["sicurezza", "piano di sicurezza", "PSC", "coordinamento sicurezza"]},
            {"name": "certificato di conformità", "keywords": ["conformità", "certificato conformità", "dichiarazione conformità", "attestazione conformità"]},
            {"name": "Attestazione del professionista", "keywords": ["attestazione professionist", "perizia", "relazione professionist", "relazione tecnica"]},
            {"name": "GANTT del progetto", "keywords": ["gantt", "cronoprogramma", "tempistiche", "pianificazione temporale"]},
            {"name": "atto di nomina", "keywords": ["nomina", "atto di nomina", "designazione", "incarico"]},
            {"name": "visura catastale", "keywords": ["visura catast", "catasto", "dati catastali", "estratto catastale"]},
            {"name": "DSAN", "keywords": ["DSAN", "dichiarazione sostitutiva atto notorietà", "atto notorio", "dichiarazione sostitutiva"]},
            {"name": "certificato di attribuzione di partita IVA", "keywords": ["partita IVA", "P.IVA", "attribuzione IVA", "certificato IVA"]},
            {"name": "brevetto", "keywords": ["brevett", "patent", "proprietà intellettuale", "invenzione"]},
            {"name": "licenza brevettuale", "keywords": ["licenza brevett", "licenza patent", "uso brevetto", "sfruttamento brevetto"]},
            {"name": "attestato di certificazione del libretto", "keywords": ["libretto", "libretto di certificazione", "libretto formativo", "attestato libretto"]},
            {"name": "visura camerale", "keywords": ["visura", "visura camerale", "camera di commercio", "registro imprese"]},
            {"name": "carta d'identità", "keywords": ["carta d'identità", "documento identità", "carta identità", "ID"]},
            {"name": "codice fiscale", "keywords": ["codice fiscale", "CF", "tessera sanitaria", "codice contribuente"]},
            {"name": "certificato Soa", "keywords": ["SOA", "attestazione SOA", "qualificazione", "certificato SOA"]}
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
        Enhanced to better identify documentation requirements.
        
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
            
            # Extract documentation-specific content first - more aggressively
            self._extract_documentation_content(pdf_text, result)
            
            # Look for specific documentation items
            self._extract_target_documentation_items(pdf_text, result)
            
            # Extract sections based on heading patterns - enhanced pattern
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
                    
                    # Check if this section is related to documentation
                    section_lower = section_title.lower()
                    if any(re.search(pattern, section_lower) for pattern in self.doc_section_patterns):
                        result['Documentazione'].append(f"{section_title}: {clean_text(section_content)}")
            
            # Extract lists (bullet points, numbered lists) - enhanced patterns
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
                            if any(keyword in item_lower for keyword in self.doc_keywords):
                                doc_related_items.append(item)
                        
                        if doc_related_items:
                            result['Documentazione'].extend(doc_related_items)
            
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
                
                # Check if table contains documentation keywords
                table_text = ' '.join(potential_table_rows).lower()
                if any(keyword in table_text for keyword in self.doc_keywords):
                    for row in potential_table_rows:
                        clean_row = clean_text(row)
                        if clean_row:
                            result['Documentazione'].append(f"Dalla tabella: {clean_row}")
            
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
                            
                            # If this term is documentation-related, add to documentation
                            if term.lower() in ['documentazione', 'documenti', 'allegati', 'certificazioni']:
                                result['Documentazione'].append(clean_match)
            
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
        Enhanced to be more aggressive in finding documentation content.
        
        Args:
            pdf_text (str): The PDF text content to analyze.
            result (Dict[str, Any]): The result dictionary to update.
        """
        try:
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
                        next_header_match = re.search(r'(?:\n|\r\n)[A-Z][A-Za-z0-9\s\-,]+[\.\:]?(?:\n|\r\n)', pdf_text[end_idx:end_idx + 3000])
                        
                        if next_header_match:
                            section_content = pdf_text[end_idx:end_idx + next_header_match.start()]
                        else:
                            # Limit to a reasonable length if no next header found
                            section_content = pdf_text[end_idx:end_idx + 2000]
                        
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
                sentences = re.split(r'[.;!?]\s+', pdf_text)
                
                for sentence in sentences:
                    sentence_lower = sentence.lower()
                    if any(keyword in sentence_lower for keyword in self.doc_keywords):
                        clean_sentence = clean_text(sentence)
                        if clean_sentence and len(clean_sentence) > 20:
                            result["Documentazione"].append(clean_sentence)
                            
                            # Check if this looks like a list header
                            is_list_header = re.search(r'(?:seguent|necessari|richied|presentare|allegare)', sentence_lower)
                            if is_list_header:
                                # Try to find subsequent list items
                                sentence_index = sentences.index(sentence)
                                for i in range(sentence_index+1, min(sentence_index+6, len(sentences))):
                                    next_sent = sentences[i]
                                    # Check if it looks like a list item
                                    if re.match(r'^[\s]*[-•*]\s|^\d+[.)\s]', next_sent):
                                        clean_next = clean_text(next_sent)
                                        if clean_next:
                                            result["Documentazione"].append(clean_next)
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
                                if clean_sentence and len(clean_sentence) > 15:
                                    result["Documentazione"].append(f"{doc_item['name']}: {clean_sentence}")
                
                # If item name itself appears in the text
                if not item_found and doc_item['name'].lower() in pdf_text_lower:
                    # Find sentences containing this item name
                    for sentence in sentences:
                        sentence_lower = sentence.lower()
                        if doc_item['name'].lower() in sentence_lower:
                            clean_sentence = clean_text(sentence)
                            if clean_sentence and len(clean_sentence) > 15:
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
        
        # Look for indented paragraphs that might be list items
        indent_pattern = re.compile(r'(?:^|\n)\s{2,}([^\n\s][^\n]{10,})', re.MULTILINE)
        indent_matches = indent_pattern.findall(text)
        if indent_matches:
            for item in indent_matches:
                clean_item = clean_text(item)
                # Only add if it doesn't look like a standard paragraph (e.g., it likely starts with a keyword)
                if clean_item and any(keyword in clean_item.lower()[:30] for keyword in self.doc_keywords):
                    list_items.append(clean_item)
        
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
            
            # Try to determine the file type directly from the URL
            parsed_url = urlparse(url)
            path = parsed_url.path.lower()
            
            # If it's not a PDF, return minimal info
            if not path.endswith('.pdf') and 'pdf' not in url.lower():
                # Try to check with a HEAD request if we're unsure
                try:
                    head_response = self.session.head(url, timeout=config.REQUEST_TIMEOUT, 
                                                   allow_redirects=True, verify=self.ssl_verify)
                    content_type = head_response.headers.get('Content-Type', '').lower()
                    if 'application/pdf' not in content_type:
                        logger.warning(f"URL {url} doesn't appear to be a PDF based on name and content type")
                        return {
                            'source': url, 
                            'context': context,
                            'error': 'Not a PDF based on URL and content type',
                            'is_priority': is_priority,
                            'is_doc_related': is_doc_related,
                            'filename': os.path.basename(path),
                            'Documentazione': [f"Il documento all'URL {url} non sembra essere un PDF."]
                        }
                except Exception as e:
                    # If we can't check with HEAD, we'll still try to download it
                    logger.warning(f"Could not verify if {url} is a PDF via HEAD: {e}, will try download anyway")
            
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