"""
Analyzes and summarizes grant information extracted from websites and PDFs.
Enhanced to extract specific content related to documentation requirements.
"""
import logging
import re
from typing import Dict, List, Any, Set, Optional
from datetime import datetime

import nltk
from nltk.tokenize import sent_tokenize

import config
from utils import clean_text, truncate_text

logger = logging.getLogger(__name__)

class DocumentationAnalyzer:
    """Analyzes and summarizes extracted grant information."""
    
    def __init__(self):
        """Initialize the documentation analyzer."""
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
        
        # Define documentation-specific keywords for more aggressive matching
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
        
        # Define target documentation items to extract from the content - updated with user-provided list
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
        
        logger.info("Documentation analyzer initialized with enhanced keyword matching")
    
    def merge_grant_data(self, web_data: List[Dict[str, Any]], pdf_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merges data from web pages and PDFs into a comprehensive grant overview.
        
        Args:
            web_data (List[Dict[str, Any]]): Information extracted from web pages.
            pdf_data (List[Dict[str, Any]]): Information extracted from PDFs.
            
        Returns:
            Dict[str, Any]: Merged grant information.
        """
        if not web_data and not pdf_data:
            # Create a minimal structure even when no data is available
            return {
                'title': "Informazioni Bando",
                'overview': "Informazioni sul bando in corso di elaborazione.",
                'sections': {},
                'lists': {},
                'requirements': ["È necessaria consultazione diretta del bando per dettagli specifici."],
                'documentation': ["Documentazione da verificare sul sito ufficiale del bando."],
                'deadlines': [],
                'eligibility': [],
                'funding': [],
                'pdf_sources': [],
                'raw_text': ""  # Store all text for documentation keyword searching
            }
        
        # Start with basic structure
        merged_data = {
            'title': "",
            'overview': "",
            'sections': {},
            'lists': {},
            'requirements': [],
            'documentation': [],
            'deadlines': [],
            'eligibility': [],
            'funding': [],
            'pdf_sources': [],
            'raw_text': "",
            'all_content': []  # Store all content chunks for more extensive searching
        }
        
        # Set title from web data if available
        if web_data:
            for data in web_data:
                if data.get('title') and (not merged_data['title'] or 
                                         len(data['title']) > len(merged_data['title'])):
                    merged_data['title'] = data['title']
        
        # If no title from web, try to get from PDFs
        if not merged_data['title'] and pdf_data:
            for data in pdf_data:
                if data.get('context') and len(data['context']) < 100:
                    merged_data['title'] = data['context']
                    break
        
        # Still no title, use a default
        if not merged_data['title']:
            merged_data['title'] = "Informazioni Bando"
        
        # Gather all sections into categories
        all_sections = {}
        
        # Process web data
        for data in web_data:
            # Extract overview from main content
            if data.get('main_content'):
                if len(data['main_content']) > len(merged_data['overview']):
                    merged_data['overview'] = data['main_content']
                # Add to raw text for searching
                merged_data['raw_text'] += " " + data['main_content']
                merged_data['all_content'].append({
                    'source': 'web_main_content',
                    'text': data['main_content']
                })
            
            # Merge structured info
            if 'structured_info' in data:
                for key, value in data['structured_info'].items():
                    all_sections[key] = value
                    # Add to collection for searching
                    if isinstance(value, list):
                        merged_data['raw_text'] += " " + " ".join(value)
                        merged_data['all_content'].append({
                            'source': f'web_structured_info_{key}',
                            'text': " ".join(value)
                        })
                    elif isinstance(value, str):
                        merged_data['raw_text'] += " " + value
                        merged_data['all_content'].append({
                            'source': f'web_structured_info_{key}',
                            'text': value
                        })
            
            # Merge lists
            if 'lists' in data:
                for key, value in data['lists'].items():
                    if key not in merged_data['lists']:
                        merged_data['lists'][key] = value
                    else:
                        # Combine lists, removing duplicates
                        existing_items = set(str(item) for item in merged_data['lists'][key])
                        for item in value:
                            if str(item) not in existing_items:
                                merged_data['lists'][key].append(item)
                                existing_items.add(str(item))
                    # Add to collection for searching
                    list_text = " ".join(str(item) for item in value)
                    merged_data['raw_text'] += " " + list_text
                    merged_data['all_content'].append({
                        'source': f'web_list_{key}',
                        'text': list_text
                    })
            
            # Merge tables
            if 'tables' in data and data['tables']:
                if 'tables' not in merged_data:
                    merged_data['tables'] = []
                
                for table_key, table_data in data['tables'].items():
                    merged_data['tables'].append({
                        'title': table_key,
                        'data': table_data
                    })
                    # Add to raw text for searching
                    if isinstance(table_data, list):
                        if table_data and isinstance(table_data[0], dict):
                            table_text = ""
                            for row in table_data:
                                row_text = " ".join(str(v) for v in row.values())
                                table_text += row_text + " "
                            merged_data['raw_text'] += " " + table_text
                            merged_data['all_content'].append({
                                'source': f'web_table_{table_key}',
                                'text': table_text
                            })
                        else:
                            table_text = ""
                            for row in table_data:
                                if isinstance(row, list):
                                    row_text = " ".join(str(cell) for cell in row)
                                else:
                                    row_text = str(row)
                                table_text += row_text + " "
                            merged_data['raw_text'] += " " + table_text
                            merged_data['all_content'].append({
                                'source': f'web_table_{table_key}',
                                'text': table_text
                            })
                    
            # Look for documentation mentions in the main content
            if data.get('main_content'):
                self._extract_documentation_from_text(data['main_content'], merged_data)
        
        # Process PDF data
        for data in pdf_data:
            # Keep track of PDF sources
            if data.get('source'):
                pdf_info = {
                    'url': data['source'],
                    'filename': data.get('filename', ''),
                    'context': data.get('context', '')
                }
                merged_data['pdf_sources'].append(pdf_info)
            
            # Add PDF content to raw text for searching
            if data.get('main_content'):
                merged_data['raw_text'] += " " + data['main_content']
                merged_data['all_content'].append({
                    'source': f'pdf_{pdf_info.get("filename", "unknown")}',
                    'text': data['main_content']
                })
            
            # Merge sections
            if 'sections' in data:
                for key, value in data['sections'].items():
                    all_sections[key] = value
                    # Add to collection
                    merged_data['raw_text'] += " " + value
                    merged_data['all_content'].append({
                        'source': f'pdf_section_{key}',
                        'text': value
                    })
            
            # Merge lists
            if 'lists' in data and data['lists']:
                for items in data['lists']:
                    list_title = "Informazioni dal PDF"
                    if data.get('context'):
                        list_title = data['context']
                    
                    if list_title not in merged_data['lists']:
                        merged_data['lists'][list_title] = items
                    else:
                        existing_items = set(str(item) for item in merged_data['lists'][list_title])
                        for item in items:
                            if str(item) not in existing_items:
                                merged_data['lists'][list_title].append(item)
                                existing_items.add(str(item))
                    
                    # Add to collection
                    list_text = " ".join(str(item) for item in items)
                    merged_data['raw_text'] += " " + list_text
                    merged_data['all_content'].append({
                        'source': f'pdf_list_{list_title}',
                        'text': list_text
                    })
            
            # Extract topic-specific information from PDFs
            for key in data.keys():
                if key in ['sections', 'lists', 'tables', 'source', 'filename', 'context', 'error', 'is_priority']:
                    continue  # Skip metadata keys
                
                if isinstance(data[key], list):
                    category = self._categorize_information(key, data[key])
                    if category:
                        merged_data[category].extend(data[key])
                        # Add to collection
                        text = " ".join(data[key])
                        merged_data['raw_text'] += " " + text
                        merged_data['all_content'].append({
                            'source': f'pdf_categorized_{category}_{key}',
                            'text': text
                        })
            
            # Look for documentation mentions in PDF text
            if data.get('main_content'):
                self._extract_documentation_from_text(data['main_content'], merged_data)
            
            # Special handling for "Documentazione" key in PDF data
            if "Documentazione" in data and isinstance(data["Documentazione"], list):
                merged_data["documentation"].extend(data["Documentazione"])
        
        # Categorize all the sections
        for key, value in all_sections.items():
            # Handle sections as either text or lists
            if isinstance(value, list):
                category = self._categorize_information(key, value)
                if category:
                    merged_data[category].extend(value)
            else:
                category = self._categorize_information(key, [value])
                if category:
                    merged_data[category].append(value)
                else:
                    merged_data['sections'][key] = value
        
        # Remove duplicate information in each category
        for category in ['requirements', 'documentation', 'deadlines', 'eligibility', 'funding']:
            if merged_data[category]:
                merged_data[category] = list(dict.fromkeys(merged_data[category]))
        
        return merged_data
    
    def _extract_documentation_from_text(self, text: str, merged_data: Dict[str, Any]) -> None:
        """
        Aggressively searches for documentation requirements in text.
        
        Args:
            text (str): The text to analyze.
            merged_data (Dict[str, Any]): The data structure to update with findings.
        """
        # Search for sentences containing documentation keywords
        sentences = sent_tokenize(text)
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            
            # Check if the sentence contains documentation keywords
            if any(keyword in sentence_lower for keyword in self.doc_keywords):
                clean_sentence = clean_text(sentence)
                
                # Determine category by keyword prevalence
                if any(kw in sentence_lower for kw in ['document', 'allegat', 'modulistic', 'certificaz']):
                    if clean_sentence and clean_sentence not in merged_data['documentation']:
                        merged_data['documentation'].append(clean_sentence)
                elif any(kw in sentence_lower for kw in ['requisit', 'necessari', 'obblig']):
                    if clean_sentence and clean_sentence not in merged_data['requirements']:
                        merged_data['requirements'].append(clean_sentence)
    
    def _categorize_information(self, key: str, values: List[str]) -> Optional[str]:
        """
        Categorizes information based on key and content.
        
        Args:
            key (str): The section title or key.
            values (List[str]): The content.
            
        Returns:
            Optional[str]: Category name or None if no specific category.
        """
        key_lower = key.lower()
        
        # Document/requirements related - enhanced with more keywords
        if any(term in key_lower for term in self.doc_keywords):
            return 'documentation'
        
        # Requirements related
        elif any(term in key_lower for term in ['requisit', 'necessari', 'obblig']):
            return 'requirements'
        
        # Deadline related
        elif any(term in key_lower for term in ['scadenz', 'termin', 'tempistic', 'deadline']):
            return 'deadlines'
        
        # Eligibility related
        elif any(term in key_lower for term in ['beneficiari', 'destinatari', 'ammissibil', 'eligibil']):
            return 'eligibility'
        
        # Funding related
        elif any(term in key_lower for term in ['contribut', 'finanz', 'budget', 'fond', 'spese']):
            return 'funding'
        
        # Content-based categorization for values
        if values:
            text = ' '.join(values)
            text_lower = text.lower()
            
            if any(term in text_lower for term in self.doc_keywords):
                return 'documentation'
            elif re.search(r'scadenz|termin|entro il|deadline', text_lower):
                return 'deadlines'
            elif re.search(r'requisit|necessari|obblig|richiesto', text_lower):
                return 'requirements'
            elif re.search(r'beneficiari|destinatari|ammissibil|eligible', text_lower):
                return 'eligibility'
            elif re.search(r'contribut|finanz|budget|fond|euro|€', text_lower):
                return 'funding'
        
        return None
    
    def extract_target_documentation(self, grant_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Extracts content specifically related to target documentation items.
        Enhanced to be more aggressive in identifying documentation requirements.
        
        Args:
            grant_data (Dict[str, Any]): The merged grant data.
            
        Returns:
            Dict[str, List[str]]: Dictionary of required documentation items with their extracted content.
        """
        extracted_docs = {}
        
        # Process each content chunk for better contextual matching
        for content_item in grant_data.get('all_content', []):
            text = content_item.get('text', '')
            if not text:
                continue
                
            # Tokenize into sentences for better context preservation
            sentences = sent_tokenize(text)
            text_lower = text.lower()
            
            # Check each target documentation item
            for doc_item in self.target_documentation:
                item_name = doc_item["name"]
                if item_name not in extracted_docs:
                    extracted_docs[item_name] = []
                
                # Check if any keyword matches in the text
                matching_keywords = [kw for kw in doc_item["keywords"] if kw.lower() in text_lower]
                
                if matching_keywords:
                    # Extract sentences containing the keywords
                    for sentence in sentences:
                        sentence_lower = sentence.lower()
                        if any(kw.lower() in sentence_lower for kw in matching_keywords):
                            clean_sentence = clean_text(sentence)
                            
                            # Only add unique, substantive sentences
                            if clean_sentence and len(clean_sentence) > 10 and clean_sentence not in extracted_docs[item_name]:
                                # Check for list items or numbered items that might follow
                                is_list_header = re.search(r'(?:seguent|necessari|richied|presentare|allegare)', sentence_lower)
                                
                                if is_list_header:
                                    # If this looks like a list header, extract the following list items too
                                    sentence_index = sentences.index(sentence)
                                    list_items = []
                                    
                                    # Look at the next 5 sentences for potential list items
                                    for i in range(sentence_index+1, min(sentence_index+6, len(sentences))):
                                        next_sent = sentences[i]
                                        # Check if it looks like a list item
                                        if re.match(r'^[\s]*[-•*]\s|^\d+[.)\s]', next_sent):
                                            list_items.append(clean_text(next_sent))
                                    
                                    if list_items:
                                        # Add the header sentence and list items
                                        extracted_docs[item_name].append(clean_sentence)
                                        extracted_docs[item_name].extend(list_items)
                                    else:
                                        # Just add the regular sentence
                                        extracted_docs[item_name].append(clean_sentence)
                                else:
                                    # Regular sentence
                                    extracted_docs[item_name].append(clean_sentence)
        
        # Also process the main text in case we missed something in chunking
        raw_text = grant_data.get('raw_text', '')
        if raw_text:
            sentences = sent_tokenize(raw_text)
            raw_text_lower = raw_text.lower()
            
            for doc_item in self.target_documentation:
                item_name = doc_item["name"]
                if item_name not in extracted_docs:
                    extracted_docs[item_name] = []
                
                # Check if we already have content for this item
                if extracted_docs[item_name]:
                    continue  # Skip items we've already found
                
                # Check if any keyword matches in the text
                matching_keywords = [kw for kw in doc_item["keywords"] if kw.lower() in raw_text_lower]
                
                if matching_keywords:
                    # Extract sentences containing the keywords
                    for sentence in sentences:
                        sentence_lower = sentence.lower()
                        if any(kw.lower() in sentence_lower for kw in matching_keywords):
                            clean_sentence = clean_text(sentence)
                            if clean_sentence and len(clean_sentence) > 15 and clean_sentence not in extracted_docs[item_name]:
                                extracted_docs[item_name].append(clean_sentence)
                                
                                # Check for list items that might follow
                                sentence_index = sentences.index(sentence)
                                for i in range(sentence_index+1, min(sentence_index+3, len(sentences))):
                                    next_sent = sentences[i]
                                    # Check if it looks like a list item
                                    if re.match(r'^[\s]*[-•*]\s|^\d+[.)\s]', next_sent):
                                        clean_next = clean_text(next_sent)
                                        if clean_next and clean_next not in extracted_docs[item_name]:
                                            extracted_docs[item_name].append(clean_next)
        
        # Check for documentation items in lists
        for list_key, list_items in grant_data.get('lists', {}).items():
            list_key_lower = list_key.lower()
            
            for doc_item in self.target_documentation:
                item_name = doc_item["name"]
                if item_name not in extracted_docs:
                    extracted_docs[item_name] = []
                
                # Match the list header with the documentation item
                if any(kw.lower() in list_key_lower for kw in doc_item["keywords"]):
                    for item in list_items:
                        if item and item not in extracted_docs[item_name]:
                            extracted_docs[item_name].append(item)
                
                # Also check each list item for keywords
                for item in list_items:
                    if item and isinstance(item, str):
                        item_lower = item.lower()
                        if any(kw.lower() in item_lower for kw in doc_item["keywords"]):
                            if item not in extracted_docs[item_name]:
                                extracted_docs[item_name].append(item)
        
        # Process general documentation sections
        for doc_item in grant_data.get('documentation', []):
            if not doc_item:
                continue
                
            doc_lower = doc_item.lower()
            
            # Match with target documentation items
            for target_item in self.target_documentation:
                item_name = target_item["name"]
                if item_name not in extracted_docs:
                    extracted_docs[item_name] = []
                
                # Check if this general documentation item matches our target item
                if any(kw.lower() in doc_lower for kw in target_item["keywords"]):
                    if doc_item not in extracted_docs[item_name]:
                        extracted_docs[item_name].append(doc_item)
        
        # Remove empty items
        extracted_docs = {k: v for k, v in extracted_docs.items() if v}
        
        return extracted_docs
    
    def generate_documentation_content(self, extracted_docs: Dict[str, List[str]], grant_title: str = "") -> str:
        """
        Generates a structured report of the extracted documentation content.
        Enhanced formatting and organization for better readability.
        
        Args:
            extracted_docs (Dict[str, List[str]]): Dictionary of documentation items with extracted content.
            grant_title (str): Title of the grant for adding context.
            
        Returns:
            str: A formatted summary of found documentation details.
        """
        if not extracted_docs:
            return "Nessuna informazione specifica sulla documentazione necessaria è stata trovata nel bando."
        
        content_parts = []
        
        # Add a title if provided
        if grant_title:
            content_parts.append(f"# Documentazione Necessaria per {grant_title}")
        else:
            content_parts.append("# Documentazione Necessaria")
        
        content_parts.append("\nDi seguito sono elencati i documenti che potrebbero essere richiesti per questo bando, con dettagli estratti direttamente dal testo del bando.\n")
        
        # Group similar documentation items
        grouped_docs = self._group_similar_items(extracted_docs)
        
        # Sort documentation items by relevance/importance
        sorted_items = self._sort_documentation_items(grouped_docs)
        
        # Add each documentation item with its extracted content
        for doc_name in sorted_items:
            content_list = grouped_docs[doc_name]
            if not content_list:
                continue
                
            content_parts.append(f"## {doc_name}")
            
            # Add each content item
            for i, content in enumerate(content_list):
                # Avoid repeating almost identical sentences
                if i > 0 and self._is_similar_to_previous(content, content_list[i-1]):
                    continue
                    
                content_parts.append(f"- {content}")
            
            # Add spacing between sections
            content_parts.append("")
        
        # Add a timestamp
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        content_parts.append(f"\n_Ultimo aggiornamento: {timestamp}_")
        
        # Add a note about further verification
        content_parts.append("\n**Nota**: Si consiglia di verificare sempre la documentazione richiesta consultando il testo completo del bando, in quanto potrebbero esserci requisiti specifici non estratti automaticamente.")
        
        return "\n".join(content_parts)
    
    def _group_similar_items(self, extracted_docs: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        Groups similar documentation items together to avoid redundancy.
        
        Args:
            extracted_docs (Dict[str, List[str]]): The extracted documentation items.
            
        Returns:
            Dict[str, List[str]]: Grouped documentation items.
        """
        # Simple implementation: keep as is but detect and merge some common overlaps
        grouped = {}
        merged_keys = set()
        
        # Define common pairs to merge
        merge_pairs = [
            ("curriculum vitae", "curriculum vitae team imprenditoriale"),
            ("copia delle ultime due dichiarazioni dei redditi", "dichiarazioni IVA"),
            ("piano finanziario delle entrate e delle spese", "programma di investimento"),
            ("copia dei pagamenti effettuati", "quietanze originali"),
            ("fatture elettroniche", "documenti giustificativi di spesa")
        ]
        
        # First handle merges
        for key1, key2 in merge_pairs:
            if key1 in extracted_docs and key2 in extracted_docs:
                # Merge under the first key
                combined_items = extracted_docs[key1] + [item for item in extracted_docs[key2] if item not in extracted_docs[key1]]
                grouped[f"{key1} / {key2}"] = combined_items
                merged_keys.add(key1)
                merged_keys.add(key2)
        
        # Then add all non-merged items
        for key, items in extracted_docs.items():
            if key not in merged_keys:
                grouped[key] = items
                
        return grouped
    
    def _sort_documentation_items(self, grouped_docs: Dict[str, List[str]]) -> List[str]:
        """
        Sorts documentation items by relevance/importance.
        
        Args:
            grouped_docs (Dict[str, List[str]]): The grouped documentation items.
            
        Returns:
            List[str]: Sorted list of documentation item keys.
        """
        # Priority items that should appear first if present
        priority_items = [
            "scheda progettuale",
            "progetto imprenditoriale",
            "Business plan",
            "piano finanziario delle entrate e delle spese",
            "DICHIARAZIONE D'INTENTI",
            "dichiarazione sostitutiva",
            "curriculum vitae"
        ]
        
        # Score each documentation item
        scored_items = {}
        for key, items in grouped_docs.items():
            # Base score on number of items and their length
            base_score = len(items)
            
            # Priority boost
            for priority in priority_items:
                if priority in key.lower():
                    base_score += 5
                    break
            
            # Boost score if item appears to be mandatory
            mandatory_patterns = ["obbligator", "necessari", "richiest", "presentare", "allegare"]
            for item in items:
                item_lower = item.lower()
                if any(pattern in item_lower for pattern in mandatory_patterns):
                    base_score += 2
                    break
            
            scored_items[key] = base_score
        
        # Sort by score (descending)
        return sorted(grouped_docs.keys(), key=lambda k: scored_items.get(k, 0), reverse=True)
    
    def _is_similar_to_previous(self, current: str, previous: str) -> bool:
        """
        Checks if the current text is very similar to the previous one.
        
        Args:
            current (str): Current text.
            previous (str): Previous text to compare with.
            
        Returns:
            bool: True if texts are very similar, False otherwise.
        """
        # Simple check: if more than 80% characters are the same, consider similar
        current = current.lower()
        previous = previous.lower()
        
        # Compare character sets
        current_chars = set(current)
        previous_chars = set(previous)
        common_chars = current_chars.intersection(previous_chars)
        
        if len(common_chars) / max(len(current_chars), len(previous_chars)) > 0.8:
            # Also check if lengths are similar
            if abs(len(current) - len(previous)) < 0.3 * max(len(current), len(previous)):
                return True
        
        return False
    
    def generate_summary(self, grant_data: Dict[str, Any]) -> str:
        """
        Generates a comprehensive summary of the grant documentation requirements.
        Enhanced to provide more structured and readable output.
        
        Args:
            grant_data (Dict[str, Any]): The merged grant data.
            
        Returns:
            str: A formatted summary of the required documentation.
        """
        if not grant_data:
            # If we have no data at all, return an empty summary
            return "Nessuna informazione sulla documentazione necessaria trovata per questo bando."
        
        # Add general grant information if available
        grant_title = grant_data.get('title', 'Bando')
        
        # Extract relevant content for each documentation target
        extracted_docs = self.extract_target_documentation(grant_data)
        
        # Check if we found specific documentation items
        if not extracted_docs:
            # If no specific items were found, try to use general documentation info
            general_docs = grant_data.get('documentation', [])
            if general_docs:
                content_parts = []
                content_parts.append(f"# Documentazione Necessaria per {grant_title}")
                content_parts.append("\nLe seguenti informazioni sulla documentazione sono state trovate nel bando:\n")
                
                for item in general_docs:
                    if item:
                        content_parts.append(f"- {item}")
                
                # Add a timestamp
                timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
                content_parts.append(f"\n_Ultimo aggiornamento: {timestamp}_")
                
                # Add a note about further verification
                content_parts.append("\n**Nota**: Si consiglia di verificare sempre la documentazione richiesta consultando il testo completo del bando.")
                
                return "\n".join(content_parts)
            else:
                # If no documentation info at all, provide a basic message
                return f"""# Documentazione Necessaria per {grant_title}

Non sono state trovate informazioni specifiche sulla documentazione richiesta per questo bando.
Si consiglia di consultare direttamente il bando disponibile al sito ufficiale per i dettagli sulla documentazione necessaria.

_Ultimo aggiornamento: {datetime.now().strftime("%d/%m/%Y %H:%M")}_
"""
        
        # Generate the structured documentation content
        documentation_content = self.generate_documentation_content(extracted_docs, grant_title)
        
        return documentation_content