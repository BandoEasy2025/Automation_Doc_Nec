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
# """
# Enhanced main entry point for the grant documentation crawler.
# Improved to better handle cases where PDFs can't be accessed and prioritize website content.
# """
# import logging
# import time
# import argparse
# import os
# import sys
# from typing import Dict, List, Any, Optional
# import concurrent.futures
# from tqdm import tqdm
# from datetime import datetime
# import traceback

# import config
# from db_manager import DatabaseManager
# from web_scraper import WebScraper
# from pdf_processor import PDFProcessor
# from documentation_analyzer import DocumentationAnalyzer
# from utils import setup_logging, is_valid_url

# logger = logging.getLogger(__name__)

# def process_grant(grant: Dict[str, Any]) -> Dict[str, Any]:
#     """
#     Processes a single grant to find specific documentation requirements.
#     Enhanced to prioritize website content when PDFs cannot be accessed.
    
#     Args:
#         grant (Dict[str, Any]): The grant details from the database.
        
#     Returns:
#         Dict[str, Any]: The grant with updated documentation.
#     """
#     grant_id = grant.get('id')
#     link_bando = grant.get('link_bando')
#     link_sito_bando = grant.get('link_sito_bando')
#     nome_bando = grant.get('nome_bando', '')  # Get the grant name if available
    
#     logger.info(f"Processing grant {grant_id}: {nome_bando}")
    
#     # Initialize components with enhanced capabilities
#     web_scraper = WebScraper()
#     pdf_processor = PDFProcessor()
#     doc_analyzer = DocumentationAnalyzer()
    
#     web_data = []
#     pdf_data = []
#     error_messages = []
#     pdf_errors = False  # Flag to indicate PDF access errors
    
#     # Process main grant webpage - this is now more critical
#     if link_bando and is_valid_url(link_bando):
#         logger.info(f"Processing main grant URL: {link_bando}")
#         html_content = web_scraper.get_page_content(link_bando)
        
#         if html_content:
#             # Extract comprehensive information from the webpage
#             try:
#                 web_info = web_scraper.extract_grant_information(html_content, link_bando)
#                 if web_info:
#                     web_data.append(web_info)
#                     logger.info(f"Successfully extracted information from {link_bando}")
#             except Exception as e:
#                 error_msg = f"Error extracting information from {link_bando}: {str(e)}"
#                 logger.error(error_msg)
#                 error_messages.append(error_msg)
            
#             # Extract PDF links
#             try:
#                 logger.info(f"Extracting PDF links from {link_bando}")
#                 pdf_links = web_scraper.extract_pdf_links(html_content, link_bando)
                
#                 # Process priority PDFs first
#                 priority_pdfs_processed = 0
#                 for pdf_info in pdf_links:
#                     if pdf_info.get('priority', False) or pdf_info.get('is_doc_related', False):
#                         try:
#                             logger.info(f"Processing priority PDF: {pdf_info.get('url')}")
#                             pdf_result = pdf_processor.process_pdf(pdf_info)
#                             if pdf_result and not pdf_result.get('error'):
#                                 pdf_data.append(pdf_result)
#                                 priority_pdfs_processed += 1
#                                 logger.info(f"Successfully processed priority PDF: {pdf_info.get('url')}")
                                
#                                 # Limit to a reasonable number
#                                 if priority_pdfs_processed >= 8:  # Increased from 5 to 8
#                                     break
#                         except Exception as e:
#                             logger.error(f"Error processing priority PDF {pdf_info.get('url')}: {str(e)}")
#                             pdf_errors = True
#                             # Still add some basic info about the failed PDF
#                             pdf_data.append({
#                                 'source': pdf_info.get('url'),
#                                 'context': pdf_info.get('context', ''),
#                                 'error': str(e),
#                                 'Documentazione': [f"Errore nell'elaborazione del PDF: {str(e)}"]
#                             })
                
#                 # Process non-priority PDFs if needed
#                 if priority_pdfs_processed < 3:  # Increased requirement from 2 to 3
#                     non_priority_pdfs = 0
#                     for pdf_info in pdf_links:
#                         if not pdf_info.get('priority', False) and not pdf_info.get('is_doc_related', False):
#                             try:
#                                 logger.info(f"Processing non-priority PDF: {pdf_info.get('url')}")
#                                 pdf_result = pdf_processor.process_pdf(pdf_info)
#                                 if pdf_result:
#                                     # Even if there's an error, still add the PDF info
#                                     pdf_data.append(pdf_result)
#                                     if not pdf_result.get('error'):
#                                         non_priority_pdfs += 1
#                                         logger.info(f"Successfully processed non-priority PDF: {pdf_info.get('url')}")
                                    
#                                     # Limit to a reasonable number
#                                     if non_priority_pdfs >= 3:
#                                         break
#                             except Exception as e:
#                                 logger.error(f"Error processing non-priority PDF {pdf_info.get('url')}: {str(e)}")
#                                 pdf_errors = True
#             except Exception as e:
#                 error_msg = f"Error extracting PDF links from {link_bando}: {str(e)}"
#                 logger.error(error_msg)
#                 error_messages.append(error_msg)
#                 pdf_errors = True
#         else:
#             error_msg = f"Could not retrieve content from {link_bando}"
#             logger.warning(error_msg)
#             error_messages.append(error_msg)
    
#     # Process supplementary site if different - more important if main site or PDFs failed
#     if link_sito_bando and is_valid_url(link_sito_bando) and link_sito_bando != link_bando:
#         logger.info(f"Processing supplementary grant URL: {link_sito_bando}")
#         html_content = web_scraper.get_page_content(link_sito_bando)
        
