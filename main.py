# part3 
"""
Web-only grant documentation crawler.
Focuses solely on website content extraction without downloading PDFs.
"""
import logging
import time
import argparse
import os
import sys
from typing import Dict, List, Any, Optional
import concurrent.futures
from tqdm import tqdm
from datetime import datetime
import traceback

import config
from db_manager import DatabaseManager
from web_scraper import WebScraper
from documentation_analyzer import DocumentationAnalyzer
from utils import setup_logging, is_valid_url

logger = logging.getLogger(__name__)

def process_grant(grant: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processes a single grant to find specific documentation requirements.
    Enhanced to extract documentation from websites only.
    
    Args:
        grant (Dict[str, Any]): The grant details from the database.
        
    Returns:
        Dict[str, Any]: The grant with updated documentation.
    """
    grant_id = grant.get('id')
    link_bando = grant.get('link_bando')
    link_sito_bando = grant.get('link_sito_bando')
    nome_bando = grant.get('nome_bando', '')  # Get the grant name if available
    
    logger.info(f"Processing grant {grant_id}: {nome_bando}")
    
    # Initialize components with enhanced website extraction capabilities
    web_scraper = WebScraper()
    doc_analyzer = DocumentationAnalyzer()
    
    web_data = []
    error_messages = []
    
    # Process main grant webpage - this is now critical since we're not using PDFs
    if link_bando and is_valid_url(link_bando):
        logger.info(f"Processing main grant URL: {link_bando}")
        html_content = web_scraper.get_page_content(link_bando)
        
        if html_content:
            # Extract comprehensive information from the webpage
            try:
                web_info = web_scraper.extract_grant_information(html_content, link_bando)
                if web_info:
                    web_data.append(web_info)
                    logger.info(f"Successfully extracted information from {link_bando}")
            except Exception as e:
                error_msg = f"Error extracting information from {link_bando}: {str(e)}"
                logger.error(error_msg)
                error_messages.append(error_msg)
        else:
            error_msg = f"Could not retrieve content from {link_bando}"
            logger.warning(error_msg)
            error_messages.append(error_msg)
    
    # Process supplementary site if different 
    if link_sito_bando and is_valid_url(link_sito_bando) and link_sito_bando != link_bando:
        logger.info(f"Processing supplementary grant URL: {link_sito_bando}")
        html_content = web_scraper.get_page_content(link_sito_bando)
        
        if html_content:
            # Extract comprehensive information from the webpage
            try:
                web_info = web_scraper.extract_grant_information(html_content, link_sito_bando)
                if web_info:
                    web_data.append(web_info)
                    logger.info(f"Successfully extracted information from {link_sito_bando}")
            except Exception as e:
                error_msg = f"Error extracting information from {link_sito_bando}: {str(e)}"
                logger.error(error_msg)
                error_messages.append(error_msg)
        else:
            error_msg = f"Could not retrieve content from {link_sito_bando}"
            logger.warning(error_msg)
            error_messages.append(error_msg)
    
    # Perform enhanced web extraction if we have some data but it may not be complete
    if web_data:
        try:
            # Perform more aggressive extraction from web data
            enhanced_web_data = _perform_enhanced_web_extraction(web_data, nome_bando)
            if enhanced_web_data:
                # Add this as the first item in web_data for higher priority
                web_data.insert(0, enhanced_web_data)
        except Exception as e:
            logger.error(f"Error performing enhanced web extraction: {str(e)}")
    
    # Clean up resources
    web_scraper.close()
    
    # Even if nothing was found, still provide some basic documentation
    if not web_data:
        basic_doc = f"""# Documentazione Necessaria per {nome_bando or 'il Bando'}

• Si consiglia di consultare direttamente i link ufficiali per ottenere i dettagli completi
• Link principale: {link_bando or 'Non disponibile'}
• Link supplementare: {link_sito_bando or 'Non disponibile'}

## Documentazione Standard
Generalmente, i bandi di questo tipo potrebbero richiedere:

• Scheda progettuale o business plan
• Piano finanziario delle entrate e delle spese
• Documentazione amministrativa (visura camerale, DURC, etc.)
• Informazioni sulla compagine sociale
• Dichiarazioni sostitutive

_Ultimo aggiornamento: {datetime.now().strftime("%d/%m/%Y %H:%M")}_
"""
        grant['documentation_summary'] = basic_doc
        return grant
    
    # Merge and analyze web data
    try:
        logger.info(f"Merging and analyzing web data for grant {grant_id}")
        # Pass empty list for pdf_data since we're not using PDFs
        merged_data = doc_analyzer.merge_grant_data(web_data, [])
        
        # Add grant name if available
        if nome_bando:
            merged_data['grant_name'] = nome_bando
            if not merged_data.get('title'):
                merged_data['title'] = nome_bando
        
        # Generate comprehensive list of found documentation items
        documentation_list = doc_analyzer.generate_summary(merged_data)
        
        # Log stats about what we found
        logger.info(f"Found documentation items: {len(merged_data.get('documentation', []))} general items")
        extracted_docs = doc_analyzer.extract_target_documentation(merged_data)
        logger.info(f"Found {len(extracted_docs)} specific documentation types")
        
        # Update the grant with the new documentation
        grant['documentation_summary'] = documentation_list
        
        logger.info(f"Completed processing for grant {grant_id}: {len(web_data)} webpage sources")
    except Exception as e:
        logger.error(f"Error analyzing grant {grant_id}: {str(e)}")
        # Provide a basic documentation message in case of error
        error_stack = traceback.format_exc()
        logger.error(f"Stack trace: {error_stack}")
        
        basic_message = f"""# Documentazione Necessaria per {nome_bando or 'il Bando'}

• Si consiglia di consultare direttamente il bando ufficiale per i dettagli specifici
• Link principale: {link_bando or 'Non disponibile'}
• Link supplementare: {link_sito_bando or 'Non disponibile'}

## Documentazione Standard
Generalmente, per bandi di questa tipologia, è necessario presentare:

• Documentazione amministrativa dell'impresa (es. visura camerale, DURC, etc.)
• Documentazione tecnica del progetto
• Documentazione economico-finanziaria
• Documentazione relativa agli aspetti di sostenibilità

_Ultimo aggiornamento: {datetime.now().strftime("%d/%m/%Y %H:%M")}_
"""
        grant['documentation_summary'] = basic_message
    
    return grant

def _perform_enhanced_web_extraction(web_data: List[Dict[str, Any]], grant_name: str) -> Dict[str, Any]:
    """
    Performs an enhanced extraction from web data.
    Searches more aggressively for documentation requirements within the web content.
    
    Args:
        web_data (List[Dict[str, Any]]): Information extracted from web pages.
        grant_name (str): Name of the grant.
        
    Returns:
        Dict[str, Any]: Enhanced grant information with focus on documentation.
    """
    # Start with an empty result
    enhanced_data = {
        'title': f"Enhanced Extraction: {grant_name}" if grant_name else "Enhanced Web Extraction",
        'structured_info': {
            'Documentazione_Specifica': {}
        }
    }
    
    # Extract content from all web pages
    all_content = ""
    for data in web_data:
        if data.get('main_content'):
            all_content += " " + data.get('main_content')
        
        # Look through all lists for documentation requirements
        if 'lists' in data:
            for list_title, list_items in data.get('lists', {}).items():
                list_title_lower = list_title.lower()
                # Check if list title suggests documentation
                if any(term in list_title_lower for term in [
                    'document', 'allegat', 'necessari', 'presentare', 'richiest',
                    'moduli', 'modello', 'certificat', 'dichiarazion'
                ]):
                    # This list likely contains documentation requirements
                    if 'Documentazione_Necessaria' not in enhanced_data['structured_info']:
                        enhanced_data['structured_info']['Documentazione_Necessaria'] = []
                    enhanced_data['structured_info']['Documentazione_Necessaria'].extend(list_items)
                    
                    # Try to categorize list items
                    for item in list_items:
                        item_lower = item.lower()
                        
                        # Check for common document types
                        for doc_type, keywords in {
                            "scheda progettuale": ["scheda", "progett", "tecnica"],
                            "business plan": ["business", "piano", "aziendale"],
                            "piano finanziario": ["finanziar", "economic", "budget"],
                            "visura camerale": ["visura", "camerale", "CCIAA"],
                            "DURC": ["DURC", "contribut", "regolarità"],
                            "curriculum": ["curriculum", "CV", "vitae"],
                            "dichiarazione sostitutiva": ["sostitutiva", "notorietà", "DPR"],
                            "documenti di spesa": ["spesa", "giustificativ", "fattur"]
                        }.items():
                            if any(keyword in item_lower for keyword in keywords):
                                if doc_type not in enhanced_data['structured_info']['Documentazione_Specifica']:
                                    enhanced_data['structured_info']['Documentazione_Specifica'][doc_type] = []
                                enhanced_data['structured_info']['Documentazione_Specifica'][doc_type].append(item)
    
    # Look for paragraphs containing documentation keywords
    if all_content:
        import re
        from nltk.tokenize import sent_tokenize
        
        # Try to use NLTK for sentence tokenization
        try:
            sentences = sent_tokenize(all_content)
        except:
            # Fallback to simple regex if NLTK fails
            sentences = re.split(r'(?<=[.!?])\s+', all_content)
        
        # Look for sentences containing documentation keywords
        doc_sentences = []
        for sentence in sentences:
            sentence_lower = sentence.lower()
            # Check if sentence contains documentation keywords
            if any(keyword in sentence_lower for keyword in [
                'document', 'allegat', 'presentare', 'necessari', 'richiest',
                'moduli', 'modello', 'certificat', 'dichiarazion', 'curriculum',
                'visura', 'DURC', 'business', 'piano', 'finanziar'
            ]):
                doc_sentences.append(sentence)
                
                # Special check for sentences that likely list documentation requirements
                if re.search(r'(?:seguent|necessari|richiest|presentare|allegare)', sentence_lower):
                    if 'Documentazione_Necessaria' not in enhanced_data['structured_info']:
                        enhanced_data['structured_info']['Documentazione_Necessaria'] = []
                    enhanced_data['structured_info']['Documentazione_Necessaria'].append(sentence)
                    
                    # Check the next 3 sentences for potential list items
                    sentence_idx = sentences.index(sentence)
                    for i in range(sentence_idx + 1, min(sentence_idx + 4, len(sentences))):
                        next_sent = sentences[i]
                        # Check if it looks like a list item
                        if re.match(r'^[\s]*[-•*]\s|^\d+[.)\s]', next_sent):
                            enhanced_data['structured_info']['Documentazione_Necessaria'].append(next_sent)
        
        # Store doc sentences if we found any
        if doc_sentences:
            enhanced_data['structured_info']['Documentazione_Paragrafi'] = doc_sentences
    
    # Add the full content (if we extracted it) for further processing
    if all_content:
        enhanced_data['main_content'] = all_content
    
    return enhanced_data

def main():
    """Main entry point for the web-only crawler."""
    parser = argparse.ArgumentParser(description='Web-only Grant Documentation Crawler')
    parser.add_argument('--log-level', default='INFO', help='Logging level')
    parser.add_argument('--max-workers', type=int, default=4, help='Maximum number of worker threads')
    parser.add_argument('--batch-size', type=int, default=0, help='Batch size (0 for all grants)')
    parser.add_argument('--verify-only', action='store_true', help='Only verify grant IDs exist without updating')
    parser.add_argument('--all-grants', action='store_true', help='Process all grants regardless of status')
    parser.add_argument('--max-retries', type=int, default=3, help='Maximum number of retries for failed processing')
    parser.add_argument('--grant-id', help='Process only a specific grant ID')
    parser.add_argument('--skip-db-update', action='store_true', help='Skip updating the database (for testing)')
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    
    logger.info("Starting web-only grant documentation crawler")
    
    try:
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Process a single grant if ID is provided
        if args.grant_id:
            try:
                if db_manager.check_grant_exists(args.grant_id):
                    # Get full grant info including name
                    response = db_manager.supabase.table(config.BANDI_TABLE) \
                        .select("id, link_bando, link_sito_bando, nome_bando") \
                        .eq("id", args.grant_id) \
                        .execute()
                    if hasattr(response, 'data') and len(response.data) > 0:
                        grants = response.data
                    else:
                        grants = [{"id": args.grant_id}]
                    logger.info(f"Processing single grant with ID: {args.grant_id}")
                else:
                    logger.error(f"Grant {args.grant_id} does not exist in the database. Exiting.")
                    return
            except Exception as e:
                logger.error(f"Error checking grant existence: {e}")
                logger.warning(f"Will try to process grant ID {args.grant_id} anyway")
                grants = [{"id": args.grant_id}]
        # Otherwise, get grants based on the flags
        elif args.all_grants:
            grants = db_manager.get_all_grants()
            if not grants:
                logger.info("No grants found in the database. Exiting.")
                return
            logger.info(f"Found {len(grants)} total grants to process")
        else:
            grants = db_manager.get_active_grants()
            if not grants:
                logger.info("No active grants found. Exiting.")
                return
            logger.info(f"Found {len(grants)} active grants to process")
        
        # Apply batch size if specified
        if args.batch_size > 0 and args.batch_size < len(grants):
            grants = grants[:args.batch_size]
            logger.info(f"Processing batch of {len(grants)} grants")
        
        # Verify grants exist first if requested
        if args.verify_only:
            existing_grants = 0
            for grant in tqdm(grants, desc="Verifying grants"):
                if db_manager.check_grant_exists(grant['id']):
                    existing_grants += 1
            
            logger.info(f"Verified {existing_grants}/{len(grants)} grants exist in the database")
            return

        # Process grants in parallel
        processed_grants = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_workers) as executor:
            # Submit all grants for processing
            future_to_grant = {executor.submit(process_grant, grant): grant for grant in grants}
            
            # Process results as they complete
            for future in tqdm(concurrent.futures.as_completed(future_to_grant), total=len(grants), desc="Processing grants"):
                grant = future_to_grant[future]
                try:
                    processed_grant = future.result()
                    processed_grants.append(processed_grant)
                except Exception as e:
                    logger.error(f"Error processing grant {grant.get('id')}: {str(e)}")
                    # Create a basic fallback message for failed grants
                    grant_name = grant.get('nome_bando', 'Bando')
                    grant['documentation_summary'] = f"""# Documentazione Necessaria per {grant_name}

• Si consiglia di consultare direttamente il bando ufficiale per i dettagli specifici
• Link principale: {grant.get('link_bando', 'Non disponibile')}
• Link supplementare: {grant.get('link_sito_bando', 'Non disponibile')}

## Documentazione Standard
Generalmente, per bandi di questa tipologia, è necessario presentare:

• Documentazione amministrativa dell'impresa
• Documentazione tecnica del progetto
• Documentazione economico-finanziaria

_Ultimo aggiornamento: {datetime.now().strftime("%d/%m/%Y %H:%M")}_
"""
                    processed_grants.append(grant)
        
        logger.info(f"Successfully processed {len(processed_grants)} grants")
        
        # Skip database update if requested
        if args.skip_db_update:
            logger.info("Skipping database update as requested")
            for i, grant in enumerate(processed_grants):
                logger.info(f"Grant {i+1}: {grant.get('id')}, documentation length: {len(grant.get('documentation_summary', ''))}")
            return
        
        # Update the database with the new documentation
        updated_count = 0
        update_errors = 0
        for grant in tqdm(processed_grants, desc="Updating database"):
            retry_count = 0
            success = False
            
            while not success and retry_count < args.max_retries:
                try:
                    if db_manager.update_documentation(grant['id'], grant['documentation_summary']):
                        updated_count += 1
                        success = True
                        logger.info(f"Successfully updated documentation for grant {grant.get('id')}")
                    else:
                        retry_count += 1
                        logger.warning(f"Update failed for grant {grant.get('id')}, retry {retry_count}/{args.max_retries}")
                        time.sleep(1)  # Short delay before retry
                except Exception as e:
                    retry_count += 1
                    logger.error(f"Error updating grant {grant.get('id')}: {str(e)}, retry {retry_count}/{args.max_retries}")
                    time.sleep(1)  # Short delay before retry
            
            if not success:
                update_errors += 1
        
        logger.info(f"Updated documentation for {updated_count} grants in the database")
        if update_errors > 0:
            logger.warning(f"Failed to update {update_errors} grants after {args.max_retries} retries")
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
    finally:
        logger.info("Web-only grant documentation crawler finished")

if __name__ == "__main__":
    main()
    