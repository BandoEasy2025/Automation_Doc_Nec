# python main.py --grant-id YOUR_GRANT_ID
"""
Enhanced grant documentation crawler.
Focuses on extracting specific documentation requirements from grant websites and PDFs.
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
from pdf_processor import PDFProcessor
from documentation_analyzer import DocumentationAnalyzer
from utils import setup_logging, is_valid_url

logger = logging.getLogger(__name__)

def process_grant(grant: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processes a single grant to find specific documentation requirements.
    Extracts sentences containing specified documentation keywords from web content and PDFs.
    
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
    
    # Initialize components with enhanced capabilities
    web_scraper = WebScraper()
    pdf_processor = PDFProcessor()
    doc_analyzer = DocumentationAnalyzer()
    
    web_data = []
    pdf_data = []
    error_messages = []
    
    # Process main grant webpage
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
                    
                    # Extract PDF links from the main page
                    pdf_links = web_scraper.extract_pdf_links(html_content, link_bando)
                    
                    # Process high-priority PDFs (especially documentation-related ones)
                    priority_pdfs = [pdf for pdf in pdf_links if pdf.get('priority', False) or pdf.get('is_doc_related', False)]
                    other_pdfs = [pdf for pdf in pdf_links if not (pdf.get('priority', False) or pdf.get('is_doc_related', False))]
                    
                    # Process PDFs with higher priority first, limited to most relevant ones
                    pdfs_to_process = priority_pdfs[:5]  # Process top 5 priority PDFs
                    if len(pdfs_to_process) < 3:  # If fewer than 3 priority PDFs, add some others
                        pdfs_to_process.extend(other_pdfs[:3 - len(pdfs_to_process)])
                    
                    logger.info(f"Found {len(pdfs_to_process)} relevant PDFs to process from {link_bando}")
                    
                    # Process PDFs in parallel for better performance
                    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                        future_to_pdf = {executor.submit(pdf_processor.process_pdf, pdf): pdf for pdf in pdfs_to_process}
                        
                        for future in concurrent.futures.as_completed(future_to_pdf):
                            pdf = future_to_pdf[future]
                            try:
                                result = future.result()
                                if result and not result.get('error'):
                                    pdf_data.append(result)
                                    logger.info(f"Processed PDF: {pdf.get('url')}")
                                else:
                                    error_msg = result.get('error', 'Unknown error processing PDF')
                                    logger.warning(f"Error processing PDF {pdf.get('url')}: {error_msg}")
                                    error_messages.append(f"PDF Error: {error_msg}")
                            except Exception as e:
                                logger.error(f"Exception processing PDF {pdf.get('url')}: {str(e)}")
                                error_messages.append(f"PDF Exception: {str(e)}")
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
                    
                    # Extract PDF links from the supplementary page
                    pdf_links = web_scraper.extract_pdf_links(html_content, link_sito_bando)
                    
                    # Process high-priority PDFs (especially documentation-related ones)
                    priority_pdfs = [pdf for pdf in pdf_links if pdf.get('priority', False) or pdf.get('is_doc_related', False)]
                    other_pdfs = [pdf for pdf in pdf_links if not (pdf.get('priority', False) or pdf.get('is_doc_related', False))]
                    
                    # Process PDFs with higher priority first, limited to most relevant ones
                    pdfs_to_process = priority_pdfs[:3]  # Process top 3 priority PDFs
                    if len(pdfs_to_process) < 2:  # If fewer than 2 priority PDFs, add some others
                        pdfs_to_process.extend(other_pdfs[:2 - len(pdfs_to_process)])
                    
                    logger.info(f"Found {len(pdfs_to_process)} relevant PDFs to process from {link_sito_bando}")
                    
                    # Process PDFs in parallel for better performance
                    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                        future_to_pdf = {executor.submit(pdf_processor.process_pdf, pdf): pdf for pdf in pdfs_to_process}
                        
                        for future in concurrent.futures.as_completed(future_to_pdf):
                            pdf = future_to_pdf[future]
                            try:
                                result = future.result()
                                if result and not result.get('error'):
                                    pdf_data.append(result)
                                    logger.info(f"Processed PDF: {pdf.get('url')}")
                                else:
                                    error_msg = result.get('error', 'Unknown error processing PDF')
                                    logger.warning(f"Error processing PDF {pdf.get('url')}: {error_msg}")
                                    error_messages.append(f"PDF Error: {error_msg}")
                            except Exception as e:
                                logger.error(f"Exception processing PDF {pdf.get('url')}: {str(e)}")
                                error_messages.append(f"PDF Exception: {str(e)}")
            except Exception as e:
                error_msg = f"Error extracting information from {link_sito_bando}: {str(e)}"
                logger.error(error_msg)
                error_messages.append(error_msg)
        else:
            error_msg = f"Could not retrieve content from {link_sito_bando}"
            logger.warning(error_msg)
            error_messages.append(error_msg)
    
    # Clean up resources
    web_scraper.close()
    pdf_processor.close()
    
    # Even if nothing was found, still provide some basic documentation
    if not web_data and not pdf_data:
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
    
    # Merge and analyze web and PDF data
    try:
        logger.info(f"Merging and analyzing data for grant {grant_id}")
        merged_data = doc_analyzer.merge_grant_data(web_data, pdf_data)
        
        # Add grant name if available
        if nome_bando:
            merged_data['grant_name'] = nome_bando
            if not merged_data.get('title'):
                merged_data['title'] = nome_bando
        
        # Extract target documentation items based on specified keywords
        extracted_docs = doc_analyzer.extract_target_documentation(merged_data)
        
        # Generate comprehensive documentation in bullet-point format
        documentation_list = doc_analyzer.generate_documentation_content(extracted_docs, nome_bando)
        
        # Log stats about what we found
        logger.info(f"Found documentation items: {len(merged_data.get('documentation', []))} general items")
        logger.info(f"Found {len(extracted_docs)} specific documentation types")
        
        # Update the grant with the new documentation
        grant['documentation_summary'] = documentation_list
        
        logger.info(f"Completed processing for grant {grant_id}")
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

def main():
    """Main entry point for the grant documentation crawler."""
    parser = argparse.ArgumentParser(description='Grant Documentation Crawler')
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
    
    logger.info("Starting grant documentation crawler")
    
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
            # By default, get only active grants
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
        logger.info("Grant documentation crawler finished")

if __name__ == "__main__":
    main()