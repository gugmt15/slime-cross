# Slime Cross

Desafio diário de genética de Mendel, em pixel art. Tu começa com três slimes de genes escondidos, cruza eles e tenta fazer nascer o slime alvo em até 6 cruzamentos.

**Jogar:** https://gugmt15.github.io/slime-cross/

## Como funciona

- Cada slime tem duas cópias de cada gene (cor, chifre, olhos), uma de cada pai. Maiúscula é dominante, minúscula recessiva.
- Cada cruzamento dá 4 filhotes nas proporções exatas de Mendel, gene por gene. O mesmo par dá sempre a mesma ninhada.
- O desafio do dia é o mesmo pra todo mundo e é gerado a partir da data. Um solucionador confere que dá pra resolver em 2 ou 3 cruzamentos, e o gene que o alvo pede sempre aparece à vista em algum slime inicial.
- **Easy Mode** mostra as letras dos genes e deixa marcar palpites.
- **Treino** tem outras versões (roxo, transparente, quatro genes com asas, roxo e transparente) e modos especiais (Difícil, Envelhecer, Ameaça).

## Editar

O jogo inteiro é o `index.html`: HTML, CSS e JavaScript num arquivo só, sem build. Pra testar, é só abrir o arquivo no navegador. Ele busca na internet só as fontes (Google Fonts) e a biblioteca que desenha a árvore (dagre, pelo cdnjs); sem internet, as fontes caem pras do sistema e a árvore vira linhas por geração.

Publicar: `git push` na branch `main`. O GitHub Pages atualiza o site sozinho em um ou dois minutos.

O progresso e as estatísticas ficam no navegador de cada jogador (localStorage).
