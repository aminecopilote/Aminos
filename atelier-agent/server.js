// Atelier agent: question/answer + file upload, with Claude / OpenAI / Gemini models and SKILL.md skills.
const http = require('http'), fs = require('fs'), path = require('path');

// ---- config (.env loader, no dependencies) ----
try {
  for (const l of fs.readFileSync(path.join(__dirname, '.env'), 'utf8').split(/\r?\n/)) {
    const m = l.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$/);
    if (m && !l.trim().startsWith('#') && m[2] && !(m[1] in process.env)) process.env[m[1]] = m[2].replace(/^["']|["']$/g, '');
  }
} catch {}
const E = process.env;
const PORT = +E.PORT || 3000;
const WORK = path.join(__dirname, 'workspace', 'files');
fs.mkdirSync(WORK, { recursive: true });
const MAX_FILE = 5 * 1024 * 1024, MAX_CTX_PER_FILE = 30000;

const PROVIDERS = {
  claude: { key: 'ANTHROPIC_API_KEY', model: E.ANTHROPIC_MODEL || 'claude-sonnet-5-5' },
  openai: { key: 'OPENAI_API_KEY', model: E.OPENAI_MODEL || 'gpt-4o' },
  gemini: { key: 'GEMINI_API_KEY', model: E.GEMINI_MODEL || 'gemini-2.5-flash' },
};

// ---- skills ----
function loadSkills() {
  const dirs = (E.SKILLS_DIRS || '../.claude/skills').split(path.delimiter === ';' ? /;/ : /[;:](?![\\/])/).filter(Boolean);
  const out = new Map();
  for (const d of dirs) {
    const root = path.resolve(__dirname, d);
    let names = []; try { names = fs.readdirSync(root); } catch { continue; }
    for (const n of names) {
      const f = path.join(root, n, 'SKILL.md');
      if (!fs.existsSync(f)) continue;
      const t = fs.readFileSync(f, 'utf8');
      const fm = (t.match(/^---\r?\n([\s\S]*?)\r?\n---/) || [])[1] || '';
      const desc = ((fm.match(/^description:\s*(.*)$/m) || [])[1] || '').replace(/^["']|["']$/g, '');
      out.set(n, { name: n, desc, file: f, body: t.replace(/^---[\s\S]*?---\r?\n/, '') });
    }
  }
  return [...out.values()];
}
let SKILLS = loadSkills();
function pickSkills(q, max = 3) {
  const words = new Set(q.toLowerCase().match(/[a-zà-ÿ0-9]{4,}/g) || []);
  return SKILLS.map(s => {
    let sc = 0;
    const hay = (s.name + ' ' + s.desc).toLowerCase();
    if (q.toLowerCase().includes(s.name.toLowerCase())) sc += 10;
    for (const w of words) if (hay.includes(w)) sc++;
    return { s, sc };
  }).filter(x => x.sc >= 3).sort((a, b) => b.sc - a.sc).slice(0, max).map(x => x.s);
}

// ---- files ----
const safeName = n => path.basename(String(n)).replace(/[^\w.\- ()]/g, '_').slice(0, 120) || 'file';
const listFiles = () => fs.readdirSync(WORK).map(n => ({ name: n, size: fs.statSync(path.join(WORK, n)).size }));
function fileContext(names) {
  let ctx = '';
  for (const n of names) {
    const p = path.join(WORK, safeName(n));
    if (!fs.existsSync(p)) continue;
    const buf = fs.readFileSync(p);
    if (buf.includes(0)) { ctx += `\n[File ${n}: binary, ${buf.length} bytes, not shown]\n`; continue; }
    const txt = buf.toString('utf8');
    ctx += `\n<file name="${n}">\n${txt.slice(0, MAX_CTX_PER_FILE)}${txt.length > MAX_CTX_PER_FILE ? '\n…[truncated]' : ''}\n</file>\n`;
  }
  return ctx;
}

// ---- model calls ----
async function post(url, headers, body) {
  const r = await fetch(url, { method: 'POST', headers: { 'content-type': 'application/json', ...headers }, body: JSON.stringify(body) });
  const t = await r.text(); let j; try { j = JSON.parse(t); } catch { j = { raw: t }; }
  if (!r.ok) throw new Error(`${r.status} ${(j.error && (j.error.message || j.error)) || t.slice(0, 300)}`);
  return j;
}
async function callModel(provider, system, messages) {
  const p = PROVIDERS[provider]; if (!p) throw new Error('Unknown provider: ' + provider);
  const key = E[p.key]; if (!key) throw new Error(`Missing ${p.key} in .env`);
  if (provider === 'claude') {
    const j = await post('https://api.anthropic.com/v1/messages', { 'x-api-key': key, 'anthropic-version': '2023-06-01' },
      { model: p.model, max_tokens: 4096, system, messages });
    return j.content.filter(b => b.type === 'text').map(b => b.text).join('');
  }
  if (provider === 'openai') {
    const j = await post('https://api.openai.com/v1/chat/completions', { authorization: 'Bearer ' + key },
      { model: p.model, messages: [{ role: 'system', content: system }, ...messages] });
    return j.choices[0].message.content;
  }
  const j = await post(`https://generativelanguage.googleapis.com/v1beta/models/${p.model}:generateContent`, { 'x-goog-api-key': key },
    { systemInstruction: { parts: [{ text: system }] }, contents: messages.map(m => ({ role: m.role === 'assistant' ? 'model' : 'user', parts: [{ text: m.content }] })) });
  return (j.candidates?.[0]?.content?.parts || []).map(x => x.text || '').join('');
}
function buildSystem(question, files) {
  const used = pickSkills(question);
  let s = 'You are the Atelier assistant. Answer questions clearly, in the language of the user. ' +
    'You can read the files the user attached (shown below). Follow the active skills when relevant.\n';
  if (used.length) s += '\n# Active skills\n' + used.map(k => `## ${k.name}\n${k.body.slice(0, 8000)}`).join('\n');
  const fc = fileContext(files || []); if (fc) s += '\n# Attached files\n' + fc;
  return { system: s, skills: used.map(k => k.name) };
}

// ---- http ----
const send = (res, code, obj) => { res.writeHead(code, { 'content-type': 'application/json' }); res.end(JSON.stringify(obj)); };
const readBody = req => new Promise((ok, ko) => { let b = '', n = 0; req.on('data', c => { n += c.length; if (n > MAX_FILE * 1.5) { ko(new Error('too large')); req.destroy(); } else b += c; }); req.on('end', () => ok(b)); req.on('error', ko); });

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, 'http://x');
    if (req.method === 'GET' && (url.pathname === '/' || url.pathname === '/index.html')) { res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' }); return res.end(fs.readFileSync(path.join(__dirname, 'public', 'index.html'))); }
    if (req.method === 'GET' && url.pathname === '/api/status') return send(res, 200, { providers: Object.fromEntries(Object.entries(PROVIDERS).map(([k, v]) => [k, { model: v.model, configured: !!E[v.key] }])), skills: SKILLS.length, files: listFiles() });
    if (req.method === 'GET' && url.pathname === '/api/files') return send(res, 200, listFiles());
    if (req.method === 'POST' && url.pathname === '/api/files') {
      const { name, contentBase64 } = JSON.parse(await readBody(req));
      const buf = Buffer.from(contentBase64 || '', 'base64');
      if (buf.length > MAX_FILE) return send(res, 413, { error: 'File over 5 MB' });
      fs.writeFileSync(path.join(WORK, safeName(name)), buf);
      return send(res, 200, { ok: true, files: listFiles() });
    }
    if (req.method === 'DELETE' && url.pathname === '/api/files') { try { fs.unlinkSync(path.join(WORK, safeName(url.searchParams.get('name')))); } catch {} return send(res, 200, listFiles()); }
    if (req.method === 'POST' && url.pathname === '/api/chat') {
      const { provider = 'claude', messages = [], files = [] } = JSON.parse(await readBody(req));
      const last = [...messages].reverse().find(m => m.role === 'user');
      if (!last) return send(res, 400, { error: 'No user message' });
      const { system, skills } = buildSystem(last.content, files);
      const answer = await callModel(provider, system, messages.map(m => ({ role: m.role, content: String(m.content) })));
      return send(res, 200, { answer, skills });
    }
    send(res, 404, { error: 'not found' });
  } catch (e) { send(res, 500, { error: e.message }); }
});
if (require.main === module) server.listen(PORT, () => console.log(`Atelier agent: http://localhost:${PORT}  (skills loaded: ${SKILLS.length})`));
module.exports = { pickSkills, buildSystem, loadSkills, server, PROVIDERS };
