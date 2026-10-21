/* Estatística anônima do desafio do dia. POST grava um evento no KV (binding KV): o começo e o fim de cada partida,
   sem conta, cookie nem nada que identifique quem jogou. GET com ?key= mostra o resumo por dia e modo
   (?format=json pra máquina, ?test=1 inclui as partidas dos endereços de teste). */
const json = (obj, status) => new Response(JSON.stringify(obj), { status: status || 200, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' } });
const clip = (v, n) => String(v == null ? '' : v).slice(0, n);
const int = (v, max) => Math.max(0, Math.min(max, Math.floor(+v) || 0));
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

export async function onRequestPost({ request, env }) {
  if (!env.KV) return json({ ok: false, reason: 'sem-kv' }, 503);
  let b;
  try { b = await request.json(); } catch (e) { return json({ ok: false, reason: 'json' }, 400); }
  if (!b || (b.ev !== 'start' && b.ev !== 'end') || !/^\d{4}-\d{2}-\d{2}$/.test(b.date)) return json({ ok: false, reason: 'campos' }, 400);
  /* tudo no metadata, que a listagem já devolve: o resumo sai sem ler chave por chave */
  const m = {
    ev: b.ev, date: b.date, day: int(b.day, 99999), hard: !!b.hard, test: !!b.test,
    won: !!b.won, reason: clip(b.reason, 12), n: int(b.n, 20), par: int(b.par, 20),
    played: int(b.played, 99999), streak: int(b.streak, 99999), lang: clip(b.lang, 5),
    country: clip(request.headers.get('cf-ipcountry'), 2), path: clip(b.path, 240),
    t: new Date().toISOString(),
  };
  const key = 'g:' + m.date + ':' + (m.hard ? 'h' : 'n') + ':' + m.ev + ':' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  await env.KV.put(key, '1', { metadata: m });
  return json({ ok: true });
}

async function allEvents(kv) {
  const out = [];
  let cursor;
  do {
    const r = await kv.list({ prefix: 'g:', cursor });
    r.keys.forEach(k => { if (k.metadata) out.push(k.metadata); });
    cursor = r.list_complete ? null : r.cursor;
  } while (cursor);
  return out;
}

function summarize(evs, withTest) {
  const rows = new Map();
  for (const e of evs) {
    if (e.test && !withTest) continue;
    const id = e.date + (e.hard ? 'h' : 'n');
    let r = rows.get(id);
    if (!r) rows.set(id, r = { date: e.date, day: e.day, hard: e.hard, started: 0, finished: 0, won: 0, out: 0, nopair: 0, gaveup: 0, gaveupBlank: 0, newcomers: 0, sumWon: 0, dist: {}, games: [] });
    if (e.ev === 'start') { r.started++; continue; }
    r.finished++;
    if (!e.played) r.newcomers++;
    if (e.won) { r.won++; r.sumWon += e.n; r.dist[e.n] = (r.dist[e.n] || 0) + 1; }
    else if (e.reason === 'gaveup') { r.gaveup++; if (!e.n) r.gaveupBlank++; }
    else if (e.reason === 'r_nopair') r.nopair++;
    else r.out++;
    r.games.push({ won: e.won, reason: e.reason, n: e.n, par: e.par, path: e.path, played: e.played, streak: e.streak, lang: e.lang, country: e.country, t: e.t });
  }
  const list = [...rows.values()].sort((a, b) => (a.date === b.date ? (a.hard ? 1 : -1) : a.date < b.date ? 1 : -1));
  list.forEach(r => {
    /* jogadores = quem cruzou pelo menos uma vez + quem desistiu sem cruzar; abandono = começou e não terminou */
    r.players = r.started + r.gaveupBlank;
    r.abandoned = Math.max(0, r.started - (r.finished - r.gaveupBlank));
    r.games.sort((a, b) => (a.t < b.t ? 1 : -1));
  });
  return list;
}

const pct = (a, b) => (b ? Math.round(100 * a / b) + '%' : '·');

function page(list) {
  const byDate = new Map();
  list.forEach(r => byDate.set(r.date, (byDate.get(r.date) || 0) + r.players));
  const days = [...byDate.keys()].sort().slice(-30);
  const avg = days.length ? (days.reduce((s, d) => s + byDate.get(d), 0) / days.length).toFixed(1) : '0';
  const reasonTxt = g => g.won ? 'ganhou' : g.reason === 'gaveup' ? 'desistiu' : g.reason === 'r_nopair' ? 'sem par' : 'sem cruzamentos';
  const rows = list.map(r => {
    const dist = [3, 4, 5, 6, 7, 8].map(n => r.dist[n] || 0).join(' · ');
    const games = r.games.map(g => '<li>' + esc(reasonTxt(g)) + ' em ' + g.n + ' (mín. ' + g.par + ') · ' + esc(g.path || '·') + ' · ' + (g.played ? g.played + ' dias antes' : 'primeira vez') + ' · ' + esc(g.lang) + ' ' + esc(g.country) + '</li>').join('');
    return '<tr><td>' + esc(r.date) + '</td><td>' + r.day + '</td><td>' + (r.hard ? 'difícil' : 'normal') + '</td><td>' + r.players + '</td><td>' + r.won + ' (' + pct(r.won, r.finished) + ')</td><td>' + r.out + '</td><td>' + r.nopair + '</td><td>' + r.gaveup + '</td><td>' + r.abandoned + '</td><td>' + r.newcomers + '</td><td>' + (r.won ? (r.sumWon / r.won).toFixed(1) : '·') + '</td><td>' + dist + '</td></tr>'
      + '<tr class="g"><td colspan="12"><details><summary>partidas</summary><ul>' + games + '</ul></details></td></tr>';
  }).join('');
  return '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Slime Cross · estatísticas</title>'
    + '<style>body{font:14px system-ui;margin:16px;background:#14121c;color:#eee}table{border-collapse:collapse}td,th{padding:4px 8px;border-bottom:1px solid #333;text-align:right;white-space:nowrap}th{color:#aaa;font-weight:500}td:nth-child(-n+3){text-align:left}.g td{text-align:left;border:0;padding-top:0}summary{color:#888;cursor:pointer}li{margin:2px 0}</style>'
    + '<h1>Slime Cross · desafio do dia</h1><p>Média de jogadores por dia (últimos ' + days.length + ' dias com partida): <b>' + avg + '</b></p>'
    + '<div style="overflow-x:auto"><table><tr><th>data</th><th>nº</th><th>modo</th><th>jogadores</th><th>ganharam</th><th>perderam: cruzamentos</th><th>perderam: sem par</th><th>desistiram</th><th>abandonaram</th><th>primeira vez</th><th>média ao ganhar</th><th>ganhou em 3 · 4 · 5 · 6 · 7 · 8</th></tr>' + rows + '</table></div>';
}

export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  if (!env.KV || !env.ADMIN_KEY || url.searchParams.get('key') !== env.ADMIN_KEY) return json({ ok: false }, 404);
  const list = summarize(await allEvents(env.KV), url.searchParams.get('test') === '1');
  if (url.searchParams.get('format') === 'json') return json({ ok: true, days: list });
  return new Response(page(list), { headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' } });
}