#         if html_content:
#             # Extract comprehensive information from the webpage
#             try:
#                 web_info = web_scraper.extract_grant_information(html_content, link_sito_bando)
#                 if web_info:
#                     web_data.append(web_info)
#                     logger.info(f"Successfully extracted information from {link_sito_bando}")
#             except Exception as e:
#                 error_msg = f"Error extracting information from {link_sito_bando}: {str(e)}"
#                 logger.error(error_msg)
#                 error_messages.append(error_msg)
            
#             # Extract PDF links if primary PDFs failed or we have few PDFs
#             try:
#                 if pdf_errors or len(pdf_data) < 10:  # More aggressive if we had PDF errors
#                     logger.info(f"Extracting PDF links from {link_sito_bando}")
#                     pdf_links = web_scraper.extract_pdf_links(html_content, link_sito_bando)
                    
#                     # Filter out PDFs we've already processed
#                     existing_urls = {pdf.get('source', '') for pdf in pdf_data}
#                     new_pdf_links = [pdf for pdf in pdf_links if pdf.get('url') not in existing_urls]
                    
#                     # Process priority PDFs first
#                     priority_pdfs_processed = 0
#                     for pdf_info in new_pdf_links:
#                         if pdf_info.get('priority', False) or pdf_info.get('is_doc_related', False):
#                             try:
#                                 logger.info(f"Processing priority PDF from supplementary site: {pdf_info.get('url')}")
#                                 pdf_result = pdf_processor.process_pdf(pdf_info)
#                                 if pdf_result:
#                                     pdf_data.append(pdf_result)
#                                     if not pdf_result.get('error'):
#                                         priority_pdfs_processed += 1
#                                         logger.info(f"Successfully processed priority PDF: {pdf_info.get('url')}")
                                    
#                                     # Limit to a reasonable number
#                                     if priority_pdfs_processed >= 5:  # Increased from 3 to 5
#                                         break
#                             except Exception as e:
#                                 logger.error(f"Error processing priority PDF {pdf_info.get('url')}: {str(e)}")
#                                 pdf_errors = True
                    
#                     # Process non-priority PDFs if needed
#                     if pdf_errors or len(pdf_data) < 5:  # More aggressive if we had PDF errors
#                         non_priority_pdfs = 0
#                         for pdf_info in new_pdf_links:
#                             if not pdf_info.get('priority', False) and not pdf_info.get('is_doc_related', False):
#                                 try:
#                                     logger.info(f"Processing non-priority PDF from supplementary site: {pdf_info.get('url')}")
#                                     pdf_result = pdf_processor.process_pdf(pdf_info)
#                                     if pdf_result:
#                                         pdf_data.append(pdf_result)
#                                         if not pdf_result.get('error'):
#                                             non_priority_pdfs += 1
#                                             logger.info(f"Successfully processed non-priority PDF: {pdf_info.get('url')}")
                                        
#                                         # Limit to a reasonable number
#                                         if non_priority_pdfs >= 3 or len(pdf_data) >= 10:
#                                             break
#                                 except Exception as e:
#                                     logger.error(f"Error processing non-priority PDF {pdf_info.get('url')}: {str(e)}")
#                                     pdf_errors = True
#             except Exception as e:
#                 error_msg = f"Error extracting PDF links from {link_sito_bando}: {str(e)}"
#                 logger.error(error_msg)
#                 error_messages.append(error_msg)
#                 pdf_errors = True
#         else:
#             error_msg = f"Could not retrieve content from {link_sito_bando}"
#             logger.warning(error_msg)
#             error_messages.append(error_msg)
    
#     # Special handling for case where PDFs failed but we have web data
#     if pdf_errors and web_data:
#         logger.warning(f"PDF processing errors encountered for grant {grant_id}. Performing enhanced web data extraction.")
#         try:
#             # Perform more aggressive extraction from web data
#             enhanced_web_data = _perform_enhanced_web_extraction(web_data, nome_bando)
#             if enhanced_web_data:
#                 # Add this as the first item in web_data for higher priority
#                 web_data.insert(0, enhanced_web_data)
#         except Exception as e:
#             logger.error(f"Error performing enhanced web extraction: {str(e)}")
    
#     # Clean up resources
#     web_scraper.close()
#     pdf_processor.close()
    
#     # Even if nothing was found, still provide some basic documentation
#     if not web_data and not pdf_data:
#         basic_doc = f"""# Documentazione Necessaria per {nome_bando or 'il Bando'}

# ## Avviso Importante
# Non è stato possibile recuperare informazioni specifiche sulla documentazione richiesta per questo bando.
# Si consiglia di consultare direttamente i link ufficiali per ottenere i dettagli completi:

# - Link principale: {link_bando or 'Non disponibile'}
# - Link supplementare: {link_sito_bando or 'Non disponibile'}

# ## Documentazione Standard
# Generalmente, i bandi di questo tipo potrebbero richiedere:

# - Scheda progettuale o business plan
# - Piano finanziario delle entrate e delle spese
# - Documentazione amministrativa (visura camerale, DURC, etc.)
# - Informazioni sulla compagine sociale
# - Dichiarazioni sostitutive

# _Ultimo aggiornamento: {datetime.now().strftime("%d/%m/%Y %H:%M")}_
# """
#         grant['documentation_summary'] = basic_doc
#         return grant
    
#     # Merge and analyze all data
#     try:
#         logger.info(f"Merging and analyzing data for grant {grant_id}")
#         merged_data = doc_analyzer.merge_grant_data(web_data, pdf_data)
        
#         # Add grant name if available
#         if nome_bando:
#             merged_data['grant_name'] = nome_bando
#             if not merged_data.get('title'):
#                 merged_data['title'] = nome_bando
        
