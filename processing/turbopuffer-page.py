import os
import json
import psycopg2
from dotenv import load_dotenv
import turbopuffer
from datetime import datetime, timezone
import time

load_dotenv()

BATCH_SIZE = 500
NAMESPACE = "searchable-whole-earth-page"
REGION = "aws-us-east-1"


def get_db_connection():
    """Create a database connection"""
    return psycopg2.connect(os.getenv('DB_URL'))


def fetch_pages_batch(cursor, batch_size=BATCH_SIZE):
    """Fetch a batch of pages that need to be uploaded to Turbopuffer"""
    cursor.execute("""
        SELECT id, parent_issue_id, page_number, ocr_result, r2_object_id, bge_embedding
        FROM page
        WHERE bge_embedding IS NOT NULL
          AND r2_object_id IS NOT NULL
          AND uploaded_to_turbopuffer_at IS NULL
        LIMIT %s
    """, (batch_size,))
    return cursor.fetchall()


def upsert_to_turbopuffer(ns, pages):
    """Upsert a batch of pages to Turbopuffer"""
    rows = []
    for page_id, parent_issue_id, page_number, ocr_result, r2_object_id, bge_embedding in pages:
        # Cast page_number to int (handle None case)
        page_num_int = None
        if page_number:
            try:
                page_num_int = int(page_number)
            except ValueError:
                page_num_int = None

        # Parse embedding from JSON string if needed
        if isinstance(bge_embedding, str):
            vector = json.loads(bge_embedding)
        else:
            vector = list(bge_embedding)

        row = {
            'id': str(page_id),
            'vector': vector,
            'parent_issue_id': str(parent_issue_id) if parent_issue_id else None,
            'page_number': page_num_int,
            'ocr_result': ocr_result or '',
            'r2_object_id': r2_object_id,
        }
        rows.append(row)

    # Upsert to Turbopuffer with schema
    result = ns.write(
        upsert_rows=rows,
        distance_metric='cosine_distance',
        schema={
            'id': 'uuid',
            'parent_issue_id': 'uuid',
            'page_number': 'int',
            'ocr_result': {
                'type': 'string',
                'full_text_search': {
                    'tokenizer': 'word_v3',
                    'case_sensitive': False,
                    'language': 'english',
                    'stemming': True,
                    'remove_stopwords': True,
                }
            },
            'r2_object_id': 'string',
        }
    )

    return result


def update_uploaded_timestamps(cursor, conn, page_ids):
    """Update the uploaded_to_turbopuffer_at timestamp for processed pages"""
    now = datetime.now(timezone.utc)

    cursor.execute("""
        UPDATE page
        SET uploaded_to_turbopuffer_at = %s
        WHERE id = ANY(%s::uuid[])
    """, (now, [str(pid) for pid in page_ids]))

    conn.commit()


def process_batch(tpuf):
    """Process one batch of pages"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        pages = fetch_pages_batch(cursor)

        if not pages:
            print("No more pages to process!")
            return 0

        print(f"Processing batch of {len(pages)} pages...")

        # Get namespace
        ns = tpuf.namespace(NAMESPACE)

        # Upsert to Turbopuffer
        print("  Upserting to Turbopuffer...")
        result = upsert_to_turbopuffer(ns, pages)
        print(f"  Turbopuffer response: {result.rows_affected} rows affected")

        # Extract page IDs and update timestamps
        page_ids = [page[0] for page in pages]
        print(f"  Updating {len(page_ids)} timestamps in Supabase...")
        update_uploaded_timestamps(cursor, conn, page_ids)

        print(f"  Batch complete: {len(pages)} pages uploaded")
        return len(pages)

    except Exception as e:
        conn.rollback()
        print(f"Batch failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def count_remaining():
    """Count how many pages still need to be uploaded"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM page
            WHERE bge_embedding IS NOT NULL
              AND r2_object_id IS NOT NULL
              AND uploaded_to_turbopuffer_at IS NULL
        """)
        return cursor.fetchone()[0]
    finally:
        cursor.close()
        conn.close()


def main():
    """Run Turbopuffer upload in batches until complete"""
    api_key = os.getenv('TURBOPUFFER_API_KEY')
    if not api_key:
        print("Error: TURBOPUFFER_API_KEY not set in environment")
        return

    tpuf = turbopuffer.Turbopuffer(
        api_key=api_key,
        region=REGION,
    )

    remaining = count_remaining()
    print(f"Total pages to upload: {remaining}")

    if remaining == 0:
        print("Nothing to upload!")
        return

    total_processed = 0
    batch_num = 0

    while True:
        batch_num += 1
        print(f"\n=== Batch {batch_num} ===")

        try:
            processed = process_batch(tpuf)
            total_processed += processed

            if processed == 0:
                break

            remaining = count_remaining()
            print(f"Progress: {total_processed} processed, {remaining} remaining")

            if remaining == 0:
                break

            # Small delay between batches
            time.sleep(0.5)

        except Exception as e:
            print(f"Error in batch {batch_num}: {e}")
            print("Waiting 5 seconds before retry...")
            time.sleep(5)

    print(f"\n=== Turbopuffer upload complete ===")
    print(f"Total processed: {total_processed}")


if __name__ == "__main__":
    main()
