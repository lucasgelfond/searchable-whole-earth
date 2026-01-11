import { Hono } from "hono";
import Turbopuffer from "@turbopuffer/turbopuffer";
import { getEnv } from "../context";

const NAMESPACE = "searchable-whole-earth-page";

export const warmNamespaceRoute = new Hono();

warmNamespaceRoute.post("/warm-namespace", async (c) => {
	console.log("POST /warm-namespace");
	try {
		const env = getEnv();

		const tpuf = new Turbopuffer({
			apiKey: env.TURBOPUFFER_API_KEY,
			region: env.TURBOPUFFER_REGION,
		});

		const ns = tpuf.namespace(NAMESPACE);
		const result = await ns.hintCacheWarm();

		console.log("  Cache warm result:", result);
		return c.json({ status: result.status, message: result.message });
	} catch (error) {
		console.error("  Warm namespace error:", error);
		return c.json({ error: "Failed to warm namespace cache" }, 500);
	}
});
