import os
from supabase import create_client, Client
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin
import time
import re

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

def extract_metadata(driver, url):
    """Extract metadata from a WEC issue page"""
    print(f"\nExtracting metadata from {url}")
    driver.get(url)
    
    # Wait for content to load
    print("Waiting for content to load...")
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "section")))
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    # Find the main section
    section = soup.find('section', class_='grid')
    if not section:
        print("Could not find main section")
        return None
        
    metadata = {
        'issue_url': url,
        'description': None,
        'pdf_download': None,
        'internet_archive': None,
        'collection': None,
        'pub_date': None,
        'filename': None
    }
    
    # Extract description
    desc_div = section.find('div', class_='with-indent')
    if desc_div and desc_div.p:
        metadata['description'] = str(desc_div.p)
        print("Found description")
    else:
        print("No description found")
    
    # Find links list
    links_ul = section.find('ul', class_='links')
    if links_ul:
        print("Found links section")
        # Extract links
        for li in links_ul.find_all('li'):
            text = li.get_text()
            
            # Get PDF and Archive links
            if 'Links:' in text:
                links = li.find_all('a')
                for link in links:
                    if 'Download PDF' in link.text:
                        metadata['pdf_download'] = link['href']
                        metadata['filename'] = link['href'].split('/')[-1]
                        print(f"Found PDF link: {metadata['filename']}")
                    elif 'Internet Archive' in link.text:
                        metadata['internet_archive'] = link['href']
                        print(f"Found Internet Archive link: {metadata['internet_archive']}")
            
            # Get collection
            elif 'Collection:' in text:
                collection_link = li.find('a')
                if collection_link and 'collection=' in collection_link['href']:
                    metadata['collection'] = collection_link['href'].split('collection=')[1]
                    print(f"Found collection: {metadata['collection']}")
            
            # Get publication date
            elif 'Published:' in text:
                pub_date = text.replace('Published:', '').strip()
                metadata['pub_date'] = pub_date
                print(f"Found publication date: {pub_date}")
    else:
        print("No links section found")
    
    print("Metadata extraction complete")
    return metadata

def update_issue_metadata():
    """Update issue records with metadata from their pages"""
    print("\nStarting metadata update process")
    
    # Set up headless Chrome driver
    print("Configuring Chrome driver...")
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=options)
    print("Chrome driver initialized")
    
    try:
        # Visit main page and collect links
        main_url = 'https://wholeearth.info'
        print(f"\nFetching main page: {main_url}")
        response = requests.get(main_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all issue pages
        issue_count = 0
        for tag in soup.find_all('a'):
            href = tag.get('href')
            if href and '/p/' in href:
                issue_count += 1
                issue_url = urljoin(main_url, href)
                print(f"\nProcessing issue {issue_count}: {issue_url}")
                
                metadata = extract_metadata(driver, issue_url)
                if metadata and metadata['filename']:
                    # Update database using filename as key
                    result = supabase.table('issue').update(metadata).eq('filename', metadata['filename']).execute()
                    print(f"Successfully updated database for {metadata['filename']}")
                else:
                    print(f"Failed to extract metadata for {issue_url}")
                
                # Small delay between requests
                print("Waiting before next request...")
                time.sleep(1)
                
    finally:
        print("\nClosing Chrome driver")
        driver.quit()
        print("Metadata update process complete")

if __name__ == "__main__":
    update_issue_metadata()

