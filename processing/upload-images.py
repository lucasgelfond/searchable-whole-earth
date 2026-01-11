import cloudinary
import cloudinary.uploader
from pathlib import Path
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from pdf2image import convert_from_path
import PyPDF2
import tempfile
from concurrent.futures import ThreadPoolExecutor
import threading
from PIL import Image

# Load environment variables
load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'), 
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

def upload_page_image(pdf_path: str, page_num: int) -> str:
    """Convert PDF page to image and upload to Cloudinary"""
    thread_name = threading.current_thread().name
    print(f"{thread_name}: Converting page {page_num} to image...")
    images = convert_from_path(
        pdf_path,
        dpi=300,
        first_page=page_num,
        last_page=page_num,
        thread_count=1
    )
    
    if not images:
        print(f"{thread_name}: Failed to convert page {page_num}")
        return None
        
    image = images[0]
    
    # Generate unique filename
    filename = f"{Path(pdf_path).stem}_page_{page_num}"
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
        try:
            # Convert to RGB and save as JPEG with compression
            rgb_image = image.convert('RGB')
            rgb_image.save(tmp_file.name, 'JPEG', quality=85, optimize=True)
            
            # Check file size and reduce quality if needed
            while os.path.getsize(tmp_file.name) > 10_000_000:  # 10MB limit
                quality = int(quality * 0.9)  # Reduce quality by 10%
                if quality < 20:  # Set minimum quality threshold
                    print(f"{thread_name}: Could not reduce file size enough")
                    return None
                rgb_image.save(tmp_file.name, 'JPEG', quality=quality, optimize=True)
            
            print(f"{thread_name}: Uploading {filename} to Cloudinary...")
            # Upload the temporary file to Cloudinary
            result = cloudinary.uploader.upload(tmp_file.name, public_id=filename)
            print(f"{thread_name}: Cloudinary upload result: {result}")
            
            return result['secure_url']
        finally:
            # Clean up
            image.close()
            rgb_image.close()
            del images
            # Remove temporary file
            if os.path.exists(tmp_file.name):
                os.unlink(tmp_file.name)

def process_page(pdf_path: str, page: dict, issue_id: str):
    """Process a single page"""
    thread_name = threading.current_thread().name
    page_num = int(page['page_number'])
    print(f"{thread_name}: Processing page {page_num}")
    
    try:
        # Upload image to Cloudinary
        image_url = upload_page_image(str(pdf_path), page_num)
        
        if image_url:
            print(f"{thread_name}: Updating database with image URL for page {page_num}")
            try:
                # Update database with image URL
                supabase.table('page').update({
                    'image_url': image_url
                }).eq('id', page['id']).execute()
            except Exception as e:
                print(f"{thread_name}: Database update failed for page {page_num}: {str(e)}")
        else:
            print(f"{thread_name}: Failed to upload image for page {page_num}")
    except Exception as e:
        print(f"{thread_name}: Failed to process page {page_num}: {str(e)}")

def process_pdfs(directory: str = "WECs"):
    """Process all PDFs in directory and upload page images"""
    pdf_dir = Path(directory)
    if not pdf_dir.exists():
        print(f"Directory {directory} not found")
        return
        
    for pdf_path in sorted(pdf_dir.glob("*.pdf")):
        print(f"\nProcessing {pdf_path}")
        
        # Get issue ID from database
        filename = pdf_path.name
        result = supabase.table('issue').select('id').eq('filename', filename).execute()
        if not result.data:
            print(f"Issue not found for {filename}")
            continue
            
        issue_id = result.data[0]['id']
        
        # Get all pages for this issue that don't have an image_url
        pages = supabase.table('page').select('*').eq('parent_issue_id', issue_id).is_('image_url', None).execute()
        
        # Process pages with thread pool
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(process_page, pdf_path, page, issue_id)
                for page in pages.data
            ]
            # Wait for all tasks to complete
            for future in futures:
                future.result()

if __name__ == "__main__":
    process_pdfs()
