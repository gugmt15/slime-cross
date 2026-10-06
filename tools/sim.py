"""Simulação de jogadores no Slime Cross.

Reproduz as regras do jogo (genes dominante/recessivo, ninhada de 4 nas proporções exatas,
permutação por gene fixa por par, gerador com modo justo e solucionador de 2 ou 3 cruzamentos)
e testa três jogadores:
  - aleatorio: cruza pares válidos ao acaso
  - intuitivo: conhece as regras e raciocina por aparência e parentesco, sem fazer conta
  - esperto: mantém crença sobre os genes escondidos (amostragem de mundos possíveis) e
    escolhe o cruzamento com maior chance de fazer o alvo, olhando um passo à frente
"""
import random, itertools, math, sys, time
from collections import Counter

P_DOM = 0.55


class Puzzle:
    def __init__(self, ngenes, rng, hard=False):
        self.n = ngenes
        self.rng = rng
        self.hard = hard

    def gen_geno(self):
        return tuple((int(self.rng.random() < P_DOM), int(self.rng.random() < P_DOM)) for _ in range(self.n))


def phen(g):
    return tuple(a | b for a, b in g)


def make_puzzle(n, seed, hard=False, maxd=3, minpar=2):
    rng = random.Random(seed)
    for attempt in range(20000):
        starters = [tuple((int(rng.random() < P_DOM), int(rng.random() < P_DOM)) for _ in range(n)) for _ in range(3)]
        tg = tuple((int(rng.random() < P_DOM), int(rng.random() < P_DOM)) for _ in range(n))
        target = phen(tg)
        if all(target):  # precisa ter ao menos um traço recessivo
            continue
        if any(phen(s) == target for s in starters):
            continue
        if not hard:
            ok = True
            for i in range(n):
                if not any(phen(s)[i] == target[i] for s in starters):
                    ok = False
            if not ok:
                continue
        P = World(n, starters, target, seed * 7919 + attempt)
        d = P.solve(maxd)
        if d and d >= minpar:
            P.par = d
            return P
    return None


class World:
    """A verdade de um desafio: genes reais e ninhadas determinísticas por par."""

    def __init__(self, n, starters, target, key):
        self.n = n
        self.geno = {'A': starters[0], 'B': starters[1], 'C': starters[2]}
        self.parents = {}
        self.target = target
        self.key = key
        self.lit = {}

    def litter(self, a, b):
        x, y = (a, b) if a < b else (b, a)
        k = (x, y)
        if k in self.lit:
            return self.lit[k]
        gx, gy = self.geno[x], self.geno[y]
        kids = [[None] * self.n for _ in range(4)]
        for i in range(self.n):
            pun = [(gx[i][0], gy[i][0]), (gx[i][0], gy[i][1]), (gx[i][1], gy[i][0]), (gx[i][1], gy[i][1])]
            r = random.Random(hash((self.key, x, y, i)))
            perm = [0, 1, 2, 3]
            r.shuffle(perm)
            for kk in range(4):
                kids[kk][i] = pun[perm[kk]]
        ids = []
        for kk in range(4):
            kid = '(' + x + 'x' + y + ')' + str(kk)
            self.geno[kid] = tuple(kids[kk])
            self.parents[kid] = (x, y)
            ids.append(kid)
        self.lit[k] = ids
        return ids

    def solve(self, maxd):
        tgt = self.target

        def dfs(pop, done, d):
            for i in range(len(pop)):
                for j in range(i + 1, len(pop)):
                    a, b = pop[i], pop[j]
                    pk = (min(a, b), max(a, b))
                    if pk in done:
                        continue
                    kids = self.litter(a, b)
                    if any(phen(self.geno[k]) == tgt for k in kids):
                        return 1
                    if d > 1:
                        r = dfs(pop + kids, done | {pk}, d - 1)
                        if r:
                            return 1 + r
            return 0

        for d in range(1, maxd + 1):
            if dfs(['A', 'B', 'C'], frozenset(), d):
                return d
        return None


# ---------------- jogo visto pelo jogador ----------------
class Game:
    def __init__(self, W, maxc):
        self.W = W
        self.maxc = maxc
        self.pop = ['A', 'B', 'C']
        self.crosses = []  # (a, b, kids)
        self.done = set()
        self.won = False

    def ph(self, c):
        return phen(self.W.geno[c])

    def pairs(self):
        out = []
        for i in range(len(self.pop)):
            for j in range(i + 1, len(self.pop)):
                a, b = self.pop[i], self.pop[j]
                if (min(a, b), max(a, b)) not in self.done:
                    out.append((a, b))
        return out

    def cross(self, a, b):
        kids = self.W.litter(a, b)
        self.done.add((min(a, b), max(a, b)))
        self.pop += kids
        self.crosses.append((a, b, kids))
        if any(self.ph(k) == self.W.target for k in kids):
            self.won = True


def play(game, chooser):
    while not game.won and len(game.crosses) < game.maxc:
        prs = game.pairs()
        if not prs:
            break
        a, b = chooser(game, prs)
        game.cross(a, b)
    return len(game.crosses) if game.won else None


# ---------------- jogadores ----------------
def chooser_random(rng):
    return lambda g, prs: rng.choice(prs)


def chooser_intuitive(rng):
    """Raciocina por aparência e parentesco. Marca como portador de um recessivo:
    quem mostra o recessivo, quem nasceu de um pai que mostra o recessivo (e não mostra),
    e quem tem irmão que mostrou o recessivo com os dois pais dominantes (palpite)."""

    def status(g, c, i):
        if g.ph(c)[i] == 0:
            return 'rec'
        par = g.W.parents.get(c)
        if par:
            pa, pb = par
            if g.ph(pa)[i] == 0 or g.ph(pb)[i] == 0:
                return 'carrier'
            sibs = g.W.lit[(min(pa, pb), max(pa, pb))]
            if any(g.ph(s)[i] == 0 for s in sibs):
                return 'maybe'
        # pai dominante que teve filho recessivo é portador certo
        for (a, b, kids) in g.crosses:
            if c in (a, b) and any(g.ph(k)[i] == 0 for k in kids):
                return 'carrier'
        return 'unknown'

    val = {'rec': 1.0, 'carrier': 0.5, 'maybe': 0.33, 'unknown': 0.2}

    def choose(g, prs):
        t = g.W.target
        best, bs = [], -1e9
        for a, b in prs:
            s = 0.0
            for i in range(g.W.n):
                if t[i] == 0:
                    pa = val[status(g, a, i)] if g.ph(a)[i] == 0 or status(g, a, i) != 'rec' else 1.0
                    pb = val[status(g, b, i)]
                    pa = val[status(g, a, i)]
                    s += math.log(max(pa * pb, 1e-3))
                else:
                    if g.ph(a)[i] == 0 and g.ph(b)[i] == 0:
                        s -= 50
            s += rng.random() * 1e-6
            if s > bs:
                bs, best = s, [(a, b)]
        return best[0]

    return choose


def chooser_smart(rng, nworlds=150, lookahead=True):
    """Crença por amostragem: sorteia mundos coerentes com tudo que foi visto
    (genes dos iniciais e quais filhotes receberam quais genes), com peso pela
    probabilidade das ninhadas observadas. Escolhe o par com maior chance de fazer
    o alvo agora; se nenhum garante, olha um cruzamento à frente."""

    def sample_world(g):
        n = g.W.n
        geno = {}
        w = 1.0
        for s in ['A', 'B', 'C']:
            gt = []
            for i in range(n):
                if g.ph(s)[i] == 0:
                    gt.append((0, 0))
                else:
                    pAA = P_DOM * P_DOM
                    pAa = 2 * P_DOM * (1 - P_DOM)
                    gt.append((1, 1) if rng.random() < pAA / (pAA + pAa) else ((1, 0) if rng.random() < 0.5 else (0, 1)))
            geno[s] = tuple(gt)
        for (a, b, kids) in g.crosses:
            ga, gb = geno[a], geno[b]
            kg = [[None] * n for _ in range(4)]
            for i in range(n):
                pun = [(ga[i][0], gb[i][0]), (ga[i][0], gb[i][1]), (ga[i][1], gb[i][0]), (ga[i][1], gb[i][1])]
                obs = [g.ph(k)[i] for k in kids]
                byp = {0: [], 1: []}
                for p in pun:
                    byp[p[0] | p[1]].append(p)
                if len(byp[0]) != obs.count(0):
                    return None, 0.0
                m = math.factorial(len(byp[0])) * math.factorial(len(byp[1]))
                w *= m / 24.0
                rng.shuffle(byp[0]); rng.shuffle(byp[1])
                it = {0: iter(byp[0]), 1: iter(byp[1])}
                for kk in range(4):
                    kg[kk][i] = next(it[obs[kk]])
            for kk, k in enumerate(kids):
                geno[k] = tuple(kg[kk])
        return geno, w

    def litter_win(ga, gb, n, t):
        cols = []
        for i in range(n):
            pun = [(ga[i][0], gb[i][0]), (ga[i][0], gb[i][1]), (ga[i][1], gb[i][0]), (ga[i][1], gb[i][1])]
            ph = [p[0] | p[1] for p in pun]
            rng.shuffle(ph)
            cols.append(ph)
        kids = [tuple(cols[i][k] for i in range(n)) for k in range(4)]
        return any(k == t for k in kids), kids

    def choose(g, prs):
        n, t = g.W.n, g.W.target
        worlds = []
        tries = 0
        while len(worlds) < nworlds and tries < nworlds * 40:
            tries += 1
            wd, w = sample_world(g)
            if wd is not None and w > 0:
                worlds.append((wd, w))
        if not worlds:
            return rng.choice(prs)
        W = sum(w for _, w in worlds)
        left = g.maxc - len(g.crosses)
        scores = []
        for a, b in prs:
            p1 = 0.0
            p2acc = {}
            for wd, w in worlds:
                win, kidsph = litter_win(wd[a], wd[b], n, t)
                if win:
                    p1 += w
                elif lookahead and left >= 2:
                    # genes dos filhotes neste mundo (aproximado: sorteio por gene)
                    kg = []
                    ga, gb = wd[a], wd[b]
                    cols = []
                    for i in range(n):
                        pun = [(ga[i][0], gb[i][0]), (ga[i][0], gb[i][1]), (ga[i][1], gb[i][0]), (ga[i][1], gb[i][1])]
                        rng.shuffle(pun)
                        cols.append(pun)
                    kg = [tuple(cols[i][k] for i in range(n)) for k in range(4)]
                    cand = [x for x in g.pop] + ['k0', 'k1', 'k2', 'k3']
                    lookup = dict(wd)
                    for kk in range(4):
                        lookup['k' + str(kk)] = kg[kk]
                    for x in ['k0', 'k1', 'k2', 'k3']:
                        for y in cand:
                            if y == x or (y.startswith('k') and y < x):
                                continue
                            win2, _ = litter_win(lookup[x], lookup[y], n, t)
                            if win2:
                                key = (x, y)
                                p2acc[key] = p2acc.get(key, 0.0) + w
                    # pares antigos que não usam filhotes novos já foram avaliados como primeiro passo
            p1 /= W
            p2 = max(p2acc.values()) / W if p2acc else 0.0
            scores.append((p1 + (1 - p1) * p2 * 0.9 + rng.random() * 1e-9, p1, (a, b)))
        scores.sort(reverse=True)
        return scores[0][2]

    return choose


