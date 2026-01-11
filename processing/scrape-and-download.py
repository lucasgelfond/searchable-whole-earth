import os
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin
from queue import Queue
from threading import Thread

# Create WECs directory if it doesn't exist
if not os.path.exists('WECs'):
    os.makedirs('WECs')

# Initialize queue for URLs
url_queue = Queue()

# Set up headless Chrome driver
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument('--disable-software-rasterizer')
options.add_argument('--ignore-certificate-errors')
options.add_argument('--ignore-ssl-errors')
options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

# Create a driver pool
NUM_WORKERS = 3  # Number of parallel workers
drivers = []
try:
    for _ in range(NUM_WORKERS):
        drivers.append(webdriver.Chrome(options=options))
except Exception as e:
    print(f"Error initializing Chrome driver: {str(e)}")
    for d in drivers:
        d.quit()
    exit(1)

def process_url(driver, url):
    if '/p/' not in url:
        return
        
    try:
        print(f"Processing URL: {url}")
        driver.get(url)
        
        # Reduced wait time
        wait = WebDriverWait(driver, 10)
        try:
            pdf_link = wait.until(
                EC.presence_of_element_located((By.XPATH, "//a[text()='Download PDF']"))
            )
            pdf_url = pdf_link.get_attribute('href')
        except Exception as e:
            print(f"No PDF link found on {url}: {str(e)}")
            return
        
        # Download the PDF
        if pdf_url:
            response = requests.get(pdf_url, stream=True)
            if response.status_code == 200:
                # Extract filename from URL or use a counter
                filename = pdf_url.split('/')[-1]
                if not filename.endswith('.pdf'):
                    filename = f"{filename}.pdf"
                    
                filepath = os.path.join('WECs', filename)
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                print(f"Downloaded: {filename}")
            
    except Exception as e:
        print(f"Error processing {url}: {str(e)}")

def worker(driver_index):
    driver = drivers[driver_index]
    while True:
        url = url_queue.get()
        if url is None:
            break
        process_url(driver, url)
        url_queue.task_done()
        # Reduced sleep time
        time.sleep(1)

# Start multiple worker threads
worker_threads = []
for i in range(NUM_WORKERS):
    thread = Thread(target=worker, args=(i,))
    thread.start()
    worker_threads.append(thread)

# Visit main page and collect links
main_url = 'https://wholeearth.info'
response = requests.get(main_url)
soup = BeautifulSoup(response.text, 'html.parser')

# Find all relevant links
for tag in soup.find_all('a'):
    href = tag.get('href')
    if href and '/p/' in href:  # Only process URLs containing '/p/'
        full_url = urljoin(main_url, href)
        url_queue.put(full_url)
        print(f"Added to queue: {full_url}")  # Debug logging

# Add sentinel value for each worker
for _ in range(NUM_WORKERS):
    url_queue.put(None)

# Wait for all tasks to complete
url_queue.join()
for thread in worker_threads:
    thread.join()

# Clean up all drivers
for driver in drivers:
    driver.quit()


