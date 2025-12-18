#!/usr/bin/env python3
"""
Snowflake Cortex Contract Extraction with Structured Outputs

This script uses Snowflake Cortex AI to extract structured contract terms from PDF documents
using AI_COMPLETE with structured outputs based on a JSON schema.

It assumes the response_format JSON file and system_prompt.md file located locally.
If in Snowflake notebook, it should be wihtin the working directory of the notebook.

Requirements:
    pip install snowflake-connector-python snowflake-ml-python

"""

# import argparse
import json
import logging
from typing import Dict, Any

from snowflake.snowpark import Session
from snowflake.cortex import complete, CompleteOptions


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ContractExtractor:
    """Extract structured contract terms using Snowflake Cortex AI."""
    
    def __init__(
        self,
        session: Session,
        response_format_path: str = "response_format.json",
        system_prompt_path: str = "system_prompt.md"
    ):
        """
        Initialize the contract extractor.
        
        Args:
            session: Snowflake Session object
            response_format_path: Path to JSON file containing response format schema
            system_prompt_path: Path to file containing system prompt
        """
        self.session = session
        self.response_format = self._load_response_format(response_format_path)
        self.system_prompt = self._load_system_prompt(system_prompt_path)
        
    def _load_response_format(self, path: str) -> Dict[str, Any]:
        """Load response format schema from JSON file."""
        try:
            with open(path, 'r') as f:
                response_format = json.load(f)
            logger.info(f"Loaded response format from {path}")
            return response_format
        except FileNotFoundError:
            logger.error(f"Response format file not found: {path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in response format file: {e}")
            raise
    
    def _load_system_prompt(self, path: str) -> str:
        """Load system prompt from file."""
        try:
            with open(path, 'r') as f:
                prompt = f.read().strip()
            logger.info(f"Loaded system prompt from {path}")
            return prompt
        except FileNotFoundError:
            logger.error(f"System prompt file not found: {path}")
            raise
    
    def _upload_document_to_stage(self, stage_path: str, filename: str) -> str:
        """Upload a document to a Snowflake stage."""
        try:
            self.session.file.put(filename, stage_path, overwrite=True, auto_compress=False)
            logger.info(f"Uploaded document to {stage_path}/{filename}")
            return f"{stage_path}/{filename}"
        except Exception as e:
            logger.error(f"Error uploading document to stage: {e}")
            raise
    
    def parse_document(
        self,
        stage_path: str,
        filename: str,
        mode: str = "LAYOUT"
    ) -> str:
        """
        Parse a PDF document using AI_PARSE_DOCUMENT.
        
        Args:
            stage_path: Snowflake stage path (e.g., '@JSUMMER.SANDBOX.DROPBOX')
            filename: PDF filename in the stage
            mode: Parse mode ('LAYOUT' or 'DOCUMENT')
            
        Returns:
            Parsed document text as string
        """
        logger.info(f"Parsing document: {stage_path}/{filename}")
        
        # Build the SQL query
        sql = f"""
        SELECT TO_VARCHAR(
            AI_PARSE_DOCUMENT(
                TO_FILE('{stage_path}', '{filename}'),
                OBJECT_CONSTRUCT('mode', '{mode}')
            )
        ) AS parsed_content
        """
        
        try:
            result = self.session.sql(sql).collect()
            if result and len(result) > 0:
                parsed_text = result[0]['PARSED_CONTENT']
                logger.info(f"Successfully parsed document ({len(parsed_text)} characters)")
                return parsed_text
            else:
                raise ValueError("No content returned from AI_PARSE_DOCUMENT")
        except Exception as e:
            logger.error(f"Error parsing document: {e}")
            raise
    
    def extract_terms(
        self,
        contract_text: str,
        model: str = "claude-4-sonnet",
        temperature: float = 0.0,
        max_tokens: int = 16000,
    ) -> Dict[str, Any]:
        """
        Extract structured contract terms using AI_COMPLETE.
        
        Args:
            contract_text: The contract text to analyze
            model: Model to use (claude-3-5-sonnet, claude-4-sonnet, mistral-large2, etc.)
            temperature: Temperature for generation (0.0 for most consistent results)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Extracted contract terms as a dictionary
        """
        logger.info(f"Extracting contract terms using model: {model}")
        
        # Build the complete prompt
        full_prompt = f"{self.system_prompt}\n\nHere is the contract:\n\n{contract_text}"
        
        # Prepare the prompt in chat format
        prompt = [
            {
                "role": "user",
                "content": full_prompt
            }
        ]
        
        # Configure options
        options = CompleteOptions(
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=1.0,
            guardrails=False,
            response_format=self.response_format
        )
        
        try:
            # Call Cortex Complete
            logger.info("Calling Cortex Complete API...")
            result = complete(
                model=model,
                prompt=prompt,
                session=self.session,
                stream=False,
                options=options
            )
            
            # Parse the result
            if isinstance(result, str):
                extracted_data = json.loads(result)
            else:
                extracted_data = result
            
            logger.info("Successfully extracted contract terms")
            
            # Log summary statistics
            if isinstance(extracted_data, dict):
                terms_count = len(extracted_data.get('terms', []))
                parties_count = len(extracted_data.get('parties', []))
                logger.info(f"Extracted {terms_count} terms and {parties_count} parties")
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error extracting contract terms: {e}")
            raise
    
    def extract_from_stage(
        self,
        stage_path: str,
        filename: str,
        model: str = "claude-4-sonnet",
        temperature: float = 0.0,
        max_tokens: int = 16000,
        parse_mode: str = "LAYOUT"
    ) -> Dict[str, Any]:
        """
        Complete workflow: parse document from stage and extract terms.
        
        Args:
            stage_path: Snowflake stage path
            filename: PDF filename
            model: Model to use
            temperature: Temperature setting
            max_tokens: Maximum tokens
            parse_mode: Document parse mode
            
        Returns:
            Extracted contract terms as a dictionary
        """
        # Step 1: Parse the document
        contract_text = self.parse_document(stage_path, filename, parse_mode)
        
        # Step 2: Extract terms
        extracted_terms = self.extract_terms(
            contract_text=contract_text,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return extracted_terms