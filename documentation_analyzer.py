"""
Analyzes and summarizes grant information extracted from websites and PDFs.
Focuses on finding specific documentation requirements from a predefined list.
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
    """Analyzes and summarizes extracted grant information with focus on required documentation."""
    
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
        
        logger.info("Documentation analyzer initialized with focus on specific document requirements")
    
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
        
        return merged_data
    
    def _extract_documentation_from_text(self, text: str, merged_data: Dict[str, Any]) -> None:
        """
        Searches for documentation requirements in text.
        
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
    
    def find_required_documentation(self, text: str) -> List[Dict[str, Any]]:
        """
        Finds specific documentation items from the predefined list in the text.
        Only returns items that are actually found.
        
        Args:
            text (str): The text to analyze.
            
        Returns:
            List[Dict[str, Any]]: List of found documentation items with context.
        """
        text_lower = text.lower()
        found_items = []
        
        # Process each documentation item
        for doc_item in config.DOCUMENTATION_ITEMS:
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
            
            # If we found matches, add this item to the results
            if keyword_matches and matching_contexts:
                found_items.append({
                    "name": item_name,
                    "matching_keywords": keyword_matches,
                    "context": matching_contexts[:3]  # Limit to 3 most relevant contexts
                })
        
        return found_items
    
    def generate_documentation_list(self, found_docs: List[Dict[str, Any]]) -> str:
        """
        Generates a structured list of found documentation requirements.
        
        Args:
            found_docs (List[Dict[str, Any]]): List of found documentation items.
            
        Returns:
            str: A formatted list of found documentation requirements.
        """
        if not found_docs:
            return "Non sono stati trovati riferimenti specifici a documentazione richiesta. Si consiglia di consultare il testo completo del bando."
        
        # Create the documentation list
        doc_parts = []
        
        # Header
        doc_parts.append("# Documentazione Necessaria")
        
        # Add each found documentation item with context
        for item in found_docs:
            doc_parts.append(f"## {item['name'].capitalize()}")
            
            # Add context if available
            if item["context"]:
                doc_parts.append("**Riferimenti nel bando:**")
                for context in item["context"]:
                    doc_parts.append(f"- {context}")
                doc_parts.append("")
        
        # Add timestamp
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        doc_parts.append(f"\n_Ultimo aggiornamento: {timestamp}_")
        
        return "\n".join(doc_parts)
    
    def generate_summary(self, grant_data: Dict[str, Any]) -> str:
        """
        Generates a summary of the required documentation found in the grant.
        
        Args:
            grant_data (Dict[str, Any]): The merged grant data.
            
        Returns:
            str: A formatted summary of the found documentation requirements.
        """
        if not grant_data:
            return "Non sono stati trovati riferimenti specifici a documentazione richiesta."
        
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
        
        # Find required documentation items
        found_docs = self.find_required_documentation(raw_text)
        
        # Generate the documentation list
        return self.generate_documentation_list(found_docs)