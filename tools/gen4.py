"""Gera a lista do modo "Quatro genes difícil" do treino.

Mesmas regras do gerador do jogo pro modo de quatro genes (justo, a asa dá trabalho,
o inicial mais parecido com o alvo erra pelo menos 2 traços, mínimo de 3 cruzamentos),
com as ninhadas sorteadas pelas mesmas fórmulas do jogo (ver gen100.py), e um filtro
de dificuldade pela simulação de jogadores com 8 cruzamentos.
No quarto gene (asa), 0 é o recessivo, e o slime com 0 nas duas cópias tem asa.
"""
import random, json, sys, time
from sim import phen, Game, play, chooser_intuitive, chooser_random
from gen100 import ExactWorld

N_GENES, MAX_CROSSES = 4, 8
PI_MIN, PI_MAX, PR_MAX = 0.25, 0.70, 0.125


def candidate(rng, key):
    n = N_GENES
    while True:
        starters = [tuple((int(rng.random() < 0.55), int(rng.random() < 0.55)) for _ in range(n)) for _ in range(3)]
        t = phen(tuple((int(rng.random() < 0.55), int(rng.random() < 0.55)) for _ in range(n)))
        ps = [phen(s) for s in starters]
        if any(p == t for p in ps):
            continue
        if not all(any(p[i] == t[i] for p in ps) for i in range(n)):  # justo: todo traço do alvo aparece em algum inicial
            continue
        work = rng.randrange(n)  # o gene que dá trabalho, sorteado (até 2026-10-23 era sempre a asa): o alvo pede o recessivo dele
        if t[work] != 0:
            continue
        score = [sum(p[i] == t[i] for i in range(n) if i != work) for p in ps]
        top = max(score)
        if any(score[k] == top and ps[k][work] == 0 for k in range(3)):  # esse recessivo não está no inicial mais parecido
            continue
        if n - max(sum(p[i] == t[i] for i in range(n)) for p in ps) < 2:  # o mais parecido erra pelo menos 2 traços
            continue
        W = ExactWorld(n, starters, t, key)
        if W.solve(3) == 3:
            return starters, t


def evaluate(starters, t, key, reps=8):
    wi = wr = 0; used = []
    for r in range(reps):
        res = play(Game(ExactWorld(N_GENES, starters, t, key), MAX_CROSSES), chooser_intuitive(random.Random(1000 + r)))
        if res: wi += 1; used.append(res)
        if play(Game(ExactWorld(N_GENES, starters, t, key), MAX_CROSSES), chooser_random(random.Random(2000 + r))): wr += 1
    return wi / reps, wr / reps, (sum(used) / len(used) if used else None)


if __name__ == '__main__':
    # uso: python gen4.py [quantos] [semente] [prefixo] [arquivo]
    # treino: 100 20261014 lista4 list4.json · desafio do dia no modo difícil: 100 20261015 dia4 daily4.json
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 20261014
    PREFIX = sys.argv[3] if len(sys.argv) > 3 else 'lista4'
    OUT = sys.argv[4] if len(sys.argv) > 4 else 'list4.json'
    rng = random.Random(SEED)
    out, tried, t0 = [], 0, time.time()
    while len(out) < N:
        tried += 1
        key = PREFIX + ':' + str(tried)
        starters, t = candidate(rng, key)
        pi, pr, avg = evaluate(starters, t, key)
        if not (PI_MIN <= pi <= PI_MAX and pr <= PR_MAX):
            continue
        out.append({'k': key, 's': [''.join(str(a) + str(b) for a, b in s) for s in starters], 't': ''.join(map(str, t)), 'pi': pi, 'pr': pr, 'avg': avg})
    json.dump(out, open(OUT, 'w'), separators=(',', ':'))
    pis = [o['pi'] for o in out]; prs = [o['pr'] for o in out]
    print('candidatos testados: %d, aceitos: %d, %.0f s' % (tried, len(out), time.time() - t0))
    print('intuitivo vence em média %.0f%%, ao acaso %.0f%%' % (100 * sum(pis) / len(pis), 100 * sum(prs) / len(prs)))
