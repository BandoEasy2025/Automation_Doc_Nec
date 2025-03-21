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
    """Analyzes and summarizes extracted grant information with focus on required documents."""
    
    def __init__(self):
        """Initialize the documentation analyzer with enhanced document type detection."""
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
        
        # Use the documentation items from config
        self.target_documentation = config.DOCUMENTATION_ITEMS
        
        # Additional mapping to group related document types
        self.document_categories = {
            "Documenti amministrativi": [
                "visura camerale", "DURC", "certificato di attribuzione del codice fiscale",
                "partita IVA", "dichiarazione sostitutiva dell'atto di notorietà", "DSAN",
                "dichiarazioni antimafia", "dichiarazione antiriciclaggio", "casellario giudiziale",
                "certificato di iscrizione al registro delle imprese", "carta d'identità"
            ],
            "Documenti progettuali": [
                "scheda progettuale", "business plan", "progetto imprenditoriale",
                "pitch", "relazione dei lavori eseguiti", "relazione finale di progetto",
                "GANTT del progetto", "piano di sicurezza e coordinamento", "materiale promozionale"
            ],
            "Documenti economico-finanziari": [
                "piano finanziario delle entrate e delle spese", "programma di investimento",
                "dichiarazioni dei redditi", "dichiarazioni IVA", "situazione economica e patrimoniale",
                "conto economico previsionale", "budget dei costi", "analisi delle entrate"
            ],
            "Documentazione di spesa": [
                "documenti giustificativi di spesa", "fatture elettroniche", "quietanze originali",
                "copia dei pagamenti effettuati", "contributo ANAC"
            ],
            "Documentazione sul personale": [
                "curriculum vitae", "curriculum vitae team imprenditoriale", "atto di nomina",
                "delega del legale rappresentante", "compagine sociale"
            ],
            "Documentazione immobiliare": [
                "dichiarazione sulla localizzazione", "atto di assenso del proprietario",
                "contratto di locazione", "contratto di comodato", "visura catastale"
            ],
            "Certificazioni e attestazioni": [
                "certificazione qualità", "certificato di conformità", "attestazione del professionista",
                "dichiarazione sul rispetto del DNSH", "attestato di frequenza", "certificato SOA"
            ]
        }
        
        logger.info("Documentation analyzer initialized with target document types")
    
    def merge_grant_data(self, web_data: List[Dict[str, Any]], pdf_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merges data from web pages and PDFs into a comprehensive grant overview.
        Enhanced to prioritize documentation extraction.
        
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
            'all_content': [],  # Store all content chunks for more extensive searching
            'specific_documentation': {}  # New field for specific document types
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
                    
                    # Process specific documentation sections
                    if key.startswith("Documentazione_Specifica") and isinstance(value, dict):
                        # This is a mapping of document types to their information
                        for doc_type, doc_info in value.items():
                            if doc_type not in merged_data['specific_documentation']:
                                merged_data['specific_documentation'][doc_type] = []
                            
                            if isinstance(doc_info, list):
                                merged_data['specific_documentation'][doc_type].extend(doc_info)
                            elif isinstance(doc_info, str):
                                merged_data['specific_documentation'][doc_type].append(doc_info)
            
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
            
            # Look for documentation mentions in the main content
            if data.get('main_content'):
                self._extract_documentation_from_text(data['main_content'], merged_data)
        
        # Process PDF data - prioritize PDF data for documentation
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
            
            # Look for documentation mentions in PDF text - this is key for our extraction
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
        
        # Aggressively extract documentation requirements if minimal found
        if len(merged_data['documentation']) < 5 and merged_data['raw_text']:
            merged_data['documentation'].extend(self._extract_documentation_aggressive(merged_data['raw_text']))
        
        # Remove duplicate information in each category
        for category in ['requirements', 'documentation', 'deadlines', 'eligibility', 'funding']:
            if merged_data[category]:
                merged_data[category] = list(dict.fromkeys(merged_data[category]))
        
        # For specific documentation, remove duplicates
        if merged_data['specific_documentation']:
            for doc_type, items in merged_data['specific_documentation'].items():
                merged_data['specific_documentation'][doc_type] = list(dict.fromkeys(items))
        
        # If we have almost no documentation after processing, add standard fallback text
        if len(merged_data['documentation']) < 3 and not merged_data['specific_documentation']:
            merged_data['documentation'].append(
                "Si consiglia di consultare direttamente il bando ufficiale per i dettagli della documentazione necessaria."
            )
            merged_data['documentation'].append(
                "Generalmente, i bandi richiedono documentazione amministrativa dell'impresa, documentazione tecnica del progetto, e documentazione economico-finanziaria."
            )
        
        return merged_data
    
    def _extract_documentation_from_text(self, text: str, merged_data: Dict[str, Any]) -> None:
        """
        Aggressively searches for documentation requirements in text.
        Enhanced to identify specific document types from the target list.
        
        Args:
            text (str): The text to analyze.
            merged_data (Dict[str, Any]): The data structure to update with findings.
        """
        # Search for sentences containing documentation keywords
        sentences = sent_tokenize(text)
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            
            # First check for direct keywords like "documentazione" or "allegati"
            general_doc_keywords = [
                'document', 'allegat', 'modulistic', 'certificaz', 
                'richiest', 'presentare', 'obbligo', 'necessari'
            ]
            
            is_doc_sentence = any(keyword in sentence_lower for keyword in general_doc_keywords)
            
            # Check for specific document types
            specific_doc_found = False
            for doc_item in self.target_documentation:
                item_name = doc_item["name"]
                matching_keywords = [kw for kw in doc_item["keywords"] if kw.lower() in sentence_lower]
                
                if matching_keywords or item_name.lower() in sentence_lower:
                    specific_doc_found = True
                    if item_name not in merged_data['specific_documentation']:
                        merged_data['specific_documentation'][item_name] = []
                
                    clean_sentence = clean_text(sentence)
                    if clean_sentence and clean_sentence not in merged_data['specific_documentation'][item_name]:
                        merged_data['specific_documentation'][item_name].append(clean_sentence)
                        
                        # Also add to general documentation
                        if clean_sentence not in merged_data['documentation']:
                            merged_data['documentation'].append(clean_sentence)
            
            # If it's a documentation sentence but no specific type was found
            if is_doc_sentence and not specific_doc_found:
                clean_sentence = clean_text(sentence)
                if clean_sentence and len(clean_sentence) > 15 and clean_sentence not in merged_data['documentation']:
                    merged_data['documentation'].append(clean_sentence)
    
    def _extract_documentation_aggressive(self, text: str) -> List[str]:
        """
        Performs a more aggressive search for documentation requirements when minimal info is found.
        Focuses on the target documentation list.
        
        Args:
            text (str): The text to analyze.
            
        Returns:
            List[str]: Found documentation requirements.
        """
        documentation = []
        
        # Look for sentences that might indicate documentation
        sentences = sent_tokenize(text)
        
        # First aggressively look for any sentence containing our target documentation keywords
        for sentence in sentences:
            sentence_lower = sentence.lower()
            
            for doc_item in self.target_documentation:
                if doc_item["name"].lower() in sentence_lower or any(kw.lower() in sentence_lower for kw in doc_item["keywords"]):
                    clean_sentence = clean_text(sentence)
                    if clean_sentence and len(clean_sentence) > 15 and clean_sentence not in documentation:
                        documentation.append(clean_sentence)
                    break
        
        # If still limited info, look for typical documentation section patterns
        if len(documentation) < 3:
            # Patterns that strongly suggest documentation requirements
            strong_indicators = [
                r'(?:allegare|presentare|documenti|documentazione)[\s]+(?:necessari|obbligatori|richiest)',
                r'(?:documentazione|documenti)[\s]+(?:a[\s]+corredo|da[\s]+presentare|richiesta)',
                r'(?:allegati|documenti)[\s]+(?:alla[\s]+domanda|al[\s]+bando)',
                r'(?:alla[\s]+domanda|al[\s]+bando)[\s]+(?:vanno|devono|dovranno)[\s]+(?:allegat|presentat)',
                r'(?:la[\s]+domanda|l\'istanza)[\s]+(?:deve|dovrà)[\s]+(?:essere[\s]+corredata|allegare)',
                r'presenta\w+[\s]+i[\s]+seguenti[\s]+documenti'
            ]
            
            for sentence in sentences:
                sentence_lower = sentence.lower()
                
                # Check against strong indicators
                for pattern in strong_indicators:
                    if re.search(pattern, sentence_lower):
                        clean_sentence = clean_text(sentence)
                        if clean_sentence and len(clean_sentence) > 15 and clean_sentence not in documentation:
                            documentation.append(clean_sentence)
                        
                        # Also check if the next sentence might be a continuation
                        idx = sentences.index(sentence)
                        if idx < len(sentences) - 1:
                            next_sentence = sentences[idx + 1]
                            # Check if it looks like a list item or continuation
                            if re.match(r'^[\s]*[-•*]\s|^\d+[.)\s]|^[a-z][.)\s]|^in[\s]+particolar', next_sentence.lower()):
                                clean_next = clean_text(next_sentence)
                                if clean_next and clean_next not in documentation:
                                    documentation.append(clean_next)
                        
                        break
        
        return documentation
    
    def _categorize_information(self, key: str, values: List[str]) -> Optional[str]:
        """
        Categorizes information based on key and content.
        Enhanced to better identify documentation sections.
        
        Args:
            key (str): The section title or key.
            values (List[str]): The content.
            
        Returns:
            Optional[str]: Category name or None if no specific category.
        """
        key_lower = key.lower()
        
        # Document/requirements related
        if any(doc_item["name"].lower() in key_lower for doc_item in self.target_documentation) or \
           any(any(kw.lower() in key_lower for kw in doc_item["keywords"]) for doc_item in self.target_documentation):
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
            
            if any(doc_item["name"].lower() in text_lower for doc_item in self.target_documentation) or \
               any(any(kw.lower() in text_lower for kw in doc_item["keywords"]) for doc_item in self.target_documentation):
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
        Enhanced to handle cases where direct extractions were already done in the web scraper.
        
        Args:
            grant_data (Dict[str, Any]): The merged grant data.
            
        Returns:
            Dict[str, List[str]]: Dictionary of required documentation items with their extracted content.
        """
        extracted_docs = {}
        
        # First, check if specific documentation was already extracted during web scraping
        if 'specific_documentation' in grant_data and grant_data['specific_documentation']:
            # Copy the already extracted specific documentation
            for doc_type, items in grant_data['specific_documentation'].items():
                if items:  # Only include if there are actual items
                    extracted_docs[doc_type] = items.copy()
        
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
                if len(extracted_docs[item_name]) >= 2:
                    continue  # Skip items we've already found enough content for
                
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
        
        # Check for documentation items in lists
        for list_key, list_items in grant_data.get('lists', {}).items():
            list_key_lower = list_key.lower()
            
            for doc_item in self.target_documentation:
                item_name = doc_item["name"]
                if item_name not in extracted_docs:
                    extracted_docs[item_name] = []
                
                # Match the list header with the documentation item
                if doc_item["name"].lower() in list_key_lower or any(kw.lower() in list_key_lower for kw in doc_item["keywords"]):
                    for item in list_items:
                        if item and item not in extracted_docs[item_name]:
                            extracted_docs[item_name].append(item)
                
                # Also check each list item for keywords
                for item in list_items:
                    if item and isinstance(item, str):
                        item_lower = item.lower()
                        if doc_item["name"].lower() in item_lower or any(kw.lower() in item_lower for kw in doc_item["keywords"]):
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
                if target_item["name"].lower() in doc_lower or any(kw.lower() in doc_lower for kw in target_item["keywords"]):
                    if doc_item not in extracted_docs[item_name]:
                        extracted_docs[item_name].append(doc_item)
        
        # Remove empty items
        extracted_docs = {k: v for k, v in extracted_docs.items() if v}
        
        return extracted_docs
    
    def generate_documentation_content(self, extracted_docs: Dict[str, List[str]], grant_title: str = "") -> str:
        """
        Generates a structured report of the extracted documentation content.
        Enhanced to produce more concise, focused bullet points.
        
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
        
        # Group documents by category for better organization
        categorized_docs = self._categorize_documents(extracted_docs)
        
        # Add each category with its documentation items
        for category, category_items in categorized_docs.items():
            if not category_items:
                continue
                
            content_parts.append(f"## {category}")
            
            # Add each document type in this category
            for doc_name, content_list in category_items.items():
                if not content_list:
                    continue
                    
                content_parts.append(f"### {doc_name}")
                
                # Add each content item - limit to 2 per document type to keep concise
                for i, content in enumerate(content_list[:2]):
                    # Avoid repeating almost identical sentences
                    if i > 0 and self._is_similar_to_previous(content, content_list[i-1]):
                        continue
                
                    # Make sure each item is a bullet point
                    if not content.startswith('•'):
                        content_parts.append(f"• {content}")
                    else:
                        content_parts.append(f"{content}")
                
                # Add spacing between sections
                content_parts.append("")
        
        # Check if there are uncategorized items
        if "Altro" in categorized_docs and categorized_docs["Altro"]:
            content_parts.append("## Altri Documenti")
            
            for doc_name, content_list in categorized_docs["Altro"].items():
                if not content_list:
                    continue
                    
                content_parts.append(f"### {doc_name}")
                
                for i, content in enumerate(content_list[:2]):
                    if i > 0 and self._is_similar_to_previous(content, content_list[i-1]):
                        continue
                        
                    # Make sure each item is a bullet point
                    if not content.startswith('•'):
                        content_parts.append(f"• {content}")
                    else:
                        content_parts.append(f"{content}")
                
                content_parts.append("")
        
        # Add timestamp
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        content_parts.append(f"\n_Ultimo aggiornamento: {timestamp}_")
        
        return "\n".join(content_parts)
    
    def _categorize_documents(self, extracted_docs: Dict[str, List[str]]) -> Dict[str, Dict[str, List[str]]]:
        """
        Categorizes documentation items into logical groups.
        
        Args:
            extracted_docs (Dict[str, List[str]]): The extracted documentation items.
            
        Returns:
            Dict[str, Dict[str, List[str]]]: Categorized documentation items.
        """
        categorized = {}
        
        for category_name, category_docs in self.document_categories.items():
            categorized[category_name] = {}
            
            for doc_name, doc_items in extracted_docs.items():
                # Check if this document belongs in this category
                if doc_name in category_docs or any(cat_doc in doc_name.lower() for cat_doc in category_docs):
                    categorized[category_name][doc_name] = doc_items
                    # Mark as categorized by removing from extracted_docs
                    extracted_docs.pop(doc_name, None)
        
        # Add "Other" category for remaining items
        if extracted_docs:
            categorized["Altro"] = extracted_docs
        
        return categorized
    
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
        Enhanced with bullet point formatting.
        
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
                        content_parts.append(f"• {item}")
                
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