# Slime Cross

A daily genetics puzzle with pixel-art slimes. Every day everyone gets the same three slimes with hidden genes and the same target slime. Cross them, read the litters, work out what each one is hiding, and hatch the target in as few crosses as you can.

**Play:** [slimecross.com](https://slimecross.com) · English, Português, 日本語

![A game in progress: the target at the top, the dominant and recessive traits, and the family tree of crosses](docs/screenshot.jpg)

## How it plays

- Each slime carries two copies of three genes (color, horn, eyes), one from each parent. The dominant copy shows; the recessive one stays hidden and can come back in the next generation.
- Every cross produces 4 offspring in Mendel's exact ratios, gene by gene. The same pair always gives the same litter, so there is no luck involved, only deduction.
- Each daily challenge needs at least 3 crosses and allows 8. Everything the target needs is visible in at least one starting slime.
- The result is shared Wordle-style, as a grid of squares per litter.
- A four-step tutorial teaches the rules through Mendel's own experiment. Easy Mode shows the gene letters and lets you mark guesses. Practice mode adds variants (incomplete dominance, a gene that hides color, a fourth gene) and harder modes (aging, a predator that removes one phenotype, hidden carriers).

## How the challenges are made

Puzzles come from a seeded generator plus a solver. The generator draws three starting slimes and a target; the solver searches every sequence of crosses for the shortest solution, and anything solvable in fewer than 3 is rejected.

That alone still gave puzzles that were too easy, so difficulty was tuned with simulated players (`ferramentas/sim.py`, a Python port of the game rules):

- a **random** player, who crosses valid pairs at random;
- an **intuitive** player, who reasons from appearance and ancestry;
- a **smart** player, who keeps a belief over the hidden genes by sampling possible worlds and picks the cross most likely to hatch the target.

Under the first version of the rules almost every puzzle was solved in 2 crosses, and even the random player won 46% of the time. With the 3-cross minimum and a simulation filter, the first 100 daily challenges (`ferramentas/gen100.py`) are ones the intuitive player wins between 50% and 95% of the time, and the random player at most 25%.

## Code

The whole game is one `index.html`: HTML, CSS and plain JavaScript, no build step. The family tree is laid out with [dagre](https://github.com/dagrejs/dagre), and the fonts come from Google Fonts. Progress and stats stay in each player's browser (local storage); the site only counts visits, with Cloudflare's cookie-free analytics.

To run it, open `index.html` in a browser. To publish, push to `main`: the site is served by Cloudflare Pages, and every other branch gets its own preview address.
