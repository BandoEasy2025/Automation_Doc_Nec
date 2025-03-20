"""
Analyzes and summarizes grant information extracted from websites and PDFs.
Enhanced to detect specific documentation requirements from a predefined list.
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
            'modulo', 'form', 'attestazione', 'certification'
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
                'raw_text': ""  # Added to store all raw text for documentation keyword searching
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
            'raw_text': ""  # Store all text for documentation keyword searching
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
            
            # Merge structured info
            if 'structured_info' in data:
                for key, value in data['structured_info'].items():
                    all_sections[key] = value
                    # Add to raw text for searching
                    if isinstance(value, list):
                        merged_data['raw_text'] += " " + " ".join(value)
                    elif isinstance(value, str):
                        merged_data['raw_text'] += " " + value
            
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
                    # Add to raw text for searching
                    merged_data['raw_text'] += " " + " ".join(str(item) for item in value)
            
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
                            for row in table_data:
                                merged_data['raw_text'] += " " + " ".join(str(v) for v in row.values())
                        else:
                            for row in table_data:
                                if isinstance(row, list):
                                    merged_data['raw_text'] += " " + " ".join(str(cell) for cell in row)
                                else:
                                    merged_data['raw_text'] += " " + str(row)
                    
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
            
            # Merge sections
            if 'sections' in data:
                for key, value in data['sections'].items():
                    all_sections[key] = value
                    # Add to raw text
                    merged_data['raw_text'] += " " + value
            
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
                    
                    # Add to raw text
                    merged_data['raw_text'] += " " + " ".join(str(item) for item in items)
            
            # Extract topic-specific information from PDFs
            for key in data.keys():
                if key in ['sections', 'lists', 'tables', 'source', 'filename', 'context', 'error', 'is_priority']:
                    continue  # Skip metadata keys
                
                if isinstance(data[key], list):
                    category = self._categorize_information(key, data[key])
                    if category:
                        merged_data[category].extend(data[key])
                        # Add to raw text
                        merged_data['raw_text'] += " " + " ".join(data[key])
            
            # Look for documentation mentions in PDF text
            if data.get('main_content'):
                self._extract_documentation_from_text(data['main_content'], merged_data)
        
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
            
        # Ensure we have something in documentation category
        if not merged_data['documentation'] and merged_data['requirements']:
            # If we have requirements but no documentation, use requirements
            merged_data['documentation'] = merged_data['requirements'].copy()
        
        # Last resort: if still no documentation, extract from overview
        if not merged_data['documentation'] and merged_data['overview']:
            self._extract_documentation_from_text(merged_data['overview'], merged_data)
            
        # Absolute last resort: add fallback message
        if not merged_data['documentation']:
            merged_data['documentation'] = [
                "Per presentare la domanda è necessaria la documentazione indicata nel bando ufficiale.",
                "Si consiglia di verificare i requisiti di ammissibilità e i documenti richiesti sul sito ufficiale.",
                "La documentazione tipicamente richiesta include: identità del richiedente, descrizione del progetto, piano finanziario, e altri documenti specifici indicati nel bando."
            ]
        
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
    
    def check_required_documentation(self, text: str) -> Dict[str, Dict[str, Any]]:
        """
        Check the text for specific documentation requirements from the predefined list.
        
        Args:
            text (str): The text to analyze.
            
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of required documentation items with their status.
        """
        text_lower = text.lower()
        results = {}
        
        # Process each required documentation item
        for doc_item in config.REQUIRED_DOCUMENTATION:
            item_name = doc_item["name"]
            keywords = doc_item["keywords"]
            
            # Check if any keyword is found in the text
            keyword_matches = []
            matching_contexts = []
            
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    keyword_matches.append(keyword)
                    
                    # Find sentences containing this keyword to provide context
                    for sentence in sent_tokenize(text):
                        sentence_lower = sentence.lower()
                        if keyword.lower() in sentence_lower:
                            clean_sentence = clean_text(sentence)
                            if clean_sentence and len(clean_sentence) > 10 and clean_sentence not in matching_contexts:
                                matching_contexts.append(clean_sentence)
            
            # Record the result
            results[item_name] = {
                "required": len(keyword_matches) > 0,
                "matching_keywords": keyword_matches,
                "context": matching_contexts[:3]  # Limit to 3 most relevant contexts
            }
        
        return results
    
    def _select_most_informative_items(self, items: List[str], max_items: int = 15) -> List[str]:
        """
        Selects the most informative items from a list.
        
        Args:
            items (List[str]): List of text items.
            max_items (int): Maximum number of items to return.
            
        Returns:
            List[str]: List of most informative items.
        """
        if not items:
            return []
            
        if len(items) <= max_items:
            return items
        
        # Score items based on information density
        scored_items = []
        for item in items:
            # Skip very short items
            if len(item) < 15:
                continue
                
            # Score longer items higher
            length_score = min(5, len(item) / 50)
            
            # Score items with specific keywords higher
            keyword_score = 0
            important_keywords = [
                'document', 'allegat', 'modulistic', 'requisit',
                'scadenz', 'termin', 'entro il', 'deadline',
                'beneficiari', 'destinatari', 'ammissibil',
                'contribut', 'finanz', 'budget', 'fond', 'euro', '€',
                'visura', 'camerale', 'bilanci', 'ula', 'dipendenti',
                'brevetto', 'patent', 'concessione', 'identità', 'digitale'
            ]
            
            for keyword in important_keywords:
                if keyword in item.lower():
                    keyword_score += 1
            
            # Score items with numbers and dates higher
            if re.search(r'\d+', item):
                keyword_score += 1
            
            # Final score
            score = length_score + keyword_score
            scored_items.append((item, score))
        
        # Sort by score (highest first) and take top items
        sorted_items = sorted(scored_items, key=lambda x: x[1], reverse=True)
        return [item[0] for item in sorted_items[:max_items]]
    
    def generate_documentation_checklist(self, required_docs: Dict[str, Dict[str, Any]]) -> str:
        """
        Generates a structured checklist of required documentation.
        
        Args:
            required_docs (Dict[str, Dict[str, Any]]): Dictionary of required documentation items.
            
        Returns:
            str: A formatted checklist of required documentation.
        """
        # Group documents by requirement status
        required_items = []
        possibly_required_items = []
        not_found_items = []
        
        for doc_name, doc_info in required_docs.items():
            if doc_info["required"]:
                # If there's context, it's definitely required
                if doc_info["context"]:
                    required_items.append((doc_name, doc_info))
                else:
                    # If keywords matched but no context, it's possibly required
                    possibly_required_items.append((doc_name, doc_info))
            else:
                not_found_items.append(doc_name)
        
        # Create the checklist
        checklist_parts = []
        
        # Add required items
        if required_items:
            checklist_parts.append("## Documentazione Obbligatoria")
            for doc_name, doc_info in required_items:
                checklist_parts.append(f"### {doc_name}")
                
                # Add context if available
                if doc_info["context"]:
                    checklist_parts.append("**Riferimenti nel bando:**")
                    for context in doc_info["context"]:
                        checklist_parts.append(f"- {context}")
                    checklist_parts.append("")
        
        # Add possibly required items
        if possibly_required_items:
            checklist_parts.append("## Documentazione Potenzialmente Richiesta")
            checklist_parts.append("*Si consiglia di verificare nel bando se i seguenti documenti sono necessari:*")
            
            for doc_name, doc_info in possibly_required_items:
                checklist_parts.append(f"- {doc_name}")
            
            checklist_parts.append("")
        
        # Add not found items
        if not_found_items:
            checklist_parts.append("## Documentazione Non Esplicitamente Menzionata")
            checklist_parts.append("*I seguenti documenti non sono stati esplicitamente menzionati nel bando:*")
            
            for doc_name in not_found_items:
                checklist_parts.append(f"- {doc_name}")
        
        # Final note
        checklist_parts.append("\n## Nota Importante")
        checklist_parts.append("Si consiglia di verificare sempre il testo completo del bando per la lista definitiva della documentazione richiesta.")
        
        return "\n".join(checklist_parts)
    
    def generate_summary(self, grant_data: Dict[str, Any]) -> str:
        """
        Generates a comprehensive, well-structured summary of the grant documentation requirements.
        
        Args:
            grant_data (Dict[str, Any]): The merged grant data.
            
        Returns:
            str: A formatted summary of the required documentation with detailed checklist.
        """
        if not grant_data:
            # If we have no data at all, return a detailed fallback message
            return """# Documentazione Necessaria per il Bando
            
