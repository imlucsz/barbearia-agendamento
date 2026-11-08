import http from 'node:http';
import path from 'node:path';
import { createReadStream } from 'node:fs';
import { stat } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

// A static server in the runner process: no backend, DB, child process or dependency.
export default async function setup() {
  const root = fileURLToPath(new URL('../', import.meta.url));
  const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.mjs': 'text/javascript', '.png': 'image/png', '.webp': 'image/webp', '.gif': 'image/gif', '.mp3': 'audio/mpeg', '.webm': 'video/webm', '.mp4': 'video/mp4' };
  const server = http.createServer(async (request, response) => {
    let filename;
    try {
      filename = path.resolve(root, `.${decodeURIComponent(new URL(request.url, 'http://localhost').pathname)}`);
    } catch { response.writeHead(400).end(); return; }
    if (!filename.startsWith(root)) { response.writeHead(403).end(); return; }
    try {
      const info = await stat(filename);
      if (!info.isFile()) { response.writeHead(404).end(); return; }
      const contentType = types[path.extname(filename)] || 'application/octet-stream';
      const commonHeaders = { 'Accept-Ranges': 'bytes', 'Content-Type': contentType };
      if (request.method === 'HEAD') {
        response.writeHead(200, { ...commonHeaders, 'Content-Length': info.size }).end();
        return;
      }
      const range = request.headers.range;
      if (range) {
        const match = /^bytes=(\d*)-(\d*)$/.exec(range);
        if (!match || (!match[1] && !match[2])) {
          response.writeHead(416, { 'Content-Range': `bytes */${info.size}` }).end();
          return;
        }
        const start = match[1] ? Number(match[1]) : Math.max(0, info.size - Number(match[2]));
        const end = match[2] && match[1] ? Math.min(Number(match[2]), info.size - 1) : info.size - 1;
        if (start >= info.size || end < start) {
          response.writeHead(416, { 'Content-Range': `bytes */${info.size}` }).end();
          return;
        }
        response.writeHead(206, { ...commonHeaders, 'Content-Length': end - start + 1, 'Content-Range': `bytes ${start}-${end}/${info.size}` });
        createReadStream(filename, { start, end }).pipe(response);
        return;
      }
      response.writeHead(200, { ...commonHeaders, 'Content-Length': info.size });
      createReadStream(filename).pipe(response);
    } catch { if (!response.headersSent) response.writeHead(404).end(); else response.destroy(); }
  });
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(4186, '127.0.0.1', resolve);
  });
  return async () => {
    server.closeAllConnections();
    await new Promise(resolve => server.close(resolve));
  };
}