#         # Add error messages to the merged data
#         if error_messages:
#             if 'errors' not in merged_data:
#                 merged_data['errors'] = []
#             merged_data['errors'].extend(error_messages)
        
#         # Record PDF failures separately to inform content generation
#         if pdf_errors:
#             merged_data['pdf_errors'] = True
        
#         # Generate comprehensive list of found documentation items
#         documentation_list = doc_analyzer.generate_summary(merged_data)
        
#         # Log some stats about what we found
#         logger.info(f"Found documentation items: {len(merged_data.get('documentation', []))} general items")
#         extracted_docs = doc_analyzer.extract_target_documentation(merged_data)
#         logger.info(f"Found {len(extracted_docs)} specific documentation types")
        
#         # Update the grant with the new documentation
#         grant['documentation_summary'] = documentation_list
        
#         logger.info(f"Completed processing for grant {grant_id}: {len(web_data)} webpage sources, {len(pdf_data)} PDF sources")
#     except Exception as e:
#         logger.error(f"Error analyzing grant {grant_id}: {str(e)}")
#         # Provide a basic documentation message in case of error
#         error_stack = traceback.format_exc()
#         logger.error(f"Stack trace: {error_stack}")
        
#         basic_message = f"""# Documentazione Necessaria per {nome_bando or 'il Bando'}

# ## Nota Importante
# Non è stato possibile estrarre automaticamente la documentazione specifica per questo bando. 
# Si consiglia di consultare direttamente il bando ufficiale per i dettagli specifici.

# ### Links
# - Link principale: {link_bando or 'Non disponibile'}
# - Link supplementare: {link_sito_bando or 'Non disponibile'}

# ## Documentazione Standard
# Generalmente, per bandi di questa tipologia, è necessario presentare:

# - Documentazione amministrativa dell'impresa (es. visura camerale, DURC, etc.)
# - Documentazione tecnica del progetto
# - Documentazione economico-finanziaria
# - Documentazione relativa agli aspetti di sostenibilità

# ## Errori riscontrati
# {'; '.join(error_messages) if error_messages else 'Errore durante l\'analisi dei dati.'}

# _Ultimo aggiornamento: {datetime.now().strftime("%d/%m/%Y %H:%M")}_
# """
#         grant['documentation_summary'] = basic_message
    
#     return grant

# def _perform_enhanced_web_extraction(web_data: List[Dict[str, Any]], grant_name: str) -> Dict[str, Any]:
#     """
#     Performs an enhanced extraction from web data when PDFs can't be accessed.
#     Searches more aggressively for documentation requirements within the web content.
    
#     Args:
#         web_data (List[Dict[str, Any]]): Information extracted from web pages.
#         grant_name (str): Name of the grant.
        
#     Returns:
#         Dict[str, Any]: Enhanced grant information with focus on documentation.
#     """
#     # Start with an empty result
#     enhanced_data = {
#         'title': f"Enhanced Extraction: {grant_name}" if grant_name else "Enhanced Web Extraction",
#         'structured_info': {
#             'Documentazione_Specifica': {}
#         }
#     }
    
#     # Extract content from all web pages
#     all_content = ""
#     for data in web_data:
#         if data.get('main_content'):
#             all_content += " " + data.get('main_content')
        
#         # Look through all lists for documentation requirements
#         if 'lists' in data:
#             for list_title, list_items in data.get('lists', {}).items():
#                 list_title_lower = list_title.lower()
#                 # Check if list title suggests documentation
#                 if any(term in list_title_lower for term in [
#                     'document', 'allegat', 'necessari', 'presentare', 'richiest',
#                     'moduli', 'modello', 'certificat', 'dichiarazion'
#                 ]):
#                     # This list likely contains documentation requirements
#                     if 'Documentazione_Necessaria' not in enhanced_data['structured_info']:
#                         enhanced_data['structured_info']['Documentazione_Necessaria'] = []
#                     enhanced_data['structured_info']['Documentazione_Necessaria'].extend(list_items)
                    
#                     # Try to categorize list items
#                     for item in list_items:
#                         item_lower = item.lower()
                        
#                         # Check for common document types
#                         for doc_type, keywords in {
#                             "scheda progettuale": ["scheda", "progett", "tecnica"],
#                             "business plan": ["business", "piano", "aziendale"],
#                             "piano finanziario": ["finanziar", "economic", "budget"],
#                             "visura camerale": ["visura", "camerale", "CCIAA"],
#                             "DURC": ["DURC", "contribut", "regolarità"],
#                             "curriculum": ["curriculum", "CV", "vitae"],
#                             "dichiarazione sostitutiva": ["sostitutiva", "notorietà", "DPR"],
#                             "documenti di spesa": ["spesa", "giustificativ", "fattur"]
#                         }.items():
#                             if any(keyword in item_lower for keyword in keywords):
#                                 if doc_type not in enhanced_data['structured_info']['Documentazione_Specifica']:
#                                     enhanced_data['structured_info']['Documentazione_Specifica'][doc_type] = []
#                                 enhanced_data['structured_info']['Documentazione_Specifica'][doc_type].append(item)
    
#     # Look for paragraphs containing documentation keywords
#     if all_content:
#         import re
#         from nltk.tokenize import sent_tokenize
        
#         # Try to use NLTK for sentence tokenization
#         try:
#             sentences = sent_tokenize(all_content)
#         except:
#             # Fallback to simple regex if NLTK fails
#             sentences = re.split(r'(?<=[.!?])\s+', all_content)
        
#         # Look for sentences containing documentation keywords
#         doc_sentences = []
#         for sentence in sentences:
#             sentence_lower = sentence.lower()
#             # Check if sentence contains documentation keywords
#             if any(keyword in sentence_lower for keyword in [
#                 'document', 'allegat', 'presentare', 'necessari', 'richiest',
#                 'moduli', 'modello', 'certificat', 'dichiarazion', 'curriculum',
#                 'visura', 'DURC', 'business', 'piano', 'finanziar'
#             ]):
#                 doc_sentences.append(sentence)
                
