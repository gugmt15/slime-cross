"""Gera a lista de desafios do dia do Slime Cross.

A ordem dos filhotes em cada ninhada usa exatamente as mesmas fórmulas do jogo
(hashStr FNV-1a, rngFrom e shuffle4 do index.html), então a dificuldade medida
aqui é a mesma que o jogador encontra. Cada candidato passa pelas regras do jogo
(justo, mínimo de 3 cruzamentos) e por uma simulação de jogadores.
"""
import random, json, sys
import sim
from sim import phen, Game, play, chooser_intuitive, chooser_random

# ---------- cópia exata das funções do jogo ----------
def u32(x): return x & 0xFFFFFFFF
def i32(x):
    x &= 0xFFFFFFFF
    return x - 0x100000000 if x >= 0x80000000 else x
def imul(a, b): return i32(u32(a) * u32(b))

def hash_str(s):
    h = 2166136261
    for ch in s:
        for cu in ch.encode('utf-16-le').__iter__() if False else [ord(ch)]:
            h = i32(h) ^ cu
            h = u32(imul(h, 16777619))
    return h

def rng_from(seed):
    a = [u32(seed)]
    def nxt():
        a[0] = u32(a[0] + 0x6D2B79F5)
        t = a[0]
        t = imul(i32(t) ^ i32(u32(t) >> 15), i32(t) | 1)
        inner = imul(i32(t) ^ i32(u32(t) >> 7), i32(t) | 61)
        t = i32(t) ^ i32(t + inner)
        return u32(i32(t) ^ i32(u32(t) >> 14)) / 4294967296
    return nxt

def shuffle4(rng):
    p = [0, 1, 2, 3]
    for i in range(3, 0, -1):
        j = int(rng() * (i + 1))
        p[i], p[j] = p[j], p[i]
    return p


class ExactWorld(sim.World):
    def litter(self, a, b):
        x, y = (a, b) if a < b else (b, a)
        k = (x, y)
        if k in self.lit:
            return self.lit[k]
        mk = x + '|' + y
        gx, gy = self.geno[x], self.geno[y]
        kids = [[None] * self.n for _ in range(4)]
        for i in range(self.n):
            pun = [(gx[i][0], gy[i][0]), (gx[i][0], gy[i][1]), (gx[i][1], gy[i][0]), (gx[i][1], gy[i][1])]
            perm = shuffle4(rng_from(hash_str(self.key + '|' + mk + '|' + str(i))))
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


def candidate(rng, key):
    n = 3
    while True:
        starters = [tuple((int(rng.random() < 0.55), int(rng.random() < 0.55)) for _ in range(n)) for _ in range(3)]
        t = phen(tuple((int(rng.random() < 0.55), int(rng.random() < 0.55)) for _ in range(n)))
        if all(t) or any(phen(s) == t for s in starters):
            continue
        if not all(any(phen(s)[i] == t[i] for s in starters) for i in range(n)):
            continue
        W = ExactWorld(n, starters, t, key)
        d = W.solve(3)
        if d == 3:
            return starters, t, W


def evaluate(starters, t, key, reps=8):
    wi = wr = 0; used = []
    for r in range(reps):
        W = ExactWorld(3, starters, t, key)
        res = play(Game(W, 8), chooser_intuitive(random.Random(1000 + r)))
        if res: wi += 1; used.append(res)
        W = ExactWorld(3, starters, t, key)
        if play(Game(W, 8), chooser_random(random.Random(2000 + r))): wr += 1
    return wi / reps, wr / reps, (sum(used) / len(used) if used else None)


if __name__ == '__main__':
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    rng = random.Random(20261006)
    out, tried, prev_t = [], 0, None
    while len(out) < N:
        tried += 1
        key = 'lista1:' + str(tried)
        starters, t, W = candidate(rng, key)
        if t == prev_t:
            continue
        pi, pr, avg = evaluate(starters, t, key)
        if not (0.5 <= pi <= 0.95 and pr <= 0.25):
            continue
        out.append({'k': key, 's': [''.join(str(a) + str(b) for a, b in s) for s in starters], 't': ''.join(map(str, t)), 'pi': pi, 'pr': pr, 'avg': avg})
        prev_t = t
    json.dump(out, open('lista100.json', 'w'), separators=(',', ':'))
    pis = [o['pi'] for o in out]; prs = [o['pr'] for o in out]; avgs = [o['avg'] for o in out if o['avg']]
    from collections import Counter
    print('candidatos testados:', tried, 'aceitos:', len(out))
    print('intuitivo vence em média %.0f%%, ao acaso %.0f%%, cruzamentos médios do intuitivo %.2f' % (100 * sum(pis) / len(pis), 100 * sum(prs) / len(prs), sum(avgs) / len(avgs)))
    print('alvos:', Counter(o['t'] for o in out).most_common())
