import os
import tempfile
import requests
import boto3
from botocore.config import Config
import psycopg2
from dotenv import load_dotenv
from urllib.parse import urlparse
import uuid
from concurrent.futures import ThreadPoolExecutor
import threading

load_dotenv()

# R2 Configuration
r2_client = boto3.client(
    's3',
    endpoint_url=os.getenv('R2_ENDPOINT'),
    aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
    config=Config(signature_version='s3v4'),
    region_name='auto'
)

R2_BUCKET = os.getenv('R2_BUCKET_NAME', 'whole-earth')
BATCH_SIZE = 100


def get_db_connection():
    """Create a database connection"""
    return psycopg2.connect(os.getenv('DB_URL'))


def fetch_pages_batch(cursor, batch_size=BATCH_SIZE):
    """Fetch a batch of pages that need migration"""
    cursor.execute("""
        SELECT id, image_url, r2_object_id
        FROM page
        WHERE r2_object_id IS NULL AND image_url IS NOT NULL
        LIMIT %s
    """, (batch_size,))
    return cursor.fetchall()


def download_image(url, temp_dir):
    """Download image from URL to temp directory"""
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        # Get file extension from URL or content-type
        parsed = urlparse(url)
        path = parsed.path
        ext = os.path.splitext(path)[1] or '.jpg'

        # Create temp file
        temp_path = os.path.join(temp_dir, f"{uuid.uuid4()}{ext}")
        with open(temp_path, 'wb') as f:
            f.write(response.content)

        return temp_path
    except Exception as e:
        print(f"  Failed to download {url}: {e}")
        return None


def upload_to_r2(file_path, object_key):
    """Upload file to R2 and return the object key"""
    try:
        # Determine content type
        ext = os.path.splitext(file_path)[1].lower()
        content_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        content_type = content_types.get(ext, 'application/octet-stream')

        r2_client.upload_file(
            file_path,
            R2_BUCKET,
            object_key,
            ExtraArgs={'ContentType': content_type}
        )
        return object_key
    except Exception as e:
        print(f"  Failed to upload to R2: {e}")
        return None


def generate_object_key(page_id, image_url):
    """Generate a unique object key for R2"""
    # Extract original filename if possible
    parsed = urlparse(image_url)
    original_name = os.path.basename(parsed.path)
    ext = os.path.splitext(original_name)[1] or '.jpg'

    # Use page ID as the key for easy lookup
    return f"pages/{page_id}{ext}"


def process_page(page_data, temp_dir):
    """Process a single page migration"""
    thread_name = threading.current_thread().name
    page_id, image_url, _ = page_data

    print(f"{thread_name}: Processing page {page_id}...")

    try:
        # Download image
        temp_path = download_image(image_url, temp_dir)
        if not temp_path:
            return None

        # Generate object key
        object_key = generate_object_key(page_id, image_url)

        # Upload to R2
        uploaded_key = upload_to_r2(temp_path, object_key)
        if not uploaded_key:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return None

        # Clean up temp file
        if os.path.exists(temp_path):
            os.unlink(temp_path)

        print(f"{thread_name}: Migrated {object_key}")
        return (page_id, uploaded_key)
    except Exception as e:
        print(f"{thread_name}: Failed to process page {page_id}: {e}")
        return None


def migrate_batch():
    """Migrate one batch of images"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        pages = fetch_pages_batch(cursor)

        if not pages:
            print("No more pages to migrate!")
            return 0

        print(f"Processing batch of {len(pages)} pages...")

        with tempfile.TemporaryDirectory() as temp_dir:
            migrated = 0

            # Process pages in batches of 10
            batch_size = 10
            for i in range(0, len(pages), batch_size):
                batch = pages[i:i + batch_size]
                print(f"\nProcessing batch {i // batch_size + 1} of {(len(pages) + batch_size - 1) // batch_size} ({len(batch)} pages)")

                with ThreadPoolExecutor(max_workers=batch_size) as executor:
                    futures = [
                        executor.submit(process_page, page, temp_dir)
                        for page in batch
                    ]

                    # Wait for batch to complete and update database
                    for future in futures:
                        result = future.result()
                        if result:
                            page_id, uploaded_key = result
                            cursor.execute("""
                                UPDATE page
                                SET r2_object_id = %s
                                WHERE id = %s
                            """, (uploaded_key, page_id))
                            conn.commit()
                            print(f"  Committed r2_object_id={uploaded_key} for page {page_id}")
                            migrated += 1

            print(f"Batch complete: {migrated}/{len(pages)} migrated successfully")
            return migrated

    except Exception as e:
        conn.rollback()
        print(f"Batch failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def count_remaining():
    """Count how many pages still need migration"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM page
            WHERE r2_object_id IS NULL AND image_url IS NOT NULL
        """)
        return cursor.fetchone()[0]
    finally:
        cursor.close()
        conn.close()


def main():
    """Run migration in batches until complete"""
    remaining = count_remaining()
    print(f"Total pages to migrate: {remaining}")

    if remaining == 0:
        print("Nothing to migrate!")
        return

    total_migrated = 0
    batch_num = 0

    while True:
        batch_num += 1
        print(f"\n=== Batch {batch_num} ===")

        migrated = migrate_batch()
        total_migrated += migrated

        if migrated == 0:
            break

        remaining = count_remaining()
        print(f"Progress: {total_migrated} migrated, {remaining} remaining")

        if remaining == 0:
            break

    print(f"\n=== Migration complete ===")
    print(f"Total migrated: {total_migrated}")


if __name__ == "__main__":
    main()
