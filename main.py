"""
Main entry point for the grant documentation crawler.
Orchestrates the entire process of updating grant information in Supabase.
Enhanced to search for specific documentation requirements and update the database with structured results.
"""
import logging
import time
import argparse
import os
from typing import Dict, List, Any
import concurrent.futures
from tqdm import tqdm
from datetime import datetime

import config
from db_manager import DatabaseManager
from web_scraper import WebScraper
from pdf_processor import PDFProcessor
from documentation_analyzer import DocumentationAnalyzer
from utils import setup_logging, is_valid_url

logger = logging.getLogger(__name__)

def process_grant(grant: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processes a single grant to extract and update its documentation.
    Thoroughly analyzes all available information from websites and PDFs.
    Searches for specific documentation requirements from the predefined list.
    
    Args:
        grant (Dict[str, Any]): The grant details from the database.
        
    Returns:
        Dict[str, Any]: The grant with updated documentation.
    """
    grant_id = grant.get('id')
    link_bando = grant.get('link_bando')
    link_sito_bando = grant.get('link_sito_bando')
    
    logger.info(f"Processing grant {grant_id}")
    
    # Initialize components
    web_scraper = WebScraper()
    pdf_processor = PDFProcessor()
    doc_analyzer = DocumentationAnalyzer()
    
    web_data = []
    pdf_data = []
    error_messages = []
    
    # Process main grant webpage
    if link_bando and is_valid_url(link_bando):
        html_content = web_scraper.get_page_content(link_bando)
        
        if html_content:
            # Extract comprehensive information from the webpage
            try:
                web_info = web_scraper.extract_grant_information(html_content, link_bando)
                if web_info:
                    web_data.append(web_info)
            except Exception as e:
                error_msg = f"Error extracting information from {link_bando}: {str(e)}"
                logger.error(error_msg)
                error_messages.append(error_msg)
            
            # Extract PDF links
            try:
                pdf_links = web_scraper.extract_pdf_links(html_content, link_bando)
                
                # Process priority PDFs first
                priority_pdfs_processed = 0
                for pdf_info in pdf_links:
                    if pdf_info.get('priority', False) or pdf_info.get('is_doc_related', False):
                        try:
                            pdf_result = pdf_processor.process_pdf(pdf_info)
                            if pdf_result and not pdf_result.get('error'):
                                pdf_data.append(pdf_result)
                                priority_pdfs_processed += 1
                                
                                # Limit to a reasonable number
                                if priority_pdfs_processed >= 5:
                                    break
                        except Exception as e:
                            logger.error(f"Error processing priority PDF {pdf_info.get('url')}: {str(e)}")
                
                # Process non-priority PDFs if needed
                if priority_pdfs_processed < 2:
                    non_priority_pdfs = 0
                    for pdf_info in pdf_links:
                        if not pdf_info.get('priority', False) and not pdf_info.get('is_doc_related', False):
                            try:
                                pdf_result = pdf_processor.process_pdf(pdf_info)
                                if pdf_result and not pdf_result.get('error'):
                                    pdf_data.append(pdf_result)
                                    non_priority_pdfs += 1
                                    
                                    # Limit to a reasonable number
                                    if non_priority_pdfs >= 3:
                                        break
                            except Exception as e:
                                logger.error(f"Error processing non-priority PDF {pdf_info.get('url')}: {str(e)}")
            except Exception as e:
                error_msg = f"Error extracting PDF links from {link_bando}: {str(e)}"
                logger.error(error_msg)
                error_messages.append(error_msg)
        else:
            error_msg = f"Could not retrieve content from {link_bando}"
            logger.warning(error_msg)
            error_messages.append(error_msg)
    
    # Process supplementary site if different
    if link_sito_bando and is_valid_url(link_sito_bando) and link_sito_bando != link_bando:
        html_content = web_scraper.get_page_content(link_sito_bando)
        
        if html_content:
            # Extract comprehensive information from the webpage
            try:
                web_info = web_scraper.extract_grant_information(html_content, link_sito_bando)
                if web_info:
                    web_data.append(web_info)
            except Exception as e:
                error_msg = f"Error extracting information from {link_sito_bando}: {str(e)}"
                logger.error(error_msg)
                error_messages.append(error_msg)
            
            # Extract PDF links
            try:
                if len(pdf_data) < 5:  # Only if we need more PDFs
                    pdf_links = web_scraper.extract_pdf_links(html_content, link_sito_bando)
                    
                    # Filter out PDFs we've already processed
                    existing_urls = {pdf.get('source', '') for pdf in pdf_data}
                    new_pdf_links = [pdf for pdf in pdf_links if pdf.get('url') not in existing_urls]
                    
                    # Process priority PDFs first
                    priority_pdfs_processed = 0
                    for pdf_info in new_pdf_links:
                        if pdf_info.get('priority', False) or pdf_info.get('is_doc_related', False):
                            try:
                                pdf_result = pdf_processor.process_pdf(pdf_info)
                                if pdf_result and not pdf_result.get('error'):
                                    pdf_data.append(pdf_result)
                                    priority_pdfs_processed += 1
                                    
                                    # Limit to a reasonable number
                                    if priority_pdfs_processed >= 3:
                                        break
                            except Exception as e:
                                logger.error(f"Error processing priority PDF {pdf_info.get('url')}: {str(e)}")
                    
                    # Process non-priority PDFs if needed
                    if len(pdf_data) < 3:
                        non_priority_pdfs = 0
                        for pdf_info in new_pdf_links:
                            if not pdf_info.get('priority', False) and not pdf_info.get('is_doc_related', False):
                                try:
                                    pdf_result = pdf_processor.process_pdf(pdf_info)
                                    if pdf_result and not pdf_result.get('error'):
                                        pdf_data.append(pdf_result)
                                        non_priority_pdfs += 1
                                        
                                        # Limit to a reasonable number
                                        if non_priority_pdfs >= 2 or len(pdf_data) >= 5:
                                            break
                                except Exception as e:
                                    logger.error(f"Error processing non-priority PDF {pdf_info.get('url')}: {str(e)}")
            except Exception as e:
                error_msg = f"Error extracting PDF links from {link_sito_bando}: {str(e)}"
                logger.error(error_msg)
                error_messages.append(error_msg)
        else:
            error_msg = f"Could not retrieve content from {link_sito_bando}"
            logger.warning(error_msg)
            error_messages.append(error_msg)
    
    # Clean up resources
    web_scraper.close()
    pdf_processor.close()
    
    # Merge and analyze all data
    try:
        merged_data = doc_analyzer.merge_grant_data(web_data, pdf_data)
        
        # Add error messages to the merged data
        if error_messages:
            if 'errors' not in merged_data:
                merged_data['errors'] = []
            merged_data['errors'].extend(error_messages)
        
        # Generate comprehensive summary with specific documentation requirements checklist
        documentation_summary = doc_analyzer.generate_summary(merged_data)
        
        # Update the grant with the new documentation
        grant['documentation_summary'] = documentation_summary
        
        logger.info(f"Completed processing for grant {grant_id}: {len(web_data)} webpage sources, {len(pdf_data)} PDF sources")
    except Exception as e:
        logger.error(f"Error analyzing grant {grant_id}: {str(e)}")
        # Provide a basic documentation summary even in case of error
        basic_summary = f"""# Documentazione Necessaria

## Nota Importante
Non è stato possibile estrarre automaticamente la documentazione completa per questo bando. 
Si consiglia di consultare direttamente il bando ufficiale per i dettagli specifici.

## Errori Riscontrati
{'; '.join(error_messages)}

## Documentazione Standard
- Documento d'identità in corso di validità del rappresentante legale
- Documentazione attestante i poteri di firma
- Documentazione finanziaria dell'impresa (es. bilanci, dichiarazioni fiscali)
- Descrizione dettagliata del progetto proposto
- Piano finanziario del progetto
- Dichiarazioni sostitutive richieste dal bando

_Ultimo aggiornamento: {datetime.now().strftime("%d/%m/%Y %H:%M")}_
"""
        grant['documentation_summary'] = basic_summary
    
    return grant

def main():
    """Main entry point for the crawler."""
    parser = argparse.ArgumentParser(description='Grant Documentation Crawler')
    parser.add_argument('--log-level', default='INFO', help='Logging level')
    parser.add_argument('--max-workers', type=int, default=4, help='Maximum number of worker threads')
    parser.add_argument('--batch-size', type=int, default=0, help='Batch size (0 for all grants)')
    parser.add_argument('--verify-only', action='store_true', help='Only verify grant IDs exist without updating')
    parser.add_argument('--all-grants', action='store_true', help='Process all grants regardless of status')
    parser.add_argument('--max-retries', type=int, default=3, help='Maximum number of retries for failed processing')
    parser.add_argument('--grant-id', help='Process only a specific grant ID')
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    
    logger.info("Starting grant documentation crawler")
    
    try:
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Process a single grant if ID is provided
        if args.grant_id:
            if db_manager.check_grant_exists(args.grant_id):
                grants = [{"id": args.grant_id}]
                logger.info(f"Processing single grant with ID: {args.grant_id}")
            else:
                logger.error(f"Grant {args.grant_id} does not exist in the database. Exiting.")
                return
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
                    # Create a basic fallback summary for failed grants
                    grant['documentation_summary'] = f"""# Documentazione Necessaria

## Nota
Non è stato possibile estrarre automaticamente la documentazione per questo bando a causa di errori tecnici.
Si consiglia di consultare direttamente il bando ufficiale per i dettagli specifici.

## Documentazione Standard
- Documento d'identità in corso di validità del rappresentante legale
- Documentazione attestante i poteri di firma
- Documentazione finanziaria dell'impresa
- Descrizione dettagliata del progetto proposto
- Piano finanziario del progetto
- Dichiarazioni sostitutive richieste dal bando

_Ultimo aggiornamento: {datetime.now().strftime("%d/%m/%Y %H:%M")}_
"""
                    processed_grants.append(grant)
        
        logger.info(f"Successfully processed {len(processed_grants)} grants")
        
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
        logger.info("Grant documentation crawler finished")

if __name__ == "__main__":
    main()