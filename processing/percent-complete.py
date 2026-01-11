import os
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv
import PyPDF2

# Load environment variables and initialize Supabase client
load_dotenv()
supabase: Client = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

def get_completion_stats():
    """
    Calculate total pages across all PDFs and database records
    """
    # Get total pages in database using count aggregation
    pages = supabase.table('page').select('*', count='exact').execute()
    db_total_pages = pages.count
    
    # Get total pages across all PDFs
    pdf_total_pages = 0
    pdf_dir = Path("WECs")
    
    if not pdf_dir.exists():
        print("WECs directory not found")
        return
        
    for pdf_file in pdf_dir.glob("*.pdf"):
        with open(pdf_file, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            pdf_total_pages += len(pdf_reader.pages)
    
    # Calculate percentage
    percent_complete = (db_total_pages / pdf_total_pages) * 100
    
    print(f"Total PDF pages: {pdf_total_pages}")
    print(f"Pages in database: {db_total_pages}")
    print(f"Percent complete: {percent_complete:.1f}%")

if __name__ == "__main__":
    get_completion_stats()