#                 # Special check for sentences that likely list documentation requirements
#                 if re.search(r'(?:seguent|necessari|richiest|presentare|allegare)', sentence_lower):
#                     if 'Documentazione_Necessaria' not in enhanced_data['structured_info']:
#                         enhanced_data['structured_info']['Documentazione_Necessaria'] = []
#                     enhanced_data['structured_info']['Documentazione_Necessaria'].append(sentence)
                    
#                     # Check the next 3 sentences for potential list items
#                     sentence_idx = sentences.index(sentence)
#                     for i in range(sentence_idx + 1, min(sentence_idx + 4, len(sentences))):
#                         next_sent = sentences[i]
#                         # Check if it looks like a list item
#                         if re.match(r'^[\s]*[-•*]\s|^\d+[.)\s]', next_sent):
#                             enhanced_data['structured_info']['Documentazione_Necessaria'].append(next_sent)
        
#         # Store doc sentences if we found any
#         if doc_sentences:
#             enhanced_data['structured_info']['Documentazione_Paragrafi'] = doc_sentences
    
#     # Add the full content (if we extracted it) for further processing
#     if all_content:
#         enhanced_data['main_content'] = all_content
    
#     return enhanced_data

# def main():
#     """Main entry point for the crawler with enhanced website processing."""
#     parser = argparse.ArgumentParser(description='Grant Documentation Crawler')
#     parser.add_argument('--log-level', default='INFO', help='Logging level')
#     parser.add_argument('--max-workers', type=int, default=4, help='Maximum number of worker threads')
#     parser.add_argument('--batch-size', type=int, default=0, help='Batch size (0 for all grants)')
#     parser.add_argument('--verify-only', action='store_true', help='Only verify grant IDs exist without updating')
#     parser.add_argument('--all-grants', action='store_true', help='Process all grants regardless of status')
#     parser.add_argument('--max-retries', type=int, default=3, help='Maximum number of retries for failed processing')
#     parser.add_argument('--grant-id', help='Process only a specific grant ID')
#     parser.add_argument('--install-deps', action='store_true', help='Check and install missing dependencies')
#     parser.add_argument('--skip-db-update', action='store_true', help='Skip updating the database (for testing)')
#     parser.add_argument('--website-only', action='store_true', help='Focus only on website extraction, skip PDFs')
#     args = parser.parse_args()
    
#     # Set up logging
#     setup_logging(args.log_level)
    
#     logger.info("Starting grant documentation crawler with enhanced website processing")
    
#     try:
#         # Initialize database manager
#         db_manager = DatabaseManager()
        
#         # Process a single grant if ID is provided
#         if args.grant_id:
#             try:
#                 if db_manager.check_grant_exists(args.grant_id):
#                     # Get full grant info including name
#                     response = db_manager.supabase.table(config.BANDI_TABLE) \
#                         .select("id, link_bando, link_sito_bando, nome_bando") \
#                         .eq("id", args.grant_id) \
#                         .execute()
#                     if hasattr(response, 'data') and len(response.data) > 0:
#                         grants = response.data
#                     else:
#                         grants = [{"id": args.grant_id}]
#                     logger.info(f"Processing single grant with ID: {args.grant_id}")
#                 else:
#                     logger.error(f"Grant {args.grant_id} does not exist in the database. Exiting.")
#                     return
#             except Exception as e:
#                 logger.error(f"Error checking grant existence: {e}")
#                 logger.warning(f"Will try to process grant ID {args.grant_id} anyway")
#                 grants = [{"id": args.grant_id}]
#         # Otherwise, get grants based on the flags
#         elif args.all_grants:
#             grants = db_manager.get_all_grants()
#             if not grants:
#                 logger.info("No grants found in the database. Exiting.")
#                 return
#             logger.info(f"Found {len(grants)} total grants to process")
#         else:
#             grants = db_manager.get_active_grants()
#             if not grants:
#                 logger.info("No active grants found. Exiting.")
#                 return
#             logger.info(f"Found {len(grants)} active grants to process")
        
#         # Apply batch size if specified
#         if args.batch_size > 0 and args.batch_size < len(grants):
#             grants = grants[:args.batch_size]
#             logger.info(f"Processing batch of {len(grants)} grants")
        
#         # Verify grants exist first if requested
#         if args.verify_only:
#             existing_grants = 0
#             for grant in tqdm(grants, desc="Verifying grants"):
#                 if db_manager.check_grant_exists(grant['id']):
#                     existing_grants += 1
            
#             logger.info(f"Verified {existing_grants}/{len(grants)} grants exist in the database")
#             return

#         # Process grants in parallel
#         processed_grants = []
#         with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_workers) as executor:
#             # Submit all grants for processing
#             future_to_grant = {executor.submit(process_grant, grant): grant for grant in grants}
            
#             # Process results as they complete
#             for future in tqdm(concurrent.futures.as_completed(future_to_grant), total=len(grants), desc="Processing grants"):
#                 grant = future_to_grant[future]
#                 try:
#                     processed_grant = future.result()
#                     processed_grants.append(processed_grant)
#                 except Exception as e:
#                     logger.error(f"Error processing grant {grant.get('id')}: {str(e)}")
#                     # Create a basic fallback message for failed grants
#                     grant_name = grant.get('nome_bando', 'Bando')
#                     grant['documentation_summary'] = f"""# Documentazione Necessaria per {grant_name}

# ## Nota Importante
# Non è stato possibile estrarre automaticamente la documentazione per questo bando a causa di errori tecnici.
# Si consiglia di consultare direttamente il bando ufficiale per i dettagli specifici.

# ## Errori Riscontrati
# Errore critico: {str(e)}

# _Ultimo aggiornamento: {datetime.now().strftime("%d/%m/%Y %H:%M")}_
# """
#                     processed_grants.append(grant)
        
#         logger.info(f"Successfully processed {len(processed_grants)} grants")
        
#         # Skip database update if requested
#         if args.skip_db_update:
#             logger.info("Skipping database update as requested")
#             for i, grant in enumerate(processed_grants):
#                 logger.info(f"Grant {i+1}: {grant.get('id')}, documentation length: {len(grant.get('documentation_summary', ''))}")
#             return
        
#         # Update the database with the new documentation
#         updated_count = 0
#         update_errors = 0
#         for grant in tqdm(processed_grants, desc="Updating database"):
#             retry_count = 0
#             success = False
            
#             while not success and retry_count < args.max_retries:
#                 try:
#                     if db_manager.update_documentation(grant['id'], grant['documentation_summary']):
#                         updated_count += 1
#                         success = True
#                         logger.info(f"Successfully updated documentation for grant {grant.get('id')}")
#                     else:
#                         retry_count += 1
#                         logger.warning(f"Update failed for grant {grant.get('id')}, retry {retry_count}/{args.max_retries}")
#                         time.sleep(1)  # Short delay before retry
#                 except Exception as e:
#                     retry_count += 1
#                     logger.error(f"Error updating grant {grant.get('id')}: {str(e)}, retry {retry_count}/{args.max_retries}")
#                     time.sleep(1)  # Short delay before retry
            
#             if not success:
#                 update_errors += 1
        
#         logger.info(f"Updated documentation for {updated_count} grants in the database")
#         if update_errors > 0:
#             logger.warning(f"Failed to update {update_errors} grants after {args.max_retries} retries")
        
#     except Exception as e:
#         logger.error(f"Unexpected error: {str(e)}", exc_info=True)
#     finally:
#         logger.info("Grant documentation crawler finished")

# if __name__ == "__main__":
#     main()
# ----------------------------------------------------------------------------------------
# """
# Main entry point for the grant documentation crawler.
# Orchestrates the entire process of finding specific documentation requirements in grants.
# Enhanced with robust error handling for deployment.
# """
# import logging
# import time
# import argparse
# import os
# import sys
# from typing import Dict, List, Any, Optional
# import concurrent.futures
# from tqdm import tqdm
# from datetime import datetime
# import traceback

# import config
# from db_manager import DatabaseManager
# from web_scraper import WebScraper
# from pdf_processor import PDFProcessor
# from documentation_analyzer import DocumentationAnalyzer
# from utils import setup_logging, is_valid_url

# logger = logging.getLogger(__name__)

# def check_dependencies():
#     """
#     Check if required dependencies are available and install if possible.
#     """
#     missing_deps = []
    
#     # Check for BeautifulSoup
#     try:
#         import bs4
#         logger.info(f"BeautifulSoup version: {bs4.__version__}")
#     except ImportError:
#         missing_deps.append("beautifulsoup4")
    
#     # Check for lxml
#     try:
#         import lxml
#         logger.info(f"lxml version: {lxml.__version__}")
#     except ImportError:
#         missing_deps.append("lxml")
    
#     # Check for PDF processing library
#     try:
#         import pdfminer
#         logger.info(f"pdfminer version: {pdfminer.__version__}")
#     except ImportError:
#         try:
#             import PyPDF2
#             logger.info(f"PyPDF2 version: {PyPDF2.__version__}")
#         except ImportError:
#             missing_deps.append("pdfminer.six")
    
#     # Check for other critical dependencies
#     try:
#         import requests
#         logger.info(f"requests version: {requests.__version__}")
#     except ImportError:
#         missing_deps.append("requests")
    
#     try:
#         import nltk
#         logger.info(f"nltk version: {nltk.__version__}")
#     except ImportError:
#         missing_deps.append("nltk")
    
#     # Try to install missing dependencies
#     if missing_deps:
#         logger.warning(f"Missing dependencies: {', '.join(missing_deps)}")
#         try:
#             import pip
#             for dep in missing_deps:
#                 logger.info(f"Attempting to install {dep}...")
#                 pip.main(['install', dep])
#             logger.info("Dependency installation attempted, please restart the crawler")
#             return False
#         except Exception as e:
#             logger.error(f"Failed to install dependencies: {e}")
#             logger.error("Please install manually: pip install " + " ".join(missing_deps))
#             return False
    
#     return True

# def process_grant(grant: Dict[str, Any]) -> Dict[str, Any]:
#     """
#     Processes a single grant to find specific documentation requirements.
#     Enhanced with additional error handling and data extraction.
    
#     Args:
#         grant (Dict[str, Any]): The grant details from the database.
        
#     Returns:
#         Dict[str, Any]: The grant with updated documentation.
#     """
#     grant_id = grant.get('id')
#     link_bando = grant.get('link_bando')
#     link_sito_bando = grant.get('link_sito_bando')
#     nome_bando = grant.get('nome_bando', '')  # Get the grant name if available
    
#     logger.info(f"Processing grant {grant_id}: {nome_bando}")
    
#     # Initialize components with enhanced capabilities
#     web_scraper = WebScraper()
#     pdf_processor = PDFProcessor()
#     doc_analyzer = DocumentationAnalyzer()
    
#     web_data = []
#     pdf_data = []
#     error_messages = []
    
#     # Process main grant webpage
#     if link_bando and is_valid_url(link_bando):
#         logger.info(f"Processing main grant URL: {link_bando}")
#         html_content = web_scraper.get_page_content(link_bando)
        
