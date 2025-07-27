#!/usr/bin/env python3
import requests
import json
import logging
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PipelineAnalyzer:
    def __init__(self):
        self.supabase_url = 'https://vwnvmjladuvnthcfkjqi.supabase.co'
        self.supabase_anon_key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ3bnZtamxhZHV2bnRoY2ZranFpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTAwMTYzNzQsImV4cCI6MjA2NTU5MjM3NH0.odOI2qeMYWD5zYULFeFeLip33Ftu7UyJp6-HgtLGJt0'
        self.access_token = None
        self.api_headers = None
        
    def authenticate(self):
        """Authenticate with Supabase and get access token."""
        auth_data = {
            'email': 'dan@admin.com',
            'password': 'Mental12'
        }
        
        headers = {
            'apikey': self.supabase_anon_key,
            'Content-Type': 'application/json'
        }
        
        response = requests.post(f'{self.supabase_url}/auth/v1/token?grant_type=password', 
                               headers=headers, json=auth_data)
        
        if response.status_code == 200:
            self.access_token = response.json()['access_token']
            self.api_headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            logger.info("Authentication successful!")
            return True
        else:
            logger.error(f"Authentication failed: {response.status_code}")
            return False
    
    def get_processing_stages(self, file_id: str) -> Dict[str, Any]:
        """Get processing data for each stage of the pipeline."""
        logger.info(f"Getting processing stages for file {file_id}")
        
        stages = ['extractor', 'preprocessor', 'categorizer', 'field_extractor', 'learning']
        stage_data = {}
        
        for stage in stages:
            try:
                url = f'http://localhost:8000/api/v2/wine-lists/{file_id}/processing-data?stage={stage}'
                response = requests.get(url, headers=self.api_headers)
                
                if response.status_code == 200:
                    stage_data[stage] = response.json()
                    logger.info(f"Retrieved {stage} data")
                else:
                    logger.warning(f"Could not retrieve {stage} data: {response.status_code}")
                    stage_data[stage] = None
            except Exception as e:
                logger.error(f"Error getting {stage} data: {e}")
                stage_data[stage] = None
        
        return stage_data
    
    def get_wine_entries(self, file_id: str) -> List[Dict[str, Any]]:
        """Get all wine entries for analysis."""
        url = f'http://localhost:8000/api/v2/wine-entries/{file_id}'
        response = requests.get(url, headers=self.api_headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error getting wine entries: {response.status_code}")
            return []
    
    def get_generated_rules(self, restaurant_id: str) -> Dict[str, Any]:
        """Get the rules that were generated for this restaurant."""
        url = f'http://localhost:8000/api/v2/restaurants/{restaurant_id}/ruleset'
        response = requests.get(url, headers=self.api_headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error getting rules: {response.status_code}")
            return {}
    
    def analyze_entry_quality(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the quality of extracted entries."""
        analysis = {
            'total_entries': len(entries),
            'entries_with_producer': 0,
            'entries_with_region': 0,
            'entries_with_price': 0,
            'entries_with_grape': 0,
            'entries_with_country': 0,
            'entries_with_vintage': 0,
            'sample_entries': [],
            'problematic_entries': [],
            'good_entries': []
        }
        
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
            if entry.get('vintage'):
                analysis['entries_with_vintage'] += 1
            
            # Store sample entries
            if i < 10:
                analysis['sample_entries'].append(entry)
            
            # Identify problematic entries (entries with obvious issues)
            raw_text = entry.get('raw_text', '')
            producer = entry.get('producer', '')
            
            # Check for problematic patterns
            if producer and len(producer) <= 2:  # Very short producer names
                analysis['problematic_entries'].append({
                    'index': i,
                    'entry': entry,
                    'issue': 'Very short producer name'
                })
            
            # Check for missing obvious fields
            if raw_text and '2019' in raw_text and not entry.get('vintage'):
                analysis['problematic_entries'].append({
                    'index': i,
                    'entry': entry,
                    'issue': 'Missing vintage despite year in text'
                })
            
            # Check for good entries (entries with most fields populated)
            populated_fields = sum(1 for field in ['producer', 'region', 'price', 'grape_variety', 'country', 'vintage'] 
                                 if entry.get(field))
            if populated_fields >= 4:
                analysis['good_entries'].append({
                    'index': i,
                    'entry': entry,
                    'populated_fields': populated_fields
                })
        
        return analysis
    
    def analyze_raw_text_patterns(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze patterns in raw text to understand extraction issues."""
        patterns = {
            'text_lengths': [],
            'common_patterns': {},
            'year_patterns': [],
            'price_patterns': [],
            'producer_patterns': []
        }
        
        for entry in entries:
            raw_text = entry.get('raw_text', '')
            if not raw_text:
                continue
            
            # Analyze text length
            patterns['text_lengths'].append(len(raw_text))
            
            # Look for year patterns
            import re
            years = re.findall(r'\b(19|20)\d{2}\b', raw_text)
            if years:
                patterns['year_patterns'].append({
                    'text': raw_text,
                    'years_found': years,
                    'vintage_extracted': entry.get('vintage')
                })
            
            # Look for price patterns
            prices = re.findall(r'\b\d+\s*$', raw_text)  # Numbers at end
            if prices:
                patterns['price_patterns'].append({
                    'text': raw_text,
                    'prices_found': prices,
                    'price_extracted': entry.get('price')
                })
            
            # Look for producer patterns (text before first comma or quote)
            producer_match = re.match(r'^([^,\'\"]+)', raw_text.strip())
            if producer_match:
                potential_producer = producer_match.group(1).strip()
                patterns['producer_patterns'].append({
                    'text': raw_text,
                    'potential_producer': potential_producer,
                    'producer_extracted': entry.get('producer')
                })
        
        return patterns
    
    def run_comprehensive_analysis(self, file_id: str, restaurant_id: str):
        """Run comprehensive analysis of the pipeline."""
        logger.info("=" * 80)
        logger.info("COMPREHENSIVE PIPELINE ANALYSIS")
        logger.info("=" * 80)
        
        if not self.authenticate():
            return
        
        # Get processing stages
        logger.info("\n1. ANALYZING PROCESSING STAGES")
        logger.info("-" * 40)
        stage_data = self.get_processing_stages(file_id)
        
        for stage, data in stage_data.items():
            if data:
                logger.info(f"{stage.upper()}: Data available")
                if isinstance(data, dict) and 'data' in data:
                    logger.info(f"  - Data keys: {list(data['data'].keys()) if isinstance(data['data'], dict) else 'Not a dict'}")
            else:
                logger.info(f"{stage.upper()}: No data available")
        
        # Get wine entries
        logger.info("\n2. ANALYZING WINE ENTRIES")
        logger.info("-" * 40)
        entries = self.get_wine_entries(file_id)
        logger.info(f"Total entries: {len(entries)}")
        
        # Analyze entry quality
        quality_analysis = self.analyze_entry_quality(entries)
        
        logger.info(f"\nExtraction Coverage:")
        total = quality_analysis['total_entries']
        logger.info(f"  Producer: {quality_analysis['entries_with_producer']}/{total} ({quality_analysis['entries_with_producer']/total*100:.1f}%)")
        logger.info(f"  Region: {quality_analysis['entries_with_region']}/{total} ({quality_analysis['entries_with_region']/total*100:.1f}%)")
        logger.info(f"  Price: {quality_analysis['entries_with_price']}/{total} ({quality_analysis['entries_with_price']/total*100:.1f}%)")
        logger.info(f"  Grape Variety: {quality_analysis['entries_with_grape']}/{total} ({quality_analysis['entries_with_grape']/total*100:.1f}%)")
        logger.info(f"  Country: {quality_analysis['entries_with_country']}/{total} ({quality_analysis['entries_with_country']/total*100:.1f}%)")
        logger.info(f"  Vintage: {quality_analysis['entries_with_vintage']}/{total} ({quality_analysis['entries_with_vintage']/total*100:.1f}%)")
        
        # Show problematic entries
        logger.info(f"\nProblematic Entries ({len(quality_analysis['problematic_entries'])}):")
        for prob in quality_analysis['problematic_entries'][:5]:  # Show first 5
            entry = prob['entry']
            logger.info(f"  Entry {prob['index']}: {prob['issue']}")
            logger.info(f"    Raw text: {entry.get('raw_text', 'N/A')}")
            logger.info(f"    Producer: {entry.get('producer', 'N/A')}")
            logger.info(f"    Vintage: {entry.get('vintage', 'N/A')}")
            logger.info(f"    Price: {entry.get('price', 'N/A')}")
            logger.info("")
        
        # Show good entries
        logger.info(f"\nGood Entries ({len(quality_analysis['good_entries'])}):")
        for good in quality_analysis['good_entries'][:3]:  # Show first 3
            entry = good['entry']
            logger.info(f"  Entry {good['index']} ({good['populated_fields']} fields):")
            logger.info(f"    Raw text: {entry.get('raw_text', 'N/A')}")
            logger.info(f"    Producer: {entry.get('producer', 'N/A')}")
            logger.info(f"    Vintage: {entry.get('vintage', 'N/A')}")
            logger.info(f"    Price: {entry.get('price', 'N/A')}")
            logger.info(f"    Grape: {entry.get('grape_variety', 'N/A')}")
            logger.info("")
        
        # Analyze raw text patterns
        logger.info("\n3. ANALYZING RAW TEXT PATTERNS")
        logger.info("-" * 40)
        pattern_analysis = self.analyze_raw_text_patterns(entries)
        
        logger.info(f"Text length analysis:")
        if pattern_analysis['text_lengths']:
            avg_length = sum(pattern_analysis['text_lengths']) / len(pattern_analysis['text_lengths'])
            logger.info(f"  Average text length: {avg_length:.1f} characters")
            logger.info(f"  Min length: {min(pattern_analysis['text_lengths'])}")
            logger.info(f"  Max length: {max(pattern_analysis['text_lengths'])}")
        
        logger.info(f"\nYear extraction issues ({len(pattern_analysis['year_patterns'])}):")
        for year_issue in pattern_analysis['year_patterns'][:3]:
            logger.info(f"  Text: {year_issue['text']}")
            logger.info(f"  Years found: {year_issue['years_found']}")
            logger.info(f"  Vintage extracted: {year_issue['vintage_extracted']}")
            logger.info("")
        
        logger.info(f"\nPrice extraction issues ({len(pattern_analysis['price_patterns'])}):")
        for price_issue in pattern_analysis['price_patterns'][:3]:
            logger.info(f"  Text: {price_issue['text']}")
            logger.info(f"  Prices found: {price_issue['prices_found']}")
            logger.info(f"  Price extracted: {price_issue['price_extracted']}")
            logger.info("")
        
        logger.info(f"\nProducer extraction issues ({len(pattern_analysis['producer_patterns'])}):")
        for producer_issue in pattern_analysis['producer_patterns'][:3]:
            logger.info(f"  Text: {producer_issue['text']}")
            logger.info(f"  Potential producer: {producer_issue['potential_producer']}")
            logger.info(f"  Producer extracted: {producer_issue['producer_extracted']}")
            logger.info("")
        
        # Get generated rules
        logger.info("\n4. ANALYZING GENERATED RULES")
        logger.info("-" * 40)
        rules = self.get_generated_rules(restaurant_id)
        
        if rules and rules.get('rules_json'):
            rules_data = rules['rules_json']
            logger.info(f"Rules found: {len(rules_data) if isinstance(rules_data, dict) else 0}")
            
            if isinstance(rules_data, dict):
                for rule_name, rule_content in rules_data.items():
                    logger.info(f"  Rule: {rule_name}")
                    if isinstance(rule_content, dict):
                        logger.info(f"    Type: {rule_content.get('type', 'unknown')}")
                        if 'regex_patterns' in rule_content:
                            logger.info(f"    Regex patterns: {len(rule_content['regex_patterns'])}")
                        if 'structural_rules' in rule_content:
                            logger.info(f"    Structural rules: {len(rule_content['structural_rules'])}")
        else:
            logger.info("No rules found or rules are empty")
        
        # Generate recommendations
        logger.info("\n5. RECOMMENDATIONS")
        logger.info("-" * 40)
        self.generate_recommendations(quality_analysis, pattern_analysis, rules)
    
    def generate_recommendations(self, quality_analysis: Dict, pattern_analysis: Dict, rules: Dict):
        """Generate recommendations based on analysis."""
        logger.info("Based on the analysis, here are the key issues and recommendations:")
        
        # Vintage extraction issues
        if pattern_analysis['year_patterns']:
            missing_vintages = sum(1 for issue in pattern_analysis['year_patterns'] if not issue['vintage_extracted'])
            if missing_vintages > 0:
                logger.info(f"\n1. VINTAGE EXTRACTION ISSUES:")
                logger.info(f"   - {missing_vintages} entries have years in text but no vintage extracted")
                logger.info(f"   - Recommendation: Review vintage regex patterns")
                logger.info(f"   - Current patterns may be too restrictive")
        
        # Price extraction issues
        if pattern_analysis['price_patterns']:
            missing_prices = sum(1 for issue in pattern_analysis['price_patterns'] if not issue['price_extracted'])
            if missing_prices > 0:
                logger.info(f"\n2. PRICE EXTRACTION ISSUES:")
                logger.info(f"   - {missing_prices} entries have prices in text but no price extracted")
                logger.info(f"   - Recommendation: Review price extraction logic")
                logger.info(f"   - Consider end-of-line price patterns")
        
        # Producer extraction issues
        if pattern_analysis['producer_patterns']:
            short_producers = sum(1 for issue in pattern_analysis['producer_patterns'] 
                                if issue['producer_extracted'] and len(issue['producer_extracted']) <= 2)
            if short_producers > 0:
                logger.info(f"\n3. PRODUCER EXTRACTION ISSUES:")
                logger.info(f"   - {short_producers} entries have very short producer names")
                logger.info(f"   - Recommendation: Review producer extraction patterns")
                logger.info(f"   - Current patterns may be too aggressive")
        
        # Overall recommendations
        logger.info(f"\n4. OVERALL RECOMMENDATIONS:")
        logger.info(f"   - Review regex patterns for all fields")
        logger.info(f"   - Check AI rule generation effectiveness")
        logger.info(f"   - Consider improving database-enhanced extraction")
        logger.info(f"   - Add validation for extracted field lengths")
        logger.info(f"   - Implement confidence scoring improvements")

def main():
    file_id = "6379949a-251e-4682-947b-e74949b2d7aa"
    restaurant_id = "3cce3b48-a801-475b-9552-5fb7377cb0be"
    
    analyzer = PipelineAnalyzer()
    analyzer.run_comprehensive_analysis(file_id, restaurant_id)

if __name__ == "__main__":
    main() 