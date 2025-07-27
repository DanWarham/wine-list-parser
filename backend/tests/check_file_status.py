#!/usr/bin/env python3
import requests
import json

def check_file_status():
    # Authenticate with Supabase
    supabase_url = 'https://vwnvmjladuvnthcfkjqi.supabase.co'
    supabase_anon_key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ3bnZtamxhZHV2bnRoY2ZranFpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTAwMTYzNzQsImV4cCI6MjA2NTU5MjM3NH0.odOI2qeMYWD5zYULFeFeLip33Ftu7UyJp6-HgtLGJt0'

    auth_data = {
        'email': 'dan@admin.com',
        'password': 'Mental12'
    }

    headers = {
        'apikey': supabase_anon_key,
        'Content-Type': 'application/json'
    }

    print("Authenticating with Supabase...")
    response = requests.post(f'{supabase_url}/auth/v1/token?grant_type=password', headers=headers, json=auth_data)
    
    if response.status_code == 200:
        access_token = response.json()['access_token']
        print("Authentication successful!")
        
        # Check file status
        api_headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        file_id = '6379949a-251e-4682-947b-e74949b2d7aa'
        print(f"\nChecking file status for ID: {file_id}")
        
        response = requests.get(f'http://localhost:8000/api/v2/wine-lists/{file_id}', headers=api_headers)
        
        if response.status_code == 200:
            file_data = response.json()
            print('File Status:', file_data.get('status'))
            print('File Metadata:', json.dumps(file_data.get('metadata', {}), indent=2))
            
            # Get wine entries
            print("\nFetching wine entries...")
            entries_response = requests.get(f'http://localhost:8000/api/v2/wine-entries/{file_id}', headers=api_headers)
            
            if entries_response.status_code == 200:
                entries = entries_response.json()
                print(f'Total Wine Entries: {len(entries)}')
                
                if entries:
                    print('\nSample Entry:')
                    print(json.dumps(entries[0], indent=2, default=str))
                    
                    # Analyze extraction quality
                    print('\nExtraction Analysis:')
                    total_entries = len(entries)
                    entries_with_producer = sum(1 for e in entries if e.get('producer'))
                    entries_with_region = sum(1 for e in entries if e.get('region'))
                    entries_with_price = sum(1 for e in entries if e.get('price'))
                    entries_with_grape = sum(1 for e in entries if e.get('grape_variety'))
                    entries_with_country = sum(1 for e in entries if e.get('country'))
                    
                    print(f'Producer extraction: {entries_with_producer}/{total_entries} ({entries_with_producer/total_entries*100:.1f}%)')
                    print(f'Region extraction: {entries_with_region}/{total_entries} ({entries_with_region/total_entries*100:.1f}%)')
                    print(f'Price extraction: {entries_with_price}/{total_entries} ({entries_with_price/total_entries*100:.1f}%)')
                    print(f'Grape variety extraction: {entries_with_grape}/{total_entries} ({entries_with_grape/total_entries*100:.1f}%)')
                    print(f'Country extraction: {entries_with_country}/{total_entries} ({entries_with_country/total_entries*100:.1f}%)')
                    
                    # Show confidence distribution
                    confidences = [e.get('row_confidence', 0) for e in entries if e.get('row_confidence') is not None]
                    if confidences:
                        avg_confidence = sum(confidences) / len(confidences)
                        print(f'Average confidence: {avg_confidence:.2f}')
                        
                        high_conf = sum(1 for c in confidences if c >= 0.8)
                        med_conf = sum(1 for c in confidences if 0.5 <= c < 0.8)
                        low_conf = sum(1 for c in confidences if c < 0.5)
                        
                        print(f'High confidence (≥0.8): {high_conf}/{len(confidences)} ({high_conf/len(confidences)*100:.1f}%)')
                        print(f'Medium confidence (0.5-0.8): {med_conf}/{len(confidences)} ({med_conf/len(confidences)*100:.1f}%)')
                        print(f'Low confidence (<0.5): {low_conf}/{len(confidences)} ({low_conf/len(confidences)*100:.1f}%)')
                else:
                    print("No wine entries found")
            else:
                print(f'Error getting wine entries: {entries_response.status_code} - {entries_response.text}')
        else:
            print(f'Error getting file: {response.status_code} - {response.text}')
    else:
        print(f'Authentication failed: {response.status_code} - {response.text}')

if __name__ == "__main__":
    check_file_status() 