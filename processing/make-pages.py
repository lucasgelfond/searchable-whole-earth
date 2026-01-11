import os
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables and initialize Supabase client
load_dotenv()
supabase: Client = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

def save_concatenated_pages():
    """
    Fetch all issues and their pages from Supabase,
    concatenate page contents in order, and save to files
    """
    # Create output directory if it doesn't exist
    output_dir = Path("OCR-results")
    output_dir.mkdir(exist_ok=True)
    
    # Get all issues
    issues = supabase.table('issue').select('*').execute()
    
    for issue in issues.data:
        issue_id = issue['id']
        filename = issue['filename']
        # Strip .pdf from filename for output
        output_filename = filename.replace('.pdf', '')
        output_path = output_dir / f"{output_filename}.txt"
        
        # Skip if output file already exists
        if output_path.exists():
            print(f"✓ {filename}: Output file already exists")
            continue
            
        # Get count of all pages in database for this issue
        pages = supabase.table('page')\
            .select('*')\
            .eq('parent_issue_id', issue_id)\
            .execute()
            
        db_page_count = len(pages.data)
        
        # Update issue record if num_pages is None
        if issue['num_pages'] is None:
            supabase.table('issue')\
                .update({'num_pages': db_page_count})\
                .eq('id', issue_id)\
                .execute()
            print(f"Updated {filename} with correct page count: {db_page_count}")
        # Skip only if page counts don't match and num_pages is not None
        elif db_page_count != issue['num_pages']:
            print(f"Skipping {filename}: Have {db_page_count} pages, expected {issue['num_pages']}")
            continue
            
        # Get all non-error pages for this issue, ordered by page number
        valid_pages = supabase.table('page')\
            .select('*')\
            .eq('parent_issue_id', issue_id)\
            .eq('error', False)\
            .order('page_number')\
            .execute()
            
        if not valid_pages.data:
            print(f"No valid pages found for issue {filename}")
            continue
            
        # Concatenate page contents in order
        full_text = ""
        for page in valid_pages.data:
            # Remove ```text annotations if present
            cleaned_text = page['ocr_result'].replace('```text', '')
            full_text += cleaned_text + "\n"
            
        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
            
        print(f"Saved concatenated text for {filename}")

if __name__ == "__main__":
    save_concatenated_pages()
