"""Gera a lista do desafio do dia no modo difícil com duas ameaças.

Mesmo desafio de quatro genes do gen4.py, mais duas ameaças: depois do 2º e do 4º
cruzamento morrem todos os slimes que mostram um traço recessivo do alvo (a ventania
leva os de asa, o lobo come os sem chifre, o gavião leva os de um olho, o sol derrete
os azuis). Quem só esconde o traço escapa. O alvo tem pelo menos dois traços recessivos,
e as duas ameaças miram dois traços diferentes dele. Um gene sorteado faz o papel que era
sempre da asa: o alvo mostra o recessivo dele, e o inicial mais parecido com o alvo não
(antes de 2026-10-23 era sempre a asa, e todo alvo do difícil tinha asa).
O solucionador e os jogadores simulados respeitam as ameaças; o jogador intuitivo não
se prepara pra elas (gente de verdade lê o aviso), então o filtro é um pouco mais duro
do que o jogador real vai sentir.
"""
import random, json, sys, time
from sim import phen, Game, play, chooser_intuitive, chooser_random
from gen100 import ExactWorld
from gen4 import N_GENES, MAX_CROSSES

AT = [2, 4]
IDS = {0: 'azul', 1: 'chifre', 2: 'olhos', 3: 'asas'}  # gene -> ameaça que mata quem mostra o recessivo dele
PI_MIN, PI_MAX, PR_MAX = 0.125, 0.5, 0.125


class GameT(Game):
    def __init__(self, W, maxc, ev):
        super().__init__(W, maxc)
        self.ev = ev  # [(gene, depois de quantos cruzamentos)]

    def cross(self, a, b):
        super().cross(a, b)
        if self.won:
            return
        for g, at in self.ev:
            if len(self.crosses) == at:
                self.pop = [c for c in self.pop if self.ph(c)[g] != 0]


def solve_t(W, ev, maxd):
    tgt = W.target

    def dfs(pop, done, made, d):
        for i in range(len(pop)):
            for j in range(i + 1, len(pop)):
                a, b = pop[i], pop[j]
                pk = (min(a, b), max(a, b))
                if pk in done:
                    continue
                kids = W.litter(a, b)
                if any(phen(W.geno[k]) == tgt for k in kids):
                    return 1
                if d > 1:
                    np = pop + kids
                    for g, at in ev:
                        if made + 1 == at:
                            np = [c for c in np if phen(W.geno[c])[g] != 0]
                    r = dfs(np, done | {pk}, made + 1, d - 1)
                    if r:
                        return 1 + r
        return 0

    for d in range(1, maxd + 1):
        if dfs(['A', 'B', 'C'], frozenset(), 0, d):
            return d
    return None


def candidate(rng, key):
    n = N_GENES
    while True:
        starters = [tuple((int(rng.random() < 0.55), int(rng.random() < 0.55)) for _ in range(n)) for _ in range(3)]
        t = phen(tuple((int(rng.random() < 0.55), int(rng.random() < 0.55)) for _ in range(n)))
        ps = [phen(s) for s in starters]
        if any(p == t for p in ps):
            continue
        if not all(any(p[i] == t[i] for p in ps) for i in range(n)):  # justo
            continue
        work = rng.randrange(n)  # o gene que dá trabalho: o alvo pede o recessivo dele
        if t[work] != 0:
            continue
        rec = [i for i in range(n) if t[i] == 0]
        if len(rec) < 2:  # duas ameaças, dois traços do alvo
            continue
        score = [sum(p[i] == t[i] for i in range(n) if i != work) for p in ps]
        top = max(score)
        if any(score[k] == top and ps[k][work] == 0 for k in range(3)):  # o recessivo não está no inicial mais parecido
            continue
        if n - max(sum(p[i] == t[i] for i in range(n)) for p in ps) < 2:
            continue
        gs = rng.sample(rec, 2)
        ev = list(zip(gs, AT))
        W = ExactWorld(n, starters, t, key)
        if solve_t(W, ev, 3) == 3:
            return starters, t, ev


def evaluate(starters, t, key, ev, reps=8):
    wi = wr = 0; used = []
    for r in range(reps):
        res = play(GameT(ExactWorld(N_GENES, starters, t, key), MAX_CROSSES, ev), chooser_intuitive(random.Random(1000 + r)))
        if res: wi += 1; used.append(res)
        if play(GameT(ExactWorld(N_GENES, starters, t, key), MAX_CROSSES, ev), chooser_random(random.Random(2000 + r))): wr += 1
    return wi / reps, wr / reps, (sum(used) / len(used) if used else None)


if __name__ == '__main__':
    # uso: python gen4ameaca.py [quantos] [semente] [primeiro número] [arquivo]
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 90
    SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 20261016
    START = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
    OUT = sys.argv[4] if len(sys.argv) > 4 else 'daily4ameaca.json'
    rng = random.Random(SEED)
    out, tried, t0 = [], START, time.time()
    while len(out) < N:
        tried += 1
        key = 'dia4:' + str(tried)
        starters, t, ev = candidate(rng, key)
        pi, pr, avg = evaluate(starters, t, key, ev)
        if not (PI_MIN <= pi <= PI_MAX and pr <= PR_MAX):
            continue
        out.append({'k': key, 's': [''.join(str(a) + str(b) for a, b in s) for s in starters], 't': ''.join(map(str, t)),
                    'e': ','.join(IDS[g] for g, _ in ev), 'pi': pi, 'pr': pr, 'avg': avg})
        print(len(out), round(time.time() - t0), flush=True)
    json.dump(out, open(OUT, 'w'), separators=(',', ':'))
    pis = [o['pi'] for o in out]; prs = [o['pr'] for o in out]
    print('candidatos testados: %d, aceitos: %d, %.0f s' % (tried - START, len(out), time.time() - t0))
    print('intuitivo vence em média %.0f%%, ao acaso %.0f%%' % (100 * sum(pis) / len(pis), 100 * sum(prs) / len(prs)))
