"""Gera desafios do difícil do dia com gene escondido e duas ameaças (experimento de 2026-10-15).

Igual ao gen4ameaca.py, mais a regra do escondido: pelo menos um traço recessivo do alvo
não aparece em nenhum slime inicial, só escondido dentro de um dominante. Pra chegar no
alvo é preciso descobrir quem carrega o gene, cruzando e lendo a ninhada.
Mede também o jogador que calcula (chooser_smart), pra separar o desafio que exige pensar
do desafio que é só azar do embaralhamento.
"""
import random, json, sys, time
from sim import phen, play, chooser_intuitive, chooser_random, chooser_smart
from gen100 import ExactWorld
from gen4 import N_GENES, MAX_CROSSES
from gen4ameaca import GameT, solve_t, AT, IDS, evaluate

PI_MIN, PI_MAX, PR_MAX = 0.125, 0.5, 0.125  # o jogador que calcula ficou lento demais (minutos por desafio) e saiu do filtro


def candidate(rng, key):
    n = N_GENES
    while True:
        starters = [tuple((int(rng.random() < 0.55), int(rng.random() < 0.55)) for _ in range(n)) for _ in range(3)]
        t = phen(tuple((int(rng.random() < 0.55), int(rng.random() < 0.55)) for _ in range(n)))
        ps = [phen(s) for s in starters]
        if any(p == t for p in ps):
            continue
        if t[3] != 0:  # o alvo pede asa
            continue
        rec = [i for i in range(n) if t[i] == 0]
        if len(rec) < 2:
            continue
        hidden = [i for i in rec if all(p[i] == 1 for p in ps) and any(0 in s[i] for s in starters)]
        if len(hidden) != 1:  # exatamente um traço do alvo escondido; os outros à vista
            continue
        if not all(any(p[i] == t[i] for p in ps) for i in range(n) if i not in hidden):
            continue
        if n - max(sum(p[i] == t[i] for i in range(n)) for p in ps) < 2:
            continue
        gs = rng.sample(rec, 2)
        ev = list(zip(gs, AT))
        W = ExactWorld(n, starters, t, key)
        if solve_t(W, ev, 3) == 3:
            return starters, t, ev, hidden[0]


def smart_rate(starters, t, key, ev, reps=4):
    w = 0
    for r in range(reps):
        if play(GameT(ExactWorld(N_GENES, starters, t, key), MAX_CROSSES, ev), chooser_smart(random.Random(3000 + r), nworlds=80)):
            w += 1
    return w / reps


if __name__ == '__main__':
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 20261017
    START = int(sys.argv[3]) if len(sys.argv) > 3 else 5000
    OUT = sys.argv[4] if len(sys.argv) > 4 else 'daily4escondido.json'
    rng = random.Random(SEED)
    out, tried, t0 = [], START, time.time()
    while len(out) < N:
        tried += 1
        key = 'dia4:' + str(tried)
        starters, t, ev, hid = candidate(rng, key)
        pi, pr, avg = evaluate(starters, t, key, ev)
        if not (PI_MIN <= pi <= PI_MAX and pr <= PR_MAX):
            continue
        ps = 0.0
        print('cand', tried, 'pi %.2f pr %.2f ps %.2f' % (pi, pr, ps), flush=True)
        out.append({'k': key, 's': [''.join(str(a) + str(b) for a, b in s) for s in starters], 't': ''.join(map(str, t)),
                    'e': ','.join(IDS[g] for g, _ in ev), 'hid': IDS[hid], 'pi': pi, 'pr': pr, 'ps': ps, 'avg': avg})
        print(len(out), round(time.time() - t0), flush=True)
    json.dump(out, open(OUT, 'w'), separators=(',', ':'))
    print('candidatos: %d, aceitos: %d, %.0f s' % (tried - START, len(out), time.time() - t0))