#         if html_content:
#             # Extract comprehensive information from the webpage
#             try:
#                 web_info = web_scraper.extract_grant_information(html_content, link_bando)
#                 if web_info:
#                     web_data.append(web_info)
#                     logger.info(f"Successfully extracted information from {link_bando}")
#             except Exception as e:
#                 error_msg = f"Error extracting information from {link_bando}: {str(e)}"
#                 logger.error(error_msg)
#                 error_messages.append(error_msg)
            
#             # Extract PDF links
#             try:
#                 logger.info(f"Extracting PDF links from {link_bando}")
#                 pdf_links = web_scraper.extract_pdf_links(html_content, link_bando)
                
#                 # Process priority PDFs first
#                 priority_pdfs_processed = 0
#                 for pdf_info in pdf_links:
#                     if pdf_info.get('priority', False) or pdf_info.get('is_doc_related', False):
#                         try:
#                             logger.info(f"Processing priority PDF: {pdf_info.get('url')}")
#                             pdf_result = pdf_processor.process_pdf(pdf_info)
#                             if pdf_result and not pdf_result.get('error'):
#                                 pdf_data.append(pdf_result)
#                                 priority_pdfs_processed += 1
#                                 logger.info(f"Successfully processed priority PDF: {pdf_info.get('url')}")
                                
#                                 # Limit to a reasonable number
#                                 if priority_pdfs_processed >= 8:  # Increased from 5 to 8
#                                     break
#                         except Exception as e:
#                             logger.error(f"Error processing priority PDF {pdf_info.get('url')}: {str(e)}")
#                             # Still add some basic info about the failed PDF
#                             pdf_data.append({
#                                 'source': pdf_info.get('url'),
#                                 'context': pdf_info.get('context', ''),
#                                 'error': str(e),
#                                 'Documentazione': [f"Errore nell'elaborazione del PDF: {str(e)}"]
#                             })
                
#                 # Process non-priority PDFs if needed
#                 if priority_pdfs_processed < 3:  # Increased requirement from 2 to 3
#                     non_priority_pdfs = 0
#                     for pdf_info in pdf_links:
#                         if not pdf_info.get('priority', False) and not pdf_info.get('is_doc_related', False):
#                             try:
#                                 logger.info(f"Processing non-priority PDF: {pdf_info.get('url')}")
#                                 pdf_result = pdf_processor.process_pdf(pdf_info)
#                                 if pdf_result:
#                                     # Even if there's an error, still add the PDF info
#                                     pdf_data.append(pdf_result)
#                                     if not pdf_result.get('error'):
#                                         non_priority_pdfs += 1
#                                         logger.info(f"Successfully processed non-priority PDF: {pdf_info.get('url')}")
                                    
#                                     # Limit to a reasonable number
#                                     if non_priority_pdfs >= 3:
#                                         break
#                             except Exception as e:
#                                 logger.error(f"Error processing non-priority PDF {pdf_info.get('url')}: {str(e)}")
#             except Exception as e:
#                 error_msg = f"Error extracting PDF links from {link_bando}: {str(e)}"
#                 logger.error(error_msg)
#                 error_messages.append(error_msg)
#         else:
#             error_msg = f"Could not retrieve content from {link_bando}"
#             logger.warning(error_msg)
#             error_messages.append(error_msg)
    
#     # Process supplementary site if different
#     if link_sito_bando and is_valid_url(link_sito_bando) and link_sito_bando != link_bando:
#         logger.info(f"Processing supplementary grant URL: {link_sito_bando}")
#         html_content = web_scraper.get_page_content(link_sito_bando)
        
#         if html_content:
#             # Extract comprehensive information from the webpage
#             try:
#                 web_info = web_scraper.extract_grant_information(html_content, link_sito_bando)
#                 if web_info:
#                     web_data.append(web_info)
#                     logger.info(f"Successfully extracted information from {link_sito_bando}")
#             except Exception as e:
#                 error_msg = f"Error extracting information from {link_sito_bando}: {str(e)}"
#                 logger.error(error_msg)
#                 error_messages.append(error_msg)
            
#             # Extract PDF links
#             try:
#                 if len(pdf_data) < 10:  # Increased from 5 to 10 to get more PDFs
#                     logger.info(f"Extracting PDF links from {link_sito_bando}")
#                     pdf_links = web_scraper.extract_pdf_links(html_content, link_sito_bando)
                    
#                     # Filter out PDFs we've already processed
#                     existing_urls = {pdf.get('source', '') for pdf in pdf_data}
#                     new_pdf_links = [pdf for pdf in pdf_links if pdf.get('url') not in existing_urls]
                    
#                     # Process priority PDFs first
#                     priority_pdfs_processed = 0
#                     for pdf_info in new_pdf_links:
#                         if pdf_info.get('priority', False) or pdf_info.get('is_doc_related', False):
#                             try:
#                                 logger.info(f"Processing priority PDF from supplementary site: {pdf_info.get('url')}")
#                                 pdf_result = pdf_processor.process_pdf(pdf_info)
#                                 if pdf_result:
#                                     pdf_data.append(pdf_result)
#                                     if not pdf_result.get('error'):
#                                         priority_pdfs_processed += 1
#                                         logger.info(f"Successfully processed priority PDF: {pdf_info.get('url')}")
                                    
#                                     # Limit to a reasonable number
#                                     if priority_pdfs_processed >= 5:  # Increased from 3 to 5
#                                         break
#                             except Exception as e:
#                                 logger.error(f"Error processing priority PDF {pdf_info.get('url')}: {str(e)}")
                    
