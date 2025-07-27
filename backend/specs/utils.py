"""
Utility functions for managing processing data and development tools.
"""

import os
import json
import shutil
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ProcessingDataManager:
    """Manages processing data for development and testing."""
    
    def __init__(self, base_path: str = "backend/specs"):
        self.base_path = base_path
        self.processing_outputs_path = os.path.join(base_path, "processing-outputs")
        self.test_data_path = os.path.join(base_path, "test-data")
        self.rules_path = os.path.join(base_path, "rules")
    
    def save_processing_output(
        self,
        wine_list_id: str,
        stage: str,
        data: Dict[str, Any],
        version: Optional[str] = None,
        description: Optional[str] = None
    ) -> str:
        """
        Save processing output locally for development/debugging.
        
        Args:
            wine_list_id: The wine list ID
            stage: Processing stage
            data: The data to save
            version: Optional version identifier
            description: Optional description for the output
            
        Returns:
            str: Path to the saved file
        """
        # Create directory structure
        stage_path = os.path.join(self.processing_outputs_path, stage)
        wine_list_path = os.path.join(stage_path, wine_list_id)
        os.makedirs(wine_list_path, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        version_suffix = f"_v{version}" if version else ""
        desc_suffix = f"_{description}" if description else ""
        filename = f"{stage}{version_suffix}{desc_suffix}_{timestamp}.json"
        
        file_path = os.path.join(wine_list_path, filename)
        
        # Save data
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved processing output to: {file_path}")
        return file_path
    
    def load_processing_output(
        self,
        wine_list_id: str,
        stage: str,
        version: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Load processing output from local storage.
        
        Args:
            wine_list_id: The wine list ID
            stage: Processing stage
            version: Optional version identifier
            
        Returns:
            Optional[Dict[str, Any]]: The loaded data or None if not found
        """
        stage_path = os.path.join(self.processing_outputs_path, stage, wine_list_id)
        
        if not os.path.exists(stage_path):
            return None
        
        # Find the most recent file or specific version
        files = [f for f in os.listdir(stage_path) if f.endswith('.json')]
        
        if not files:
            return None
        
        if version:
            # Look for specific version
            target_file = None
            for file in files:
                if f"_v{version}_" in file:
                    target_file = file
                    break
            if not target_file:
                return None
        else:
            # Get the most recent file
            files.sort(reverse=True)
            target_file = files[0]
        
        file_path = os.path.join(stage_path, target_file)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def list_processing_stages(self, wine_list_id: str) -> Dict[str, Any]:
        """
        List all available processing stages for a wine list.
        
        Args:
            wine_list_id: The wine list ID
            
        Returns:
            Dict[str, Any]: Dictionary with stages and their metadata
        """
        stages = {}
        
        for stage in ['extractor', 'preprocessor', 'categorizer', 'field_extractor', 'learning']:
            stage_path = os.path.join(self.processing_outputs_path, stage, wine_list_id)
            
            if os.path.exists(stage_path):
                files = [f for f in os.listdir(stage_path) if f.endswith('.json')]
                files.sort(reverse=True)
                
                stages[stage] = {
                    'files': files,
                    'count': len(files),
                    'latest': files[0] if files else None
                }
        
        return stages
    
    def cleanup_processing_data(self, wine_list_id: str, stage: Optional[str] = None) -> bool:
        """
        Clean up processing data for a wine list.
        
        Args:
            wine_list_id: The wine list ID
            stage: Optional specific stage to delete
            
        Returns:
            bool: True if cleanup was successful
        """
        try:
            if stage:
                # Delete specific stage
                stage_path = os.path.join(self.processing_outputs_path, stage, wine_list_id)
                if os.path.exists(stage_path):
                    shutil.rmtree(stage_path)
            else:
                # Delete all stages for this wine list
                for stage_name in ['extractor', 'preprocessor', 'categorizer', 'field_extractor', 'learning']:
                    stage_path = os.path.join(self.processing_outputs_path, stage_name, wine_list_id)
                    if os.path.exists(stage_path):
                        shutil.rmtree(stage_path)
            
            logger.info(f"Cleaned up processing data for wine list {wine_list_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up processing data: {str(e)}")
            return False
    
    def migrate_test_data(self, source_path: str, wine_list_id: str) -> bool:
        """
        Migrate existing test data to the new structure.
        
        Args:
            source_path: Path to the test data directory
            wine_list_id: The wine list ID to use
            
        Returns:
            bool: True if migration was successful
        """
        try:
            if not os.path.exists(source_path):
                logger.error(f"Source path does not exist: {source_path}")
                return False
            
            # Map of old filenames to new stages
            stage_mapping = {
                'extractor_output.json': 'extractor',
                'preprocessor_output.json': 'preprocessor',
                'categorizer_output.json': 'categorizer',
                'field_extractor_output.json': 'field_extractor',
                'ai_refined_entries.json': 'learning',
                'learning_results.json': 'learning'
            }
            
            migrated_files = []
            
            for filename, stage in stage_mapping.items():
                source_file = os.path.join(source_path, filename)
                
                if os.path.exists(source_file):
                    # Load the data
                    with open(source_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Save to new structure
                    self.save_processing_output(
                        wine_list_id=wine_list_id,
                        stage=stage,
                        data=data,
                        description="migrated"
                    )
                    
                    migrated_files.append(filename)
            
            logger.info(f"Migrated {len(migrated_files)} files: {migrated_files}")
            return True
            
        except Exception as e:
            logger.error(f"Error migrating test data: {str(e)}")
            return False
    
    def create_test_case(
        self,
        name: str,
        pdf_path: str,
        expected_outputs: Dict[str, Any],
        description: Optional[str] = None
    ) -> str:
        """
        Create a test case with expected outputs.
        
        Args:
            name: Name of the test case
            pdf_path: Path to the PDF file
            expected_outputs: Dictionary of expected outputs by stage
            description: Optional description
            
        Returns:
            str: Path to the created test case
        """
        test_case_path = os.path.join(self.test_data_path, "realworld", name)
        os.makedirs(test_case_path, exist_ok=True)
        
        # Copy PDF file
        pdf_filename = os.path.basename(pdf_path)
        pdf_dest = os.path.join(test_case_path, pdf_filename)
        shutil.copy2(pdf_path, pdf_dest)
        
        # Save expected outputs
        expected_outputs_file = os.path.join(test_case_path, "expected_outputs.json")
        with open(expected_outputs_file, 'w', encoding='utf-8') as f:
            json.dump(expected_outputs, f, indent=2, ensure_ascii=False)
        
        # Create metadata
        metadata = {
            "name": name,
            "description": description,
            "pdf_file": pdf_filename,
            "created_at": datetime.utcnow().isoformat(),
            "expected_stages": list(expected_outputs.keys())
        }
        
        metadata_file = os.path.join(test_case_path, "metadata.json")
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Created test case: {test_case_path}")
        return test_case_path

# Global instance for easy access
data_manager = ProcessingDataManager()

def save_dev_output(wine_list_id: str, stage: str, data: Dict[str, Any], **kwargs):
    """Convenience function to save development output."""
    return data_manager.save_processing_output(wine_list_id, stage, data, **kwargs)

def load_dev_output(wine_list_id: str, stage: str, **kwargs):
    """Convenience function to load development output."""
    return data_manager.load_processing_output(wine_list_id, stage, **kwargs)
