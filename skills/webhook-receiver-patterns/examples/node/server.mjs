// Starts the example receiver: WEBHOOK_SECRET=<test secret> node server.mjs
// The queue here only logs; replace it with your real queue or job table.
import { createApp } from "./app.mjs";

const app = createApp({
  secret: process.env.WEBHOOK_SECRET,
  enqueue: async (event) => console.log(`queued ${event.id}`),
});
const port = Number(process.env.PORT ?? 3000);
app.listen(port, () => console.log(`listening on ${port}`));