## Documentazione Standard
- Documento d'identità in corso di validità del rappresentante legale
- Documentazione attestante i poteri di firma
- Documentazione finanziaria dell'impresa (es. bilanci, dichiarazioni fiscali)
- Descrizione dettagliata del progetto proposto
- Piano finanziario del progetto
- Dichiarazioni sostitutive richieste dal bando

## Nota
Per la documentazione specifica, si consiglia di consultare il testo integrale del bando.

_Ultimo aggiornamento: {data}_
""".format(data=datetime.now().strftime("%d/%m/%Y %H:%M"))
        
        # Get the raw text from the grant data for keyword searching
        raw_text = grant_data.get('raw_text', '')
        
        # If no raw text, combine all text content we can find
        if not raw_text:
            text_parts = []
            if grant_data.get('overview'):
                text_parts.append(grant_data['overview'])
            
            for doc in grant_data.get('documentation', []):
                text_parts.append(doc)
                
            for req in grant_data.get('requirements', []):
                text_parts.append(req)
                
            for section, content in grant_data.get('sections', {}).items():
                text_parts.append(content)
                
            for list_title, items in grant_data.get('lists', {}).items():
                text_parts.extend(items)
                
            raw_text = ' '.join(text_parts)
        
        # Check for required documentation
        required_docs = self.check_required_documentation(raw_text)
        
        # Generate the documentation checklist
        documentation_checklist = self.generate_documentation_checklist(required_docs)
        
        summary_parts = []
        
        # Title
        if grant_data.get('title'):
            summary_parts.append(f"# Documentazione Necessaria: {grant_data['title']}")
        else:
            summary_parts.append("# Documentazione Necessaria")
        
        # Brief overview
        if grant_data.get('overview'):
            overview = truncate_text(grant_data['overview'], 300)
            summary_parts.append(f"\n## Panoramica del Bando\n{overview}")
        
        # Add the documentation checklist
        summary_parts.append("\n" + documentation_checklist)
        
        # Additional general documentation information from the text
        if grant_data.get('documentation'):
            summary_parts.append("\n## Informazioni Aggiuntive sulla Documentazione")
            docs = self._select_most_informative_items(grant_data['documentation'], 10)
            for doc in docs:
                summary_parts.append(f"- {doc}")
        
        # Add PDF sources that might contain documentation details
        if grant_data.get('pdf_sources'):
            summary_parts.append("\n## Fonti PDF per Documentazione")
            for pdf in grant_data['pdf_sources'][:5]:  # Limit to 5 most relevant sources
                filename = pdf.get('filename', 'PDF')
                context = pdf.get('context', '')
                if context:
                    summary_parts.append(f"- {context} [{filename}]")
                else:
                    summary_parts.append(f"- {filename}")
        
        # Add a timestamp to indicate when the documentation was last updated
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        summary_parts.append(f"\n\n_Ultimo aggiornamento: {timestamp}_")
        
        return "\n".join(summary_parts)