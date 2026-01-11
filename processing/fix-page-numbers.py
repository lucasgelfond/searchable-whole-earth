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

def fix_page_numbers():
    """
    Set page numbers for issues where they are null by checking the PDF files
    """
    # Get all issues where num_pages is null
    issues = supabase.table('issue')\
        .select('*')\
        .is_('num_pages', 'null')\
        .execute()
    
    for issue in issues.data:
        issue_id = issue['id']
        filename = issue['filename']
        
        # Get page count from PDF
        pdf_path = Path("WECs") / filename
        if not pdf_path.exists():
            print(f"PDF not found for {filename}")
            continue
            
        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            pdf_page_count = len(pdf_reader.pages)
            
        # Update the issue record with page count
        supabase.table('issue')\
            .update({'num_pages': pdf_page_count})\
            .eq('id', issue_id)\
            .execute()
            
        print(f"Updated {filename}: set to {pdf_page_count} pages")

if __name__ == "__main__":
    fix_page_numbers()
