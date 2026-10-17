# Element Flashcards

Spaced-repetition flashcards and a find-it game for 42 common elements (atomic numbers 1-30 plus Br, Kr, Ag, Sn, I, Pt, Au, Hg, Pb, Rn, U, Pu): name, symbol, and metal / nonmetal / metalloid.

Live: https://tkunst.github.io/element-flashcards/ · Part of the study-resources hub: https://tkunst.github.io/

- **Flashcards:** two cards per element (symbol → name + category, name → symbol), typed answers with no word bank. Leitner boxes: right moves a card up (due again in 1, 2, 4, then 7 days), wrong sends it back to box 1 and brings it back a few cards later in the same session. Up to 12 new cards a day. "Practice all" ignores the schedule.
- **Find the Elements:** a periodic-table board; tap the square for the element named. Hints after 2 and 3 misses; optional timer with a best time.
- **Progress:** per-element strength map, plus a backup code to copy progress to another device.

No account: progress lives in this browser's `localStorage` only and is never sent anywhere. Clearing site data, a guest window, or a different device starts fresh (use the backup code to move it).

## CI

See [`docs/ci.md`](docs/ci.md).

## Privacy pre-push hook

Run `scripts/install-hooks.sh` once per clone. It blocks pushes containing locally configured private terms (`~/.config/privacy-gate/terms.txt`, kept outside the repo; fail-closed if missing).

## License

Content CC BY-NC 4.0, code MIT. © 2026 Trisha Kunst.
