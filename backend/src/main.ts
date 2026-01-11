import { Hono } from "hono";
import { cors } from "hono/cors";
import type { Env } from "./env";
import { runWithEnv } from "./context";
import { searchRoute } from "./routes/search";
import { healthRoute } from "./routes/health";
import { pagesRoute } from "./routes/pages";

const app = new Hono<{ Bindings: Env }>();

app.use("*", cors());

app.use("*", async (c, next) => {
	return runWithEnv(c.env, () => next());
});

app.route("/", healthRoute);
app.route("/", searchRoute);
app.route("/", pagesRoute);

export default app;
