#!/usr/bin/env python3
import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clear_restaurant_data():
    """Clear all rules and files from the specified restaurant."""
    
    # Configuration
    supabase_url = 'https://vwnvmjladuvnthcfkjqi.supabase.co'
    supabase_anon_key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ3bnZtamxhZHV2bnRoY2ZranFpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTAwMTYzNzQsImV4cCI6MjA2NTU5MjM3NH0.odOI2qeMYWD5zYULFeFeLip33Ftu7UyJp6-HgtLGJt0'
    restaurant_id = "3cce3b48-a801-475b-9552-5fb7377cb0be"
    
    # Authenticate
    auth_data = {
        'email': 'dan@admin.com',
        'password': 'Mental12'
    }
    
    headers = {
        'apikey': supabase_anon_key,
        'Content-Type': 'application/json'
    }
    
    logger.info("Authenticating with Supabase...")
    response = requests.post(f'{supabase_url}/auth/v1/token?grant_type=password', 
                           headers=headers, json=auth_data)
    
    if response.status_code != 200:
        logger.error(f"Authentication failed: {response.status_code}")
        return False
    
    access_token = response.json()['access_token']
    api_headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    logger.info("Authentication successful!")
    
    # Step 1: Clear restaurant rules
    logger.info(f"Clearing rules for restaurant {restaurant_id}...")
    rules_url = f'http://localhost:8000/api/v2/restaurants/{restaurant_id}/ruleset'
    
    # Get current rules first
    response = requests.get(rules_url, headers=api_headers)
    if response.status_code == 200:
        current_rules = response.json()
        logger.info(f"Found existing rules: {json.dumps(current_rules, indent=2)}")
        
        # Clear rules by setting empty ruleset
        clear_data = {"rules_json": {}}
        response = requests.put(rules_url, json=clear_data, headers=api_headers)
        
        if response.status_code == 200:
            logger.info("Successfully cleared restaurant rules")
        else:
            logger.error(f"Failed to clear rules: {response.status_code} - {response.text}")
    else:
        logger.info("No existing rules found")
    
    # Step 2: Get all wine lists for the restaurant
    logger.info(f"Getting wine lists for restaurant {restaurant_id}...")
    wine_lists_url = f'http://localhost:8000/api/v2/restaurants/{restaurant_id}/wine-lists'
    response = requests.get(wine_lists_url, headers=api_headers)
    
    if response.status_code == 200:
        wine_lists = response.json()
        logger.info(f"Found {len(wine_lists)} wine lists")
        
        # Step 3: Delete each wine list
        for wine_list in wine_lists:
            file_id = wine_list['id']
            filename = wine_list.get('filename', 'Unknown')
            logger.info(f"Deleting wine list: {filename} (ID: {file_id})")
            
            delete_url = f'http://localhost:8000/api/v2/wine-lists/{file_id}'
            delete_response = requests.delete(delete_url, headers=api_headers)
            
            if delete_response.status_code == 200:
                logger.info(f"Successfully deleted wine list: {filename}")
            else:
                logger.error(f"Failed to delete wine list {filename}: {delete_response.status_code} - {delete_response.text}")
    else:
        logger.error(f"Failed to get wine lists: {response.status_code} - {response.text}")
    
    # Step 4: Verify cleanup
    logger.info("Verifying cleanup...")
    
    # Check rules
    response = requests.get(rules_url, headers=api_headers)
    if response.status_code == 200:
        rules = response.json()
        if not rules.get('rules_json') or rules['rules_json'] == {}:
            logger.info("✓ Rules successfully cleared")
        else:
            logger.warning("⚠ Rules may not be fully cleared")
    
    # Check wine lists
    response = requests.get(wine_lists_url, headers=api_headers)
    if response.status_code == 200:
        wine_lists = response.json()
        if len(wine_lists) == 0:
            logger.info("✓ All wine lists successfully deleted")
        else:
            logger.warning(f"⚠ {len(wine_lists)} wine lists still remain")
    
    logger.info("Restaurant data cleanup completed!")
    return True

if __name__ == "__main__":
    clear_restaurant_data() 