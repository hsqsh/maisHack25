/* eslint-disable no-console */
const express = require('express');
const http = require('http');
const path = require('path');
const cors = require('cors');
const morgan = require('morgan');
const { WebSocketServer } = require('ws');
const url = require('url');

const app = express();
app.use(cors());
app.use(express.json({ limit: process.env.MAX_BODY || '5mb' }));
app.use(morgan('dev'));

const server = http.createServer(app);

// sessionId -> Set<WebSocket>
const sessions = new Map();
// sessionId -> last push timestamp (防抖)
const lastPushAt = new Map();

const wss = new WebSocketServer({ server, path: '/ws' });
wss.on('connection', (ws, req) => {
  const { query } = url.parse(req.url, true);
  const sessionId = query.session;
  const role = query.role;

  if (!sessionId || role !== 'mobile') {
    ws.close(1008, 'Invalid params');
    return;
  }

  if (!sessions.has(sessionId)) sessions.set(sessionId, new Set());
  sessions.get(sessionId).add(ws);
  console.log(`[WS] mobile connected: session=${sessionId}, total=${sessions.get(sessionId).size}`);

  ws.on('close', () => {
    const set = sessions.get(sessionId);
    if (set) {
      set.delete(ws);
      if (set.size === 0) sessions.delete(sessionId);
    }
    console.log(`[WS] mobile disconnected: session=${sessionId}`);
  });
});

// 健康检查
app.get('/health', (_req, res) => res.json({ ok: true }));

// Laptop 通知命中：POST /notify { session, type, payload }
app.post('/notify', (req, res) => {
  const { session, type = 'found', payload = {} } = req.body || {};
  if (!session) return res.status(400).json({ error: 'session required' });

  // 简单防抖：1秒
  const now = Date.now();
  const last = lastPushAt.get(session) || 0;
  const cooldown = parseInt(process.env.PUSH_COOLDOWN_MS || '1000', 10);
  if (now - last < cooldown) {
    return res.json({ delivered: 0, throttled: true });
  }
  lastPushAt.set(session, now);

  const set = sessions.get(session);
  if (!set || set.size === 0) return res.json({ delivered: 0 });

  const msg = JSON.stringify({ type, payload, ts: now });
  let delivered = 0;
  for (const ws of set) {
    if (ws.readyState === ws.OPEN) {
      ws.send(msg);
      delivered++;
    }
  }
  return res.json({ delivered });
});

// 静态文件：/laptop 与 /mobile（如果目录存在）
app.use('/laptop', express.static(path.join(__dirname, '../frontend-laptop')));
app.use('/mobile', express.static(path.join(__dirname, '../frontend-mobile')));

const PORT = parseInt(process.env.PORT || '3000', 10);
server.listen(PORT, () => console.log(`Node server on http://localhost:${PORT}`));
