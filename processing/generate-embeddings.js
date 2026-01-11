import { createClient } from '@supabase/supabase-js';
import { pipeline } from '@huggingface/transformers';
import * as dotenv from 'dotenv';

// Load environment variables
dotenv.config();

// Initialize Supabase client
const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_KEY;
const supabase = createClient(supabaseUrl, supabaseKey);

(async () => {
	// Initialize the pipeline
	const classifier = await pipeline('feature-extraction', 'Supabase/gte-small', {
		dtype: 'fp32',
		device: 'cpu'
	});

	// Get rows from page table that have OCR results but no embeddings yet
	const { data: rows, error } = await supabase
		.from('page')
		.select('id, ocr_result')
		.not('ocr_result', 'is', null)
		.is('embedding', null);

	if (error) {
		console.error('Error fetching rows:', error);
		return;
	}

	console.log(`Processing ${rows.length} rows...`);

	// Process each row
	for (const row of rows) {
		try {
			console.log(`Processing row ${row.id}...`);

			// Generate embedding
			const output = await classifier(row.ocr_result, {
				pooling: 'mean',
				normalize: true
			});

			// Convert to array
			const embedding = Array.from(output.data);

			// Update the row with embedding
			const { error: updateError } = await supabase
				.from('page')
				.update({ embedding })
				.eq('id', row.id);

			if (updateError) {
				throw updateError;
			}

			console.log(`Successfully processed row ${row.id}`);
		} catch (error) {
			console.error(`Error processing row ${row.id}:`, error);
		}
	}

	console.log('Finished processing all rows');
})().catch(console.error);
