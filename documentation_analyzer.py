"""
Analyzes and summarizes grant information extracted from websites and PDFs,
with specific focus on required documentation.
"""
import logging
import re
from typing import Dict, List, Any, Set, Optional
from datetime import datetime

import nltk
from nltk.tokenize import sent_tokenize

from utils import clean_text, truncate_text

logger = logging.getLogger(__name__)

class DocumentationAnalyzer:
    """Analyzes and summarizes extracted grant information with focus on documentation requirements."""
    
    def __init__(self):
        """Initialize the documentation analyzer."""
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
        
        logger.info("Documentation analyzer initialized")
    
    def merge_grant_data(self, web_data: List[Dict[str, Any]], pdf_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merges data from web pages and PDFs into a comprehensive grant overview,
        prioritizing documentation requirements.
        
        Args:
            web_data (List[Dict[str, Any]]): Information extracted from web pages.
            pdf_data (List[Dict[str, Any]]): Information extracted from PDFs.
            
        Returns:
            Dict[str, Any]: Merged grant information.
        """
        if not web_data and not pdf_data:
            return {}
        
        # Start with basic structure
        merged_data = {
            'title': "",
            'overview': "",
            'sections': {},
            'lists': {},
            'requirements': [],
            'documentation': [],  # This is our primary focus
            'deadlines': [],
            'eligibility': [],
            'funding': [],
            'pdf_sources': []
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
        
        # Gather all sections into categories
        all_sections = {}
        
        # Process web data
        for data in web_data:
            # Extract overview from main content
            if data.get('main_content') and len(data['main_content']) > len(merged_data['overview']):
                merged_data['overview'] = data['main_content']
            
            # Merge structured info
            if 'structured_info' in data:
                for key, value in data['structured_info'].items():
                    # Check if this key might contain documentation information
                    if self._is_likely_documentation_related(key):
                        if isinstance(value, list):
                            merged_data['documentation'].extend(value)
                        else:
                            merged_data['documentation'].append(value)
                    else:
                        all_sections[key] = value
            
            # Merge lists - prioritize lists that might contain documentation info
            if 'lists' in data:
                for key, value in data['lists'].items():
                    if self._is_likely_documentation_related(key):
                        # Add directly to documentation if related to documentation
                        merged_data['documentation'].extend(value)
                    else:
                        if key not in merged_data['lists']:
                            merged_data['lists'][key] = value
                        else:
                            # Combine lists, removing duplicates
                            existing_items = set(str(item) for item in merged_data['lists'][key])
                            for item in value:
                                if str(item) not in existing_items:
                                    merged_data['lists'][key].append(item)
                                    existing_items.add(str(item))
            
            # Merge tables - just add them, as tables are harder to merge
            if 'tables' in data and data['tables']:
                table_count = len(merged_data.get('tables', []))
                if 'tables' not in merged_data:
                    merged_data['tables'] = []
                
                for table_key, table_data in data['tables'].items():
                    # Check if table might contain documentation info
                    if self._is_likely_documentation_related(table_key):
                        # Try to extract documentation info from table
                        if isinstance(table_data, list):
                            for row in table_data:
                                if isinstance(row, dict):
                                    for col_key, col_value in row.items():
                                        if self._is_likely_documentation_related(col_key):
                                            merged_data['documentation'].append(f"{col_key}: {col_value}")
                                elif isinstance(row, list) and len(row) > 0:
                                    merged_data['documentation'].append(" - ".join(str(cell) for cell in row))
                    
                    merged_data['tables'].append({
                        'title': table_key,
                        'data': table_data
                    })
        
        # Process PDF data with a specific focus on documentation
        for data in pdf_data:
            # Keep track of PDF sources
            if data.get('source'):
                pdf_info = {
                    'url': data['source'],
                    'filename': data.get('filename', ''),
                    'context': data.get('context', '')
                }
                merged_data['pdf_sources'].append(pdf_info)
            
            # Merge sections, prioritizing documentation-related ones
            if 'sections' in data:
                for key, value in data['sections'].items():
                    if self._is_likely_documentation_related(key):
                        # If it seems documentation-related, add to documentation
                        merged_data['documentation'].append(f"{key}: {value}")
                    else:
                        all_sections[key] = value
            
            # Merge lists, prioritizing documentation-related ones
            if 'lists' in data and data['lists']:
                for items in data['lists']:
                    list_title = "Informazioni dal PDF"
                    if data.get('context'):
                        list_title = data['context']
                    
                    # Check if this list might be documentation-related
                    if self._is_likely_documentation_related(list_title):
                        merged_data['documentation'].extend(items)
                    else:
                        if list_title not in merged_data['lists']:
                            merged_data['lists'][list_title] = items
                        else:
                            existing_items = set(str(item) for item in merged_data['lists'][list_title])
                            for item in items:
                                if str(item) not in existing_items:
                                    merged_data['lists'][list_title].append(item)
                                    existing_items.add(str(item))
            
            # Extract topic-specific information from PDFs
            for key in data.keys():
                # Expanded list of documentation-related terms
                documentation_terms = [
                    'document', 'allegat', 'modulistic', 'certificaz', 'modulo', 'moduli',
                    'domanda', 'presentazione', 'istanza', 'dichiaraz', 'autocertificaz',
                    'documentazione', 'necessari', 'richiesta', 'obbligatori'
                ]
                
                search_terms = ['document', 'allegat', 'modulistic', 'certificaz', 'requisit', 
                               'necessari', 'obblig', 'scadenz', 'termin', 'tempistic', 
                               'deadline', 'beneficiari', 'destinatari', 'ammissibil', 
                               'eligibil', 'contribut', 'finanz', 'budget', 'fond', 'spese']
                
                if key in search_terms and isinstance(data[key], list):
                    # Prioritize documentation-related terms
                    if any(term in key.lower() for term in documentation_terms):
                        merged_data['documentation'].extend(data[key])
                    else:
                        category = self._categorize_information(key, data[key])
                        if category:
                            merged_data[category].extend(data[key])
        
        # Further process the main content to look for documentation mentions
        if merged_data.get('overview'):
            doc_mentions = self._extract_documentation_mentions(merged_data['overview'])
            if doc_mentions:
                merged_data['documentation'].extend(doc_mentions)
        
        # Categorize all the sections
        for key, value in all_sections.items():
            # Prioritize documentation-related sections
            if self._is_likely_documentation_related(key):
                if isinstance(value, list):
                    merged_data['documentation'].extend(value)
                else:
                    merged_data['documentation'].append(value)
            else:
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
        
        # If there's very little information in documentation, look in requirements and eligibility
        if len(merged_data['documentation']) < 2 and (merged_data['requirements'] or merged_data['eligibility']):
            logger.info("Limited documentation info found, checking requirements and eligibility for potential documentation")
            # Check requirements for documentation-related information
            doc_from_req = [req for req in merged_data['requirements'] if self._is_likely_documentation_related(req)]
            merged_data['documentation'].extend(doc_from_req)
            
            # Check eligibility for documentation-related information
            doc_from_elig = [elig for elig in merged_data['eligibility'] if self._is_likely_documentation_related(elig)]
            merged_data['documentation'].extend(doc_from_elig)
        
        return merged_data
    
    def _is_likely_documentation_related(self, text: str) -> bool:
        """
        Checks if a text is likely related to documentation requirements.
        
        Args:
            text (str): The text to check.
            
        Returns:
            bool: True if likely documentation-related, False otherwise.
        """
        text_lower = text.lower()
        documentation_terms = [
            'document', 'allegat', 'modulistic', 'certificaz', 'modulo', 'moduli',
            'domanda', 'presentazione', 'istanza', 'dichiaraz', 'autocertificaz',
            'documentazione', 'necessari', 'richiesta', 'obbligatori'
        ]
        
        return any(term in text_lower for term in documentation_terms)
    
    def _extract_documentation_mentions(self, text: str) -> List[str]:
        """
        Extracts sentences that mention documentation from a text.
        
        Args:
            text (str): The text to extract from.
            
        Returns:
            List[str]: List of sentences mentioning documentation.
        """
        documentation_terms = [
            'document', 'allegat', 'modulistic', 'certificaz', 'modulo', 'moduli',
            'domanda', 'presentazione', 'istanza', 'dichiaraz', 'autocertificaz',
            'documentazione', 'necessari', 'richiesta', 'obbligatori'
        ]
        
        sentences = sent_tokenize(text)
        doc_mentions = []
        
        for sentence in sentences:
            if any(term in sentence.lower() for term in documentation_terms):
                doc_mentions.append(clean_text(sentence))
        
        return doc_mentions
    
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
        
        # Document/requirements related - expanded list of terms
        if any(term in key_lower for term in ['document', 'allegat', 'modulistic', 'certificaz', 
                                             'modulo', 'moduli', 'domanda', 'presentazione', 
                                             'istanza', 'dichiaraz', 'autocertificaz']):
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
            
            # Expanded documentation-related terms
            if re.search(r'document|allegat|modulistic|certificaz|modulo|moduli|domanda|presentazione|istanza|dichiaraz|autocertificaz', text_lower):
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
            
            # Documentation-specific keywords get higher score
            doc_keywords = [
                'document', 'allegat', 'modulistic', 'certificaz', 'modulo', 'moduli',
                'domanda', 'presentazione', 'istanza', 'dichiaraz', 'autocertificaz',
                'documentazione', 'necessari', 'richiesta', 'obbligatori'
            ]
            
            other_keywords = [
                'requisit', 'scadenz', 'termin', 'entro il', 'deadline',
                'beneficiari', 'destinatari', 'ammissibil',
                'contribut', 'finanz', 'budget', 'fond', 'euro', '€',
                'visura', 'camerale', 'bilanci', 'ula', 'dipendenti',
                'brevetto', 'patent', 'concessione', 'identità', 'digitale'
            ]
            
            for keyword in doc_keywords:
                if keyword in item.lower():
                    keyword_score += 2  # Higher score for documentation terms
            
            for keyword in other_keywords:
                if keyword in item.lower():
                    keyword_score += 1
            
            # Score items with numbers and dates higher
            if re.search(r'\d+', item):
                keyword_score += 1
            
            # Final score with emphasis on documentation
            score = length_score + keyword_score
            scored_items.append((item, score))
        
        # Sort by score (highest first) and take top items
        sorted_items = sorted(scored_items, key=lambda x: x[1], reverse=True)
        return [item[0] for item in sorted_items[:max_items]]
    
    def generate_summary(self, grant_data: Dict[str, Any]) -> str:
        """
        Generates a comprehensive, well-structured summary of the grant documentation information.
        
        Args:
            grant_data (Dict[str, Any]): The merged grant data.
            
        Returns:
            str: A formatted summary of the grant documentation information.
        """
        if not grant_data:
            return "Nessuna documentazione necessaria specificata."
        
        summary_parts = []
        
        # Title
        if grant_data.get('title'):
            summary_parts.append(f"# {grant_data['title']}")
        else:
            summary_parts.append("# Documentazione Necessaria")
        
        # Documentation section - this is our primary focus
        if grant_data.get('documentation'):
            summary_parts.append("\n## Documentazione Richiesta")
            docs = self._select_most_informative_items(grant_data['documentation'], 20)
            for doc in docs:
                summary_parts.append(f"- {doc}")
        else:
            summary_parts.append("\n## Documentazione Richiesta")
            summary_parts.append("- Informazioni specifiche sulla documentazione necessaria non trovate. Si consiglia di consultare il link del bando per dettagli.")
        
        # Brief overview - just a short context
        if grant_data.get('overview'):
            overview = truncate_text(grant_data['overview'], 300)  # Shorter overview to focus on documentation
            summary_parts.append(f"\n## Contesto del Bando\n{overview}")
        
        # Requirements section
        if grant_data.get('requirements'):
            summary_parts.append("\n## Requisiti")
            reqs = self._select_most_informative_items(grant_data['requirements'], 10)
            for req in reqs:
                summary_parts.append(f"- {req}")
        
        # Eligibility section
        if grant_data.get('eligibility'):
            summary_parts.append("\n## Beneficiari Ammissibili")
            eligs = self._select_most_informative_items(grant_data['eligibility'], 8)
            for elig in eligs:
                summary_parts.append(f"- {elig}")
        
        # Deadlines section - important for documentation submission
        if grant_data.get('deadlines'):
            summary_parts.append("\n## Scadenze per la Presentazione")
            deadlines = self._select_most_informative_items(grant_data['deadlines'], 5)
            for deadline in deadlines:
                summary_parts.append(f"- {deadline}")
        
        # Funding section - included but less emphasized
        if grant_data.get('funding'):
            summary_parts.append("\n## Informazioni sul Finanziamento")
            funds = self._select_most_informative_items(grant_data['funding'], 5) 
            for fund in funds:
                summary_parts.append(f"- {fund}")
        
        # Sources section - helpful for finding more documentation info
        if grant_data.get('pdf_sources'):
            summary_parts.append("\n## Fonti di Documentazione")
            for pdf in grant_data['pdf_sources']:
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