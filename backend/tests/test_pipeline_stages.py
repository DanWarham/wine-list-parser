#!/usr/bin/env python3
"""
Comprehensive Pipeline Stage Analysis Test

This script:
1. Authenticates with Supabase using provided credentials
2. Clears all rules for the specified restaurant
3. Uploads a test PDF file
4. Examines each stage of the parsing pipeline in detail
5. Analyzes the effectiveness of generated rules
"""

import os
import sys
import json
import time
import requests
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

# Load environment variables from .env files
try:
    from dotenv import load_dotenv
    # Load backend .env
    backend_env_path = Path(__file__).parent.parent / '.env'
    if backend_env_path.exists():
        load_dotenv(backend_env_path)
    # Load frontend .env.local
    frontend_env_path = Path(__file__).parent.parent.parent / 'frontend' / '.env.local'
    if frontend_env_path.exists():
        load_dotenv(frontend_env_path)
except ImportError:
    pass  # dotenv not available, continue without it

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pipeline_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PipelineStageAnalyzer:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api/v2"
        self.session = requests.Session()
        self.access_token = None
        self.restaurant_id = "3cce3b48-a801-475b-9552-5fb7377cb0be"
        
    def authenticate_with_supabase(self, email: str, password: str) -> bool:
        """Authenticate with Supabase and get JWT token."""
        try:
            logger.info("Authenticating with Supabase...")
            
            # Get Supabase URL and anon key from environment or use defaults
            supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "https://vwnvmjladuvnthcfkjqi.supabase.co")
            supabase_anon_key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ3bnZtamxhZHV2bnRoY2ZranFpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTAwMTYzNzQsImV4cCI6MjA2NTU5MjM3NH0.odOI2qeMYWD5zYULFeFeLip33Ftu7UyJp6-HgtLGJt0")
            
            if not supabase_url or not supabase_anon_key:
                logger.error("Missing Supabase environment variables")
                return False
            
            # Authenticate with Supabase
            auth_url = f"{supabase_url}/auth/v1/token?grant_type=password"
            headers = {
                "apikey": supabase_anon_key,
                "Content-Type": "application/json"
            }
            
            data = {
                "email": email,
                "password": password
            }
            
            response = self.session.post(auth_url, headers=headers, json=data)
            
            if response.status_code == 200:
                auth_data = response.json()
                self.access_token = auth_data.get("access_token")
                if self.access_token:
                    logger.info("Successfully authenticated with Supabase")
                    # Set the token in session headers for future requests
                    self.session.headers.update({
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json"
                    })
                    return True
                else:
                    logger.error("No access token in response")
                    return False
            else:
                logger.error(f"Authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    def clear_restaurant_rules(self) -> bool:
        """Clear all rules for the specified restaurant."""
        try:
            logger.info(f"Clearing rules for restaurant {self.restaurant_id}...")
            
            # First, check if there are existing rules
            rules_url = f"{self.api_base}/restaurants/{self.restaurant_id}/ruleset"
            response = self.session.get(rules_url)
            
            if response.status_code == 200:
                existing_rules = response.json()
                logger.info(f"Found existing rules: {json.dumps(existing_rules, indent=2)}")
                
                # Clear rules by setting empty ruleset
                clear_data = {"rules_json": {}}
                response = self.session.put(rules_url, json=clear_data)
                
                if response.status_code == 200:
                    logger.info("Successfully cleared restaurant rules")
                    return True
                else:
                    logger.error(f"Failed to clear rules: {response.status_code} - {response.text}")
                    return False
            else:
                logger.info("No existing rules found")
                return True
                
        except Exception as e:
            logger.error(f"Error clearing rules: {e}")
            return False
    
    def upload_test_file(self, file_path: str) -> Optional[str]:
        """Upload the test PDF file and return the file ID."""
        try:
            from requests_toolbelt.multipart.encoder import MultipartEncoder
            logger.info(f"Uploading test file: {file_path}")
            
            if not os.path.exists(file_path):
                logger.error(f"Test file not found: {file_path}")
                return None
            
            upload_url = f"{self.api_base}/wine-lists/upload"
            
            with open(file_path, 'rb') as f:
                m = MultipartEncoder(
                    fields={
                        'file': (os.path.basename(file_path), f, 'application/pdf'),
                        'restaurant_id': str(self.restaurant_id)
                    }
                )
                headers = self.session.headers.copy()
                headers['Content-Type'] = m.content_type
                response = self.session.post(upload_url, data=m, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                file_id = result.get('id')
                logger.info(f"Successfully uploaded file. File ID: {file_id}")
                return file_id
            else:
                logger.error(f"Upload failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return None
    
    def wait_for_processing(self, file_id: str, timeout: int = 300) -> bool:
        """Wait for file processing to complete."""
        try:
            logger.info(f"Waiting for processing to complete (timeout: {timeout}s)...")
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                # Check file status
                status_url = f"{self.api_base}/wine-lists/{file_id}"
                response = self.session.get(status_url)
                
                if response.status_code == 200:
                    file_data = response.json()
                    status = file_data.get('status')
                    logger.info(f"File status: {status}")
                    
                    if status in ['completed', 'failed']:
                        return status == 'completed'
                
                time.sleep(5)  # Wait 5 seconds before checking again
            
            logger.error("Processing timeout reached")
            return False
            
        except Exception as e:
            logger.error(f"Error waiting for processing: {e}")
            return False
    
    def analyze_processing_stages(self, file_id: str) -> Dict[str, Any]:
        """Analyze each stage of the processing pipeline."""
        try:
            logger.info("Analyzing processing stages...")
            
            # Get processing data for each stage
            stages = ['extractor', 'preprocessor', 'categorizer', 'field_extractor', 'learning']
            stage_data = {}
            
            for stage in stages:
                logger.info(f"Analyzing {stage} stage...")
                stage_url = f"{self.api_base}/wine-lists/{file_id}/processing-data?stage={stage}"
                response = self.session.get(stage_url)
                
                if response.status_code == 200:
                    stage_data[stage] = response.json()
                    logger.info(f"Retrieved {stage} data")
                else:
                    logger.warning(f"Could not retrieve {stage} data: {response.status_code}")
                    stage_data[stage] = None
            
            return stage_data
            
        except Exception as e:
            logger.error(f"Error analyzing processing stages: {e}")
            return {}
    
    def analyze_wine_entries(self, file_id: str) -> Dict[str, Any]:
        """Analyze the extracted wine entries."""
        try:
            logger.info("Analyzing wine entries...")
            
            # Get wine entries
            entries_url = f"{self.api_base}/wine-entries/{file_id}"
            response = self.session.get(entries_url)
            
            if response.status_code == 200:
                entries = response.json()
                logger.info(f"Retrieved {len(entries)} wine entries")
                
                # Analyze entry quality
                analysis = {
                    'total_entries': len(entries),
                    'entries_with_producer': 0,
                    'entries_with_region': 0,
                    'entries_with_price': 0,
                    'entries_with_grape': 0,
                    'entries_with_country': 0,
                    'average_confidence': 0.0,
                    'confidence_distribution': {'high': 0, 'medium': 0, 'low': 0},
                    'sample_entries': []
                }
                
                total_confidence = 0.0
                
                for i, entry in enumerate(entries):
                    # Count fields
                    if entry.get('producer'):
                        analysis['entries_with_producer'] += 1
                    if entry.get('region'):
                        analysis['entries_with_region'] += 1
                    if entry.get('price'):
                        analysis['entries_with_price'] += 1
                    if entry.get('grape_variety'):
                        analysis['entries_with_grape'] += 1
                    if entry.get('country'):
                        analysis['entries_with_country'] += 1
                    
                    # Analyze confidence
                    confidence = entry.get('row_confidence', 0.0)
                    total_confidence += confidence
                    
                    if confidence >= 0.8:
                        analysis['confidence_distribution']['high'] += 1
                    elif confidence >= 0.5:
                        analysis['confidence_distribution']['medium'] += 1
                    else:
                        analysis['confidence_distribution']['low'] += 1
                    
                    # Store sample entries
                    if i < 5:
                        analysis['sample_entries'].append(entry)
                
                if analysis['total_entries'] > 0:
                    analysis['average_confidence'] = total_confidence / analysis['total_entries']
                
                return analysis
            else:
                logger.error(f"Failed to get wine entries: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"Error analyzing wine entries: {e}")
            return {}
    
    def analyze_generated_rules(self) -> Dict[str, Any]:
        """Analyze the rules that were generated for this restaurant."""
        try:
            logger.info("Analyzing generated rules...")
            
            # Get current rules
            rules_url = f"{self.api_base}/restaurants/{self.restaurant_id}/ruleset"
            response = self.session.get(rules_url)
            
            if response.status_code == 200:
                rules_data = response.json()
                logger.info(f"Retrieved rules data: {json.dumps(rules_data, indent=2)}")
                
                # Analyze rule structure
                analysis = {
                    'has_rules': bool(rules_data.get('rules_json')),
                    'rule_count': 0,
                    'rule_types': {},
                    'rule_complexity': 'none'
                }
                
                if rules_data.get('rules_json'):
                    rules = rules_data['rules_json']
                    analysis['rule_count'] = len(rules) if isinstance(rules, dict) else 0
                    
                    # Analyze rule types
                    for rule_name, rule_data in rules.items():
                        if isinstance(rule_data, dict):
                            rule_type = rule_data.get('type', 'unknown')
                            analysis['rule_types'][rule_type] = analysis['rule_types'].get(rule_type, 0) + 1
                
                return analysis
            else:
                logger.warning(f"Could not retrieve rules: {response.status_code}")
                return {'has_rules': False}
                
        except Exception as e:
            logger.error(f"Error analyzing rules: {e}")
            return {}
    
    def run_comprehensive_test(self, email: str, password: str, test_file_path: str):
        """Run the complete pipeline analysis test."""
        logger.info("=" * 80)
        logger.info("STARTING COMPREHENSIVE PIPELINE ANALYSIS TEST")
        logger.info("=" * 80)
        
        try:
            # Step 1: Authenticate
            if not self.authenticate_with_supabase(email, password):
                logger.error("Authentication failed. Exiting.")
                return
            
            # Step 2: Clear restaurant rules
            if not self.clear_restaurant_rules():
                logger.error("Failed to clear restaurant rules. Exiting.")
                return
            
            # Step 3: Upload test file
            file_id = self.upload_test_file(test_file_path)
            if not file_id:
                logger.error("Failed to upload test file. Exiting.")
                return
            
            # Step 4: Wait for processing
            if not self.wait_for_processing(file_id):
                logger.error("File processing failed or timed out. Exiting.")
                return
            
            # Step 5: Analyze processing stages
            logger.info("\n" + "=" * 60)
            logger.info("ANALYZING PROCESSING STAGES")
            logger.info("=" * 60)
            stage_data = self.analyze_processing_stages(file_id)
            
            # Step 6: Analyze wine entries
            logger.info("\n" + "=" * 60)
            logger.info("ANALYZING WINE ENTRIES")
            logger.info("=" * 60)
            entry_analysis = self.analyze_wine_entries(file_id)
            
            # Step 7: Analyze generated rules
            logger.info("\n" + "=" * 60)
            logger.info("ANALYZING GENERATED RULES")
            logger.info("=" * 60)
            rule_analysis = self.analyze_generated_rules()
            
            # Step 8: Generate comprehensive report
            self.generate_report(file_id, stage_data, entry_analysis, rule_analysis)
            
        except Exception as e:
            logger.error(f"Test failed with error: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def generate_report(self, file_id: str, stage_data: Dict, entry_analysis: Dict, rule_analysis: Dict):
        """Generate a comprehensive analysis report."""
        logger.info("\n" + "=" * 80)
        logger.info("COMPREHENSIVE ANALYSIS REPORT")
        logger.info("=" * 80)
        
        report = {
            'test_info': {
                'timestamp': datetime.now().isoformat(),
                'restaurant_id': self.restaurant_id,
                'file_id': file_id,
                'test_file': 'the-10-cases - Test2.pdf'
            },
            'processing_stages': stage_data,
            'wine_entries_analysis': entry_analysis,
            'rules_analysis': rule_analysis,
            'summary': {
                'total_entries_processed': entry_analysis.get('total_entries', 0),
                'extraction_coverage': {
                    'producer': f"{entry_analysis.get('entries_with_producer', 0)}/{entry_analysis.get('total_entries', 0)}",
                    'region': f"{entry_analysis.get('entries_with_region', 0)}/{entry_analysis.get('total_entries', 0)}",
                    'price': f"{entry_analysis.get('entries_with_price', 0)}/{entry_analysis.get('total_entries', 0)}",
                    'grape_variety': f"{entry_analysis.get('entries_with_grape', 0)}/{entry_analysis.get('total_entries', 0)}",
                    'country': f"{entry_analysis.get('entries_with_country', 0)}/{entry_analysis.get('total_entries', 0)}"
                },
                'average_confidence': entry_analysis.get('average_confidence', 0.0),
                'rules_generated': rule_analysis.get('has_rules', False),
                'rule_count': rule_analysis.get('rule_count', 0)
            }
        }
        
        # Save detailed report to file
        report_file = f"pipeline_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Detailed report saved to: {report_file}")
        
        # Print summary
        logger.info("\nSUMMARY:")
        logger.info(f"Total entries processed: {report['summary']['total_entries_processed']}")
        logger.info(f"Producer extraction: {report['summary']['extraction_coverage']['producer']}")
        logger.info(f"Region extraction: {report['summary']['extraction_coverage']['region']}")
        logger.info(f"Price extraction: {report['summary']['extraction_coverage']['price']}")
        logger.info(f"Grape variety extraction: {report['summary']['extraction_coverage']['grape_variety']}")
        logger.info(f"Country extraction: {report['summary']['extraction_coverage']['country']}")
        logger.info(f"Average confidence: {report['summary']['average_confidence']:.2f}")
        logger.info(f"Rules generated: {report['summary']['rules_generated']}")
        logger.info(f"Rule count: {report['summary']['rule_count']}")
        
        # Print sample entries
        if entry_analysis.get('sample_entries'):
            logger.info("\nSAMPLE ENTRIES:")
            for i, entry in enumerate(entry_analysis['sample_entries'][:3]):
                logger.info(f"Entry {i+1}:")
                logger.info(f"  Producer: {entry.get('producer', 'N/A')}")
                logger.info(f"  Region: {entry.get('region', 'N/A')}")
                logger.info(f"  Price: {entry.get('price', 'N/A')}")
                logger.info(f"  Confidence: {entry.get('row_confidence', 'N/A')}")
                logger.info(f"  Raw text: {entry.get('raw_text', 'N/A')[:100]}...")

def main():
    """Main function to run the test."""
    # Test configuration
    email = "dan@admin.com"
    password = "Mental12"
    test_file_path = r"C:\Users\Dan\Projects\wine-list-parser\backend\tests\real-files\the-10-cases - Test2.pdf"
    
    # Create analyzer and run test
    analyzer = PipelineStageAnalyzer()
    analyzer.run_comprehensive_test(email, password, test_file_path)

if __name__ == "__main__":
    main() 