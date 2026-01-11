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

def check_page_counts():
    """
    Compare page counts between PDFs and database records
    """
    # Get all issues
    issues = supabase.table('issue').select('*').execute()
    
    for issue in issues.data:
        issue_id = issue['id']
        filename = issue['filename']
        
        # Get count of pages in database for this issue
        pages = supabase.table('page')\
            .select('id')\
            .eq('parent_issue_id', issue_id)\
            .execute()
        
        db_page_count = len(pages.data)
        
        # Get/set PDF page count from issue record
        if issue['num_pages'] is None:
            # Need to check PDF to set the count
            pdf_path = Path("WECs") / filename
            if not pdf_path.exists():
                print(f"PDF not found for {filename}")
                continue
                
            with open(pdf_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                pdf_page_count = len(pdf_reader.pages)
                
            # Update the issue record with page count
            supabase.table('issue').update({'num_pages': pdf_page_count})\
                .eq('id', issue_id)\
                .execute()
        else:
            pdf_page_count = issue['num_pages']
        
        # Compare counts
        if db_page_count != pdf_page_count:
            print(f"Mismatch for {filename}: Should have {pdf_page_count} pages, DB has {db_page_count} pages")
        else:
            print(f"✓ {filename}: {pdf_page_count} pages")

if __name__ == "__main__":
    check_page_counts()