#                     # Process non-priority PDFs if needed
#                     if len(pdf_data) < 5:  # Increased from 3 to 5
#                         non_priority_pdfs = 0
#                         for pdf_info in new_pdf_links:
#                             if not pdf_info.get('priority', False) and not pdf_info.get('is_doc_related', False):
#                                 try:
#                                     logger.info(f"Processing non-priority PDF from supplementary site: {pdf_info.get('url')}")
#                                     pdf_result = pdf_processor.process_pdf(pdf_info)
#                                     if pdf_result:
#                                         pdf_data.append(pdf_result)
#                                         if not pdf_result.get('error'):
#                                             non_priority_pdfs += 1
#                                             logger.info(f"Successfully processed non-priority PDF: {pdf_info.get('url')}")
                                        
#                                         # Limit to a reasonable number
#                                         if non_priority_pdfs >= 3 or len(pdf_data) >= 10:
#                                             break
#                                 except Exception as e:
#                                     logger.error(f"Error processing non-priority PDF {pdf_info.get('url')}: {str(e)}")
#             except Exception as e:
#                 error_msg = f"Error extracting PDF links from {link_sito_bando}: {str(e)}"
#                 logger.error(error_msg)
#                 error_messages.append(error_msg)
#         else:
#             error_msg = f"Could not retrieve content from {link_sito_bando}"
#             logger.warning(error_msg)
#             error_messages.append(error_msg)
    
#     # Clean up resources
#     web_scraper.close()
#     pdf_processor.close()
    
#     # Even if nothing was found, still provide some basic documentation
#     if not web_data and not pdf_data:
#         basic_doc = f"""# Documentazione Necessaria per {nome_bando or 'il Bando'}

# ## Avviso Importante
# Non è stato possibile recuperare informazioni specifiche sulla documentazione richiesta per questo bando.
# Si consiglia di consultare direttamente i link ufficiali per ottenere i dettagli completi:

# - Link principale: {link_bando or 'Non disponibile'}
# - Link supplementare: {link_sito_bando or 'Non disponibile'}

# ## Documentazione Standard
# Generalmente, i bandi di questo tipo potrebbero richiedere:

# - Scheda progettuale o business plan
# - Piano finanziario delle entrate e delle spese
# - Documentazione amministrativa (visura camerale, DURC, etc.)
# - Informazioni sulla compagine sociale
# - Dichiarazioni sostitutive

# _Ultimo aggiornamento: {datetime.now().strftime("%d/%m/%Y %H:%M")}_
# """
#         grant['documentation_summary'] = basic_doc
#         return grant
    
#     # Merge and analyze all data
#     try:
#         logger.info(f"Merging and analyzing data for grant {grant_id}")
#         merged_data = doc_analyzer.merge_grant_data(web_data, pdf_data)
        
#         # Add grant name if available
#         if nome_bando:
#             merged_data['grant_name'] = nome_bando
#             if not merged_data.get('title'):
#                 merged_data['title'] = nome_bando
        
#         # Add error messages to the merged data
#         if error_messages:
#             if 'errors' not in merged_data:
#                 merged_data['errors'] = []
#             merged_data['errors'].extend(error_messages)
        
#         # Generate comprehensive list of found documentation items
#         documentation_list = doc_analyzer.generate_summary(merged_data)
        
#         # Log some stats about what we found
#         logger.info(f"Found documentation items: {len(merged_data.get('documentation', []))} general items")
#         extracted_docs = doc_analyzer.extract_target_documentation(merged_data)
#         logger.info(f"Found {len(extracted_docs)} specific documentation types")
        
#         # Update the grant with the new documentation
#         grant['documentation_summary'] = documentation_list
        
#         logger.info(f"Completed processing for grant {grant_id}: {len(web_data)} webpage sources, {len(pdf_data)} PDF sources")
#     except Exception as e:
#         logger.error(f"Error analyzing grant {grant_id}: {str(e)}")
#         # Provide a basic documentation message in case of error
#         error_stack = traceback.format_exc()
#         logger.error(f"Stack trace: {error_stack}")
        
#         basic_message = f"""# Documentazione Necessaria per {nome_bando or 'il Bando'}

# ## Nota Importante
# Non è stato possibile estrarre automaticamente la documentazione specifica per questo bando. 
# Si consiglia di consultare direttamente il bando ufficiale per i dettagli specifici.

# ### Links
# - Link principale: {link_bando or 'Non disponibile'}
# - Link supplementare: {link_sito_bando or 'Non disponibile'}

# ## Documentazione Standard
# Generalmente, per bandi di questa tipologia, è necessario presentare:

# - Documentazione amministrativa dell'impresa (es. visura camerale, DURC, etc.)
# - Documentazione tecnica del progetto
# - Documentazione economico-finanziaria
# - Documentazione relativa agli aspetti di sostenibilità

# ## Errori riscontrati
# {'; '.join(error_messages) if error_messages else 'Errore durante l\'analisi dei dati.'}

# _Ultimo aggiornamento: {datetime.now().strftime("%d/%m/%Y %H:%M")}_
# """
#         grant['documentation_summary'] = basic_message
    
#     return grant

# def main():
#     """Main entry point for the crawler."""
#     parser = argparse.ArgumentParser(description='Grant Documentation Crawler')
#     parser.add_argument('--log-level', default='INFO', help='Logging level')
#     parser.add_argument('--max-workers', type=int, default=4, help='Maximum number of worker threads')
#     parser.add_argument('--batch-size', type=int, default=0, help='Batch size (0 for all grants)')
#     parser.add_argument('--verify-only', action='store_true', help='Only verify grant IDs exist without updating')
#     parser.add_argument('--all-grants', action='store_true', help='Process all grants regardless of status')
#     parser.add_argument('--max-retries', type=int, default=3, help='Maximum number of retries for failed processing')
#     parser.add_argument('--grant-id', help='Process only a specific grant ID')
#     parser.add_argument('--install-deps', action='store_true', help='Check and install missing dependencies')
#     parser.add_argument('--skip-db-update', action='store_true', help='Skip updating the database (for testing)')
#     args = parser.parse_args()
    
