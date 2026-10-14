// Starts agent-hq bound to 127.0.0.1 only.
// agent-hq's own serve() calls server.listen(port) with no host, which listens on every interface, and the service has
// no authentication: on a public server its board, memory and messages would be readable by anyone.
// Usage: node start-agent-hq.mjs [path-to-agent-hq]   (PORT env var, default 7700)
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const root = resolve(process.argv[2] || new URL('./agent-hq', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'));
const { createHqServer } = await import(pathToFileURL(resolve(root, 'src/server.js')).href);
const { Boards, Agents } = await import(pathToFileURL(resolve(root, 'src/services.js')).href);

const port = Number(process.env.PORT) || 7700;
const server = createHqServer();
server.listen(port, '127.0.0.1', () => {
  Boards.ensureDefault();
  setInterval(() => { try { Agents.reapStale(Number(process.env.HQ_STALE_MS) || 90_000); } catch {} }, 30_000);
  console.log(`Agent HQ (local only) -> http://127.0.0.1:${port}`);
});
