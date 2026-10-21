/* Sugestões do site. POST grava no KV (binding KV, o mesmo das estatísticas, chaves com fb:); GET com ?key= (ADMIN_KEY) lista as últimas.
   Sem o binding, responde 503 e a página mostra o jeito alternativo de mandar. */
const json = (obj, status) => new Response(JSON.stringify(obj), { status: status || 200, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' } });

export async function onRequestPost({ request, env }) {
  if (!env.KV) return json({ ok: false, reason: 'sem-kv' }, 503);
  let body;
  try { body = await request.json(); } catch (e) { return json({ ok: false, reason: 'json' }, 400); }
  const msg = String(body.msg || '').trim().slice(0, 2000);
  if (msg.length < 3) return json({ ok: false, reason: 'vazio' }, 400);
  const item = {
    t: new Date().toISOString(),
    msg,
    contact: String(body.contact || '').trim().slice(0, 200),
    lang: String(body.lang || '').slice(0, 5),
    page: String(body.page || '').slice(0, 100),
    ua: (request.headers.get('user-agent') || '').slice(0, 120),
    country: request.headers.get('cf-ipcountry') || '',
  };
  const key = 'fb:' + item.t + '-' + Math.random().toString(36).slice(2, 8);
  await env.KV.put(key, JSON.stringify(item));
  return json({ ok: true });
}

export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  if (!env.KV || !env.ADMIN_KEY || url.searchParams.get('key') !== env.ADMIN_KEY) return json({ ok: false }, 404);
  const list = await env.KV.list({ prefix: 'fb:', limit: 200 });
  const items = [];
  for (const k of list.keys.sort((a, b) => (a.name < b.name ? 1 : -1))) {
    const v = await env.KV.get(k.name);
    if (v) items.push(JSON.parse(v));
  }
  return json({ ok: true, items });
}
