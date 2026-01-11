import Together from "together-ai";
import { getEnv } from "../context";

const EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5";

export async function embedQuery(text: string): Promise<number[]> {
	const env = getEnv();
	const together = new Together({ apiKey: env.TOGETHER_API_KEY });
	const response = await together.embeddings.create({
		model: EMBEDDING_MODEL,
		input: text,
	});
	return response.data[0].embedding;
}