#     # Set up logging
#     setup_logging(args.log_level)
    
#     logger.info("Starting grant documentation crawler")
    
#     # Check dependencies if requested
#     if args.install_deps:
#         if not check_dependencies():
#             logger.error("Missing dependencies, please install them and try again")
#             return
    
#     try:
#         # Initialize database manager
#         db_manager = DatabaseManager()
        
#         # Process a single grant if ID is provided
#         if args.grant_id:
#             try:
#                 if db_manager.check_grant_exists(args.grant_id):
#                     # Get full grant info including name
#                     response = db_manager.supabase.table(config.BANDI_TABLE) \
#                         .select("id, link_bando, link_sito_bando, nome_bando") \
#                         .eq("id", args.grant_id) \
#                         .execute()
#                     if hasattr(response, 'data') and len(response.data) > 0:
#                         grants = response.data
#                     else:
#                         grants = [{"id": args.grant_id}]
#                     logger.info(f"Processing single grant with ID: {args.grant_id}")
#                 else:
#                     logger.error(f"Grant {args.grant_id} does not exist in the database. Exiting.")
#                     return
#             except Exception as e:
#                 logger.error(f"Error checking grant existence: {e}")
#                 logger.warning(f"Will try to process grant ID {args.grant_id} anyway")
#                 grants = [{"id": args.grant_id}]
#         # Otherwise, get grants based on the flags
#         elif args.all_grants:
#             grants = db_manager.get_all_grants()
#             if not grants:
#                 logger.info("No grants found in the database. Exiting.")
#                 return
#             logger.info(f"Found {len(grants)} total grants to process")
#         else:
#             grants = db_manager.get_active_grants()
#             if not grants:
#                 logger.info("No active grants found. Exiting.")
#                 return
#             logger.info(f"Found {len(grants)} active grants to process")
        
#         # Apply batch size if specified
#         if args.batch_size > 0 and args.batch_size < len(grants):
#             grants = grants[:args.batch_size]
#             logger.info(f"Processing batch of {len(grants)} grants")
        
#         # Verify grants exist first if requested
#         if args.verify_only:
#             existing_grants = 0
#             for grant in tqdm(grants, desc="Verifying grants"):
#                 if db_manager.check_grant_exists(grant['id']):
#                     existing_grants += 1
            
#             logger.info(f"Verified {existing_grants}/{len(grants)} grants exist in the database")
#             return

#         # Process grants in parallel
#         processed_grants = []
#         with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_workers) as executor:
#             # Submit all grants for processing
#             future_to_grant = {executor.submit(process_grant, grant): grant for grant in grants}
            
#             # Process results as they complete
#             for future in tqdm(concurrent.futures.as_completed(future_to_grant), total=len(grants), desc="Processing grants"):
#                 grant = future_to_grant[future]
#                 try:
#                     processed_grant = future.result()
#                     processed_grants.append(processed_grant)
#                 except Exception as e:
#                     logger.error(f"Error processing grant {grant.get('id')}: {str(e)}")
#                     # Create a basic fallback message for failed grants
#                     grant_name = grant.get('nome_bando', 'Bando')
#                     grant['documentation_summary'] = f"""# Documentazione Necessaria per {grant_name}

# ## Nota Importante
# Non è stato possibile estrarre automaticamente la documentazione per questo bando a causa di errori tecnici.
# Si consiglia di consultare direttamente il bando ufficiale per i dettagli specifici.

# ## Errori Riscontrati
# Errore critico: {str(e)}

# _Ultimo aggiornamento: {datetime.now().strftime("%d/%m/%Y %H:%M")}_
# """
#                     processed_grants.append(grant)
        
#         logger.info(f"Successfully processed {len(processed_grants)} grants")
        
#         # Skip database update if requested
#         if args.skip_db_update:
#             logger.info("Skipping database update as requested")
#             for i, grant in enumerate(processed_grants):
#                 logger.info(f"Grant {i+1}: {grant.get('id')}, documentation length: {len(grant.get('documentation_summary', ''))}")
#             return
        
#         # Update the database with the new documentation
#         updated_count = 0
#         update_errors = 0
#         for grant in tqdm(processed_grants, desc="Updating database"):
#             retry_count = 0
#             success = False
            
#             while not success and retry_count < args.max_retries:
#                 try:
#                     if db_manager.update_documentation(grant['id'], grant['documentation_summary']):
#                         updated_count += 1
#                         success = True
#                         logger.info(f"Successfully updated documentation for grant {grant.get('id')}")
#                     else:
#                         retry_count += 1
#                         logger.warning(f"Update failed for grant {grant.get('id')}, retry {retry_count}/{args.max_retries}")
#                         time.sleep(1)  # Short delay before retry
#                 except Exception as e:
#                     retry_count += 1
#                     logger.error(f"Error updating grant {grant.get('id')}: {str(e)}, retry {retry_count}/{args.max_retries}")
#                     time.sleep(1)  # Short delay before retry
            
#             if not success:
#                 update_errors += 1
        
#         logger.info(f"Updated documentation for {updated_count} grants in the database")
#         if update_errors > 0:
#             logger.warning(f"Failed to update {update_errors} grants after {args.max_retries} retries")
        
#     except Exception as e:
#         logger.error(f"Unexpected error: {str(e)}", exc_info=True)
#     finally:
#         logger.info("Grant documentation crawler finished")

# if __name__ == "__main__":
#     main()