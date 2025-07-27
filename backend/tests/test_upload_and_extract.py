#!/usr/bin/env python3
import requests
import time
import json
import logging
import os

# --- CONFIG ---
SUPABASE_URL = 'https://vwnvmjladuvnthcfkjqi.supabase.co'
SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ3bnZtamxhZHV2bnRoY2ZranFpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTAwMTYzNzQsImV4cCI6MjA2NTU5MjM3NH0.odOI2qeMYWD5zYULFeFeLip33Ftu7UyJp6-HgtLGJt0'
RESTAURANT_ID = '3cce3b48-a801-475b-9552-5fb7377cb0be'
PDF_PATH = os.path.join(os.path.dirname(__file__), 'real-files', 'the-10-cases - Test2.pdf')
API_BASE = 'http://localhost:8000/api/v2'
EMAIL = 'dan@admin.com'
PASSWORD = 'Mental12'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_token():
    headers = {'apikey': SUPABASE_ANON_KEY, 'Content-Type': 'application/json'}
    data = {'email': EMAIL, 'password': PASSWORD}
    r = requests.post(f'{SUPABASE_URL}/auth/v1/token?grant_type=password', headers=headers, json=data)
    r.raise_for_status()
    return r.json()['access_token']

# def clear_restaurant(token):
#     api_headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
#     # Clear ruleset
#     rules_url = f'{API_BASE}/restaurants/{RESTAURANT_ID}/ruleset'
#     requests.put(rules_url, json={'rules_json': {}}, headers=api_headers)
#     # Delete all wine lists
#     wine_lists_url = f'{API_BASE}/restaurants/{RESTAURANT_ID}/wine-lists'
#     r = requests.get(wine_lists_url, headers=api_headers)
#     if r.status_code == 200:
#         for wl in r.json():
#             file_id = wl['id']
#             requests.delete(f'{API_BASE}/wine-lists/{file_id}', headers=api_headers)

def upload_pdf(token):
    api_headers = {'Authorization': f'Bearer {token}'}
    with open(PDF_PATH, 'rb') as f:
        files = {'file': f}
        data = {'restaurant_id': RESTAURANT_ID}
        r = requests.post(f'{API_BASE}/wine-lists/upload', files=files, data=data, headers=api_headers)
        r.raise_for_status()
        return r.json()['id']

def wait_for_processing(token, wine_list_id, timeout=120):
    api_headers = {'Authorization': f'Bearer {token}'}
    status_url = f'{API_BASE}/wine-lists/{wine_list_id}'
    for _ in range(timeout):
        r = requests.get(status_url, headers=api_headers)
        if r.status_code == 200:
            status = r.json().get('status')
            logger.info(f"Wine list status: {status}")
            if status == 'parsed':
                return True
            if status == 'error':
                logger.error(f"Processing failed: {r.json().get('notes')}")
                return False
        time.sleep(1)
    logger.error("Timeout waiting for processing.")
    return False

def fetch_entries(token, wine_list_id):
    api_headers = {'Authorization': f'Bearer {token}'}
    url = f'{API_BASE}/wine-entries/{wine_list_id}'
    r = requests.get(url, headers=api_headers)
    r.raise_for_status()
    return r.json()

def summarize(entries):
    total = len(entries)
    with_producer = sum(1 for e in entries if e.get('producer'))
    with_wine_name = sum(1 for e in entries if e.get('wine_name') or e.get('cuvee'))
    with_vintage = sum(1 for e in entries if e.get('vintage'))
    with_price = sum(1 for e in entries if e.get('price'))
    logger.info(f"Total entries: {total}")
    logger.info(f"With producer: {with_producer}")
    logger.info(f"With wine name: {with_wine_name}")
    logger.info(f"With vintage: {with_vintage}")
    logger.info(f"With price: {with_price}")
    logger.info(f"Sample entries:")
    for e in entries[:5]:
        logger.info(json.dumps(e, indent=2))

def main():
    logger.info("Authenticating...")
    token = get_token()
    # logger.info("Clearing restaurant data...")
    # clear_restaurant(token)
    logger.info("Uploading PDF...")
    wine_list_id = upload_pdf(token)
    logger.info(f"Uploaded. Wine list ID: {wine_list_id}")
    logger.info("Waiting for processing...")
    if wait_for_processing(token, wine_list_id):
        logger.info("Fetching extracted entries...")
        entries = fetch_entries(token, wine_list_id)
        summarize(entries)
    else:
        logger.error("Processing did not complete successfully.")

if __name__ == "__main__":
    main() 