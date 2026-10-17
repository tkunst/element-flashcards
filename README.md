# Element Flashcards

Spaced-repetition flashcards and a find-it game for 42 common elements (atomic numbers 1-30 plus Br, Kr, Ag, Sn, I, Pt, Au, Hg, Pb, Rn, U, Pu): name, symbol, and metal / nonmetal / metalloid.

Live: https://tkunst.github.io/element-flashcards/ · Part of the study-resources hub: https://tkunst.github.io/

- **Flashcards:** two cards per element (symbol → name + category, name → symbol), typed answers with no word bank at the top step. Leitner boxes: right moves a card up (due again in 1, 2, 4, then 7 days), wrong sends it back to box 1 and brings it back a few cards later in the same session. Up to 12 new cards a day. "Practice all" ignores the schedule.
- **Step-by-step names** (default; "Always type" turns it off): the card's spaced-repetition box picks the step. New or missed cards: pick the real spelling from three (the decoys are realistic misspellings: ph/f, c/k, -on/-an, dropped double letters). Box 2: build the name from syllable pieces plus a decoy piece. Box 3 and up: type it with no help. A card can only reach "solid" by typing it. A near-miss spelling counts as right and the correct spelling is shown.
- **Sort:** drag (or tap) each element from the periodic table into a metal, metalloid, or nonmetal oval; check; send wrong ones back. A perfect sort shows the staircase rule.
- **Find the Elements** (easy round first: for each element group, the first round highlights the row right away; after one easy round, the row hint waits for 2 misses; the checkbox turns it back on): a periodic-table board; tap the square for the element named. Hints after 2 and 3 misses; optional timer with a best time.
- **Find the Elements boards:** Symbols, Numbers only, or Blank (a found square shows its symbol). Best times are kept per board.
- **Connections:** 16 tiles, find 4 groups of 4. "Same element": an element's symbol, name, atomic number, and spot on a mini table. "Same family": halogens, noble gases, groups 1-2 metals, transition metals (from all 42). "One away!" when 3 of 4 match; mistakes are counted, never game-ending.
- **Spelling:** the 42 names in 8 spelling families by ending (-ium, -inum, -ine, -on, -gen, -er/-ur, short and old, one of a kind) plus a "sneaky y" strip, with the tricky letters marked, or a "Letter teams" view that boxes each multi-letter grapheme (ph, ch, th, ck, ll, ss, pp, ar, or, er, ur, ea, uor) and shows split teams (i_e, e_e) dashed. Ladder pieces never split a letter team. Tap a name for its symbol, category, and location.
- **Hear it:** a play button on every flashcard answer and in the Spelling details plays a recorded human pronunciation (`audio/NN-name.mp3`, 42 clips). Clips play only when tapped and load from this site; nothing is sent anywhere.
- **Progress:** per-element strength map, plus a backup code to copy progress to another device.

No account: progress lives in this browser's `localStorage` only and is never sent anywhere. Clearing site data, a guest window, or a different device starts fresh (use the backup code to move it).

## CI

See [`docs/ci.md`](docs/ci.md).

## Privacy pre-push hook

Run `scripts/install-hooks.sh` once per clone. It blocks pushes containing locally configured private terms (`~/.config/privacy-gate/terms.txt`, kept outside the repo; fail-closed if missing).

## License

Content and audio recordings CC BY-NC 4.0, code MIT. © 2026 Trisha Kunst.
