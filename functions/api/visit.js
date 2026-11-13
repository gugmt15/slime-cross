/* Registro de cada visita, no banco D1 (binding DB): uma linha por página aberta, sem conta, cookie nem nada que
   identifique a pessoa. POST grava ou atualiza a linha da visita (o jogo manda de novo quando a página volta a sumir).
   GET com ?key= (ADMIN_KEY) mostra o resumo dos últimos 30 dias (?test=1 inclui os endereços de teste, ?days=N muda o período). */
const json = (obj, status) => new Response(JSON.stringify(obj), { status: status || 200, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' } });
const clip = (v, n) => String(v == null ? '' : v).slice(0, n);
const int = (v, min, max) => Math.max(min, Math.min(max, Math.floor(+v) || 0));
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const arr = (v, n) => (Array.isArray(v) ? v.slice(0, n) : []);

const SCHEMA = 'CREATE TABLE IF NOT EXISTS visits (id TEXT PRIMARY KEY, t TEXT, day TEXT, test INTEGER, via TEXT, origem TEXT, '
  + 'first_days INTEGER, played_days INTEGER, lang TEXT, country TEXT, device TEXT, w INTEGER, secs INTEGER, data TEXT)';

export async function onRequestPost({ request, env }) {
  if (!env.DB) return json({ ok: false, reason: 'sem-db' }, 503);
  let b;
  try { b = JSON.parse(await request.text()); } catch (e) { return json({ ok: false, reason: 'json' }, 400); }
  if (!b || !/^[a-z0-9-]{8,40}$/i.test(b.id || '') || !/^\d{4}-\d{2}-\d{2}$/.test(b.day || '')) return json({ ok: false, reason: 'campos' }, 400);
  /* só os campos conhecidos, cortados: nada de texto livre de quem mandou */
  const data = {
    views: arr(b.views, 40).map(v => clip(v, 16)),
    tut: int(b.tut, 0, 20), tutDone: !!b.tutDone,
    games: arr(b.games, 40).map(g => ({ m: clip(g && g.m, 6), h: !!(g && g.h), k: clip(g && g.k, 12), r: clip(g && g.r, 8),
      n: int(g && g.n, 0, 30), p: int(g && g.p, 0, 30), s: int(g && g.s, 0, 86400), st: int(g && g.st, 0, 3) })),
    share: arr(b.share, 10).map(v => clip(v, 6)),
    coffee: arr(b.coffee, 10).map(v => clip(v, 6)),
    help: int(b.help, 0, 999),
    err: arr(b.err, 5).map(v => clip(v, 140)),
  };
  const row = [clip(b.id, 40), clip(b.t, 30), clip(b.day, 10), b.test ? 1 : 0, clip(b.via, 30), clip(b.origem, 30),
    int(b.first_days, -1, 100000), int(b.played_days, 0, 100000), clip(b.lang, 5), clip(request.headers.get('cf-ipcountry'), 2),
    clip(b.device, 4), int(b.w, 0, 10000), int(b.secs, 0, 86400), JSON.stringify(data)];
  const put = () => env.DB.prepare('INSERT OR REPLACE INTO visits (id, t, day, test, via, origem, first_days, played_days, lang, country, device, w, secs, data) '
    + 'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)').bind(...row).run();
  try { await put(); }
  catch (e) {
    if (!/no such table/i.test(String(e && e.message || e))) throw e;
    await env.DB.prepare(SCHEMA).run();
    await put();
  }
  return json({ ok: true });
}

const pct = (a, b) => (b ? Math.round(100 * a / b) + '%' : '·');
const count = (list, f) => { const o = {}; list.forEach(x => { const k = f(x); if (k != null && k !== '') o[k] = (o[k] || 0) + 1; }); return o; };
const top = (o, n) => Object.keys(o).sort((a, b) => o[b] - o[a]).slice(0, n || 99).map(k => esc(k) + ' ' + o[k]).join(' · ') || '·';
const median = a => { if (!a.length) return 0; const s = a.slice().sort((x, y) => x - y); return s[Math.floor(s.length / 2)]; };
const mins = s => (s >= 60 ? Math.floor(s / 60) + 'min ' + (s % 60) + 's' : s + 's');

function page(rows, nDays) {
  const V = rows.map(r => Object.assign({}, r, { d: JSON.parse(r.data || '{}') }));
  const played = v => (v.d.games || []).length > 0;
  const total = V.length;
  const P = V.filter(played);
  const newV = V.filter(v => v.first_days === 0), back = V.filter(v => v.first_days > 0);
  const tutStart = V.filter(v => v.d.tut > 0), tutDone = V.filter(v => v.d.tutDone);
  const games = [].concat(...V.map(v => v.d.games || []));
  const shares = V.filter(v => (v.d.share || []).length), coffee = [].concat(...V.map(v => v.d.coffee || []));
  const line = (label, value) => '<tr><th>' + label + '</th><td>' + value + '</td></tr>';
  /* por origem: a da visita (via) diz o que trouxe hoje; a da primeira vez (origem) diz qual canal traz gente que volta */
  const vias = Object.keys(count(V, v => v.via || '?'));
  const byVia = vias.map(k => { const g = V.filter(v => (v.via || '?') === k); return { k, n: g.length, p: g.filter(played).length, s: g.filter(v => (v.d.share || []).length).length, t: median(g.map(v => v.secs)) }; })
    .sort((a, b) => b.n - a.n)
    .map(o => '<tr><td>' + esc(o.k) + '</td><td>' + o.n + '</td><td>' + pct(o.p, o.n) + '</td><td>' + pct(o.s, o.n) + '</td><td>' + mins(o.t) + '</td></tr>').join('');
  const tutSteps = count(tutStart.filter(v => !v.d.tutDone), v => 'parou no ' + v.d.tut);
  const results = count(games, g => g.m + (g.h ? ' difícil' : '') + ': ' + (g.r === 'won' ? 'ganhou' : g.r === 'gaveup' ? 'desistiu' : 'perdeu'));
  const errs = [].concat(...V.map(v => (v.d.err || []).map(e => v.day + ' ' + v.device + ' ' + e))).slice(0, 20);
  return '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Slime Cross · visitas</title>'
    + '<style>body{font:14px system-ui;margin:16px;background:#14121c;color:#eee;max-width:900px}table{border-collapse:collapse;margin:8px 0 20px}td,th{padding:4px 10px;border-bottom:1px solid #333;text-align:left;vertical-align:top}th{color:#aaa;font-weight:500}h2{font-size:1.1rem;margin-top:24px}li{margin:2px 0}</style>'
    + '<h1>Slime Cross · visitas dos últimos ' + nDays + ' dias</h1>'
    + '<h2>Quem chega</h2><table>'
    + line('visitas', total)
    + line('primeira vez · voltando · de antes do registro', newV.length + ' · ' + back.length + ' · ' + V.filter(v => v.first_days < 0).length)
    + line('celular · computador', V.filter(v => v.device === 'cel').length + ' · ' + V.filter(v => v.device === 'pc').length)
    + line('países', top(count(V, v => v.country), 8))
    + line('idiomas', top(count(V, v => v.lang)))
    + '</table>'
    + '<h2>O que fazem</h2><table>'
    + line('jogaram pelo menos uma partida', P.length + ' (' + pct(P.length, total) + ')')
    + line('novatos que jogaram', pct(newV.filter(played).length, newV.length))
    + line('telas abertas (visitas)', top(count([].concat(...V.map(v => [...new Set(v.d.views || [])])), x => x)))
    + line('tutorial: começaram · terminaram', tutStart.length + ' · ' + tutDone.length + ' (' + pct(tutDone.length, tutStart.length) + ')')
    + line('tutorial: onde quem não terminou parou', top(tutSteps))
    + line('partidas', top(results))
    + line('abriram o "?"', V.filter(v => v.d.help > 0).length)
    + '</table>'
    + '<h2>Se gostaram</h2><table>'
    + line('tempo na página (mediana) · de quem jogou', mins(median(V.map(v => v.secs))) + ' · ' + mins(median(P.map(v => v.secs))))
    + line('compartilharam', shares.length + ' (' + pct(shares.length, P.length) + ' de quem jogou)')
    + line('cliques no café', coffee.length + (coffee.length ? ' (' + top(count(coffee, x => x)) + ')' : ''))
    + line('voltaram, pela origem da primeira vez', top(count(back, v => v.origem || '?')))
    + '</table>'
    + '<h2>Por origem desta visita</h2><table><tr><th>origem</th><th>visitas</th><th>jogaram</th><th>compartilharam</th><th>tempo (mediana)</th></tr>' + byVia + '</table>'
    + '<h2>Erros</h2>' + (errs.length ? '<ul>' + errs.map(e => '<li>' + esc(e) + '</li>').join('') + '</ul>' : '<p>Nenhum.</p>');
}

export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  if (!env.DB || !env.ADMIN_KEY || url.searchParams.get('key') !== env.ADMIN_KEY) return json({ ok: false }, 404);
  const nDays = int(url.searchParams.get('days') || 30, 1, 365);
  const since = new Date(Date.now() - nDays * 864e5).toISOString().slice(0, 10);
  const withTest = url.searchParams.get('test') === '1';
  let rows = [];
  try {
    rows = (await env.DB.prepare('SELECT * FROM visits WHERE day >= ?' + (withTest ? '' : ' AND test = 0') + ' ORDER BY t DESC LIMIT 20000').bind(since).all()).results || [];
  } catch (e) { if (!/no such table/i.test(String(e && e.message || e))) throw e; }
  if (url.searchParams.get('format') === 'json') return json({ ok: true, visits: rows });
  return new Response(page(rows, nDays), { headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' } });
}
