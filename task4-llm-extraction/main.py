"""
Main Execution Script for LLM Data Extraction

Processes sample documents and generates comparison report.

Author: LLM Data Extraction
Date: 2025-11-26
"""

import json
import logging
import os
import sys
from pathlib import Path

from llm_extractor import LLMDataExtractor
from data_extractor import TraditionalExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('extraction.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def load_document(filepath: str) -> str:
    """Load document text from file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error loading document {filepath}: {e}")
        raise


def main():
    """Main execution function."""
    logger.info("=" * 80)
    logger.info("LLM Data Extraction Started")
    logger.info("=" * 80)
    
    # Sample documents directory
    documents_dir = Path('sample_documents')
    
    # Dynamically find all .txt files in sample_documents folder (including subdirectories)
    if not documents_dir.exists():
        logger.error(f"Sample documents directory not found: {documents_dir}")
        sys.exit(1)
    
    # Get all .txt files from the directory and subdirectories (recursive)
    document_files = sorted(documents_dir.rglob('*.txt'))
    
    if not document_files:
        logger.warning(f"No .txt files found in {documents_dir}")
        sys.exit(1)
    
    logger.info(f"Found {len(document_files)} document(s) to process")
    
    # Initialize extractors
    # Use mock mode by default (set USE_MOCK=false in .env to use real API)
    llm_extractor = LLMDataExtractor(use_mock=True)
    traditional_extractor = TraditionalExtractor()
    
    # Store all results
    all_results = {
        'llm_extractions': [],
        'traditional_extractions': []
    }
    
    # Process each document
    for doc_path in document_files:
        doc_name = doc_path.name
        
        if not doc_path.exists():
            logger.warning(f"Document not found: {doc_path}")
            continue
        
        logger.info(f"\nProcessing: {doc_name}")
        logger.info("-" * 80)
        
        # Load document
        document_text = load_document(doc_path)
        
        # Extract with LLM
        try:
            llm_result = llm_extractor.extract_from_document(document_text, doc_name)
            all_results['llm_extractions'].append(llm_result)
            logger.info(f"LLM extraction completed for {doc_name}")
        except Exception as e:
            logger.error(f"LLM extraction failed for {doc_name}: {e}")
        
        # Extract with traditional method
        try:
            trad_result = traditional_extractor.extract_from_document(document_text, doc_name)
            all_results['traditional_extractions'].append(trad_result)
            logger.info(f"Traditional extraction completed for {doc_name}")
        except Exception as e:
            logger.error(f"Traditional extraction failed for {doc_name}: {e}")
    
    # Save results
    output_file = 'extracted_data.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\nResults saved to: {output_file}")
    
    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("EXTRACTION SUMMARY")
    logger.info("=" * 80)
    
    llm_valid = sum(1 for r in all_results['llm_extractions'] if r['validation']['is_valid'])
    trad_valid = sum(1 for r in all_results['traditional_extractions'] if r['validation']['is_valid'])
    
    num_documents = len(all_results['llm_extractions'])
    logger.info(f"Documents processed: {num_documents}")
    logger.info(f"LLM extractions valid: {llm_valid}/{len(all_results['llm_extractions'])}")
    logger.info(f"Traditional extractions valid: {trad_valid}/{len(all_results['traditional_extractions'])}")
    
    logger.info("\n" + "=" * 80)
    logger.info("Extraction completed successfully")
    logger.info("=" * 80)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        sys.exit(1)