def run(label, n, maxc, npuz, hard=False, smart_worlds=120, seed0=1, minpar=2):
    t0 = time.time()
    res = {'aleatorio': [], 'intuitivo': [], 'esperto': []}
    pars = []
    for s in range(npuz):
        P = make_puzzle(n, seed0 * 100000 + s, hard=hard, minpar=minpar)
        if P is None:
            continue
        pars.append(P.par)
        for name, mk in [('aleatorio', lambda r: chooser_random(r)), ('intuitivo', lambda r: chooser_intuitive(r)),
                         ('esperto', lambda r: chooser_smart(r, smart_worlds))]:
            reps = 3 if name != 'esperto' else 1
            for rep in range(reps):
                W2 = World(n, [P.geno['A'], P.geno['B'], P.geno['C']], P.target, P.key)
                g = Game(W2, maxc)
                r = play(g, mk(random.Random(s * 31 + rep)))
                res[name].append((r, P.par))
    out = [f'== {label}: {len(pars)} desafios, par 2: {pars.count(2)}, par 3: {pars.count(3)}  ({time.time() - t0:.0f}s)']
    for name, rs in res.items():
        wins = [r for r, _ in rs if r is not None]
        atpar = sum(1 for r, p in rs if r is not None and r <= p)
        dist = Counter(r if r is not None else 'X' for r, _ in rs)
        out.append(f'  {name:9s} vence {100 * len(wins) / len(rs):5.1f}%  média {sum(wins) / max(1, len(wins)):.2f}  no mínimo {100 * atpar / len(rs):5.1f}%  dist {dict(sorted(dist.items(), key=lambda kv: str(kv[0])))}')
    return '\n'.join(out)


if __name__ == '__main__':
    which = sys.argv[1]
    npuz = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    if which == 'classico':
        print(run('Clássico, 3 genes, 6 cruzamentos', 3, 6, npuz))
    elif which == 'classico4':
        print(run('Clássico, 3 genes, 4 cruzamentos', 3, 4, npuz))
    elif which == 'genes4':
        print(run('4 genes, 7 cruzamentos', 4, 7, npuz, seed0=2))
    elif which == 'genes4x6':
        print(run('4 genes, 6 cruzamentos', 4, 6, npuz, seed0=2))
    elif which == 'par3x6':
        print(run('Clássico só com mínimo 3, 6 cruzamentos', 3, 6, npuz, seed0=4, minpar=3))
    elif which == 'par3x5':
        print(run('Clássico só com mínimo 3, 5 cruzamentos', 3, 5, npuz, seed0=4, minpar=3))
    elif which == 'g4par3x6':
        print(run('4 genes só com mínimo 3, 6 cruzamentos', 4, 6, npuz, seed0=5, minpar=3))
    elif which == 'par3x8':
        print(run('Clássico só com mínimo 3, 8 cruzamentos', 3, 8, npuz, seed0=4, minpar=3))
    elif which == 'classico5':
        print(run('Clássico, 3 genes, 5 cruzamentos', 3, 5, npuz))
    elif which == 'dificil':
        print(run('Difícil (recessivo escondido), 3 genes, 6 cruzamentos', 3, 6, npuz, hard=True, seed0=3))
    sys.stdout.flush()
