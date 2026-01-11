import os
import psycopg2
from dotenv import load_dotenv
from together import Together
from transformers import AutoTokenizer
import time

load_dotenv()

BATCH_SIZE = 500
MODEL = "BAAI/bge-base-en-v1.5"
MAX_TOKENS = 512

# Load the BGE tokenizer once at module level
print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL)


def get_db_connection():
    """Create a database connection"""
    return psycopg2.connect(os.getenv('DB_URL'))


def truncate_text(text, max_tokens=MAX_TOKENS):
    """Truncate text to fit within token limit using the actual tokenizer"""
    if not text:
        return ""

    # Tokenize and truncate
    tokens = tokenizer.encode(text, add_special_tokens=True, truncation=True, max_length=max_tokens)

    # Decode back to text
    return tokenizer.decode(tokens, skip_special_tokens=True)


def fetch_pages_batch(cursor, batch_size=BATCH_SIZE):
    """Fetch a batch of pages that need embeddings"""
    cursor.execute("""
        SELECT id, ocr_result
        FROM page
        WHERE bge_embedding IS NULL AND ocr_result IS NOT NULL
        LIMIT %s
    """, (batch_size,))
    return cursor.fetchall()


def get_embeddings_batch(client, texts):
    """Get embeddings for a batch of texts from Together AI"""
    response = client.embeddings.create(
        model=MODEL,
        input=texts
    )

    # Extract embeddings in order
    embeddings = [None] * len(texts)
    for item in response.data:
        embeddings[item.index] = item.embedding

    return embeddings


def process_batch(client):
    """Process one batch of embeddings"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        pages = fetch_pages_batch(cursor)

        if not pages:
            print("No more pages to process!")
            return 0

        print(f"Processing batch of {len(pages)} pages...")

        # Prepare texts for embedding
        page_ids = []
        texts = []
        for page_id, ocr_result in pages:
            page_ids.append(page_id)
            texts.append(truncate_text(ocr_result))

        # Get embeddings from Together AI
        print("  Calling Together AI API...")
        embeddings = get_embeddings_batch(client, texts)

        # Update database with embeddings
        updated = 0
        for page_id, embedding in zip(page_ids, embeddings):
            if embedding:
                cursor.execute("""
                    UPDATE page
                    SET bge_embedding = %s
                    WHERE id = %s
                """, (embedding, page_id))
                updated += 1

        conn.commit()
        print(f"  Updated {updated} rows with embeddings")
        return updated

    except Exception as e:
        conn.rollback()
        print(f"Batch failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def count_remaining():
    """Count how many pages still need embeddings"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM page
            WHERE bge_embedding IS NULL AND ocr_result IS NOT NULL
        """)
        return cursor.fetchone()[0]
    finally:
        cursor.close()
        conn.close()


def main():
    """Run embedding generation in batches until complete"""
    api_key = os.getenv('TOGETHER_API_KEY')
    if not api_key:
        print("Error: TOGETHER_API_KEY not set in environment")
        return

    client = Together(api_key=api_key)

    remaining = count_remaining()
    print(f"Total pages to process: {remaining}")

    if remaining == 0:
        print("Nothing to process!")
        return

    total_processed = 0
    batch_num = 0

    while True:
        batch_num += 1
        print(f"\n=== Batch {batch_num} ===")

        try:
            processed = process_batch(client)
            total_processed += processed

            if processed == 0:
                break

            remaining = count_remaining()
            print(f"Progress: {total_processed} processed, {remaining} remaining")

            if remaining == 0:
                break

            # Small delay to avoid rate limiting
            time.sleep(0.5)

        except Exception as e:
            print(f"Error in batch {batch_num}: {e}")
            print("Waiting 5 seconds before retry...")
            time.sleep(5)

    print(f"\n=== Embedding generation complete ===")
    print(f"Total processed: {total_processed}")


if __name__ == "__main__":
    main()
