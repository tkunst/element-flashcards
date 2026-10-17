# CI for Element Flashcards

This repo is one resource on the tklearn study hub (https://tkunst.github.io/) and shares the hub's CI setup. The full description, including what was deliberately left out and how to add a new resource repo, is in the hub repo's [`docs/ci.md`](https://github.com/tkunst/tkunst.github.io/blob/main/docs/ci.md).

## What runs here

| Check | When | What it does |
|---|---|---|
| **ci: site-guard** | every push / PR | `scripts/site_guard.py` (shared with the hub; keep the copies identical): no em-dashes, nothing loaded from another site, only the published contact address, AP notice where AP is mentioned, page basics, link back to the hub. |
| **ci: smoke** | every push / PR | `tests/smoke_test.py` in headless Chromium at laptop and phone sizes (details below). |
| **secrets** | every push / PR | gitleaks over the full git history. |
| **Dependabot** | monthly | Workflow actions and Playwright (`tests/requirements.txt`). |

The hub's weekly `live` check also opens the published page and confirms it returns 200, has a title, and links back to the hub.

## What the smoke test covers

The test carries its own answer key for all 42 elements, so it also cross-checks the page's data.

- A correct first answer moves a new card to box 2 (saved in `localStorage`).
- A misspelled name is "close" and can be fixed; a fixed answer does not promote the card.
- A wrong-case symbol (`co` for `Co`) is "close", never right.
- A missed card comes back within the next few cards, and re-answering it does not promote it.
- Progress survives a reload; the new-card count goes down; the next day (simulated with the `window.__tklearn.shiftDays` test hook) cards come due.
- Tap-a-color category answers grade correctly.
- A near-miss name spelling counts as right, shows the correct spelling, and promotes the card.
- Name ladder: a new card starts at step 1 (three spellings, exactly one real); picking a misspelling is wrong and keeps box 1; a box-2 card shows the right chunk tiles plus the decoy; wrong order is wrong and drops to box 1; the right order promotes to box 3; a box-3 card is typed and a near miss counts.
- Sort: the metal block is exactly Na + Mg in 1-15 and K through Zn in 16-30, moves as one chip ("2 metals") and scores as one item (14 items in 1-15, 4 in 16-30; the block in nonmetal is wrong); tap-to-place and mouse drag both land in the right oval; check scores right/wrong; "send wrong ones back" returns only the wrong ones; a perfect sort shows the staircase rule.
- Game: the first round of a group is the easy round (row highlighted before any tap); finishing it makes the next round normal (no row until 2 misses, square revealed at 3); a correct tap counts and colors the square.
- Backup code: reset clears progress and restore brings it back exactly.
- Connections (same element): 16 tiles, 4 of each kind; each group's symbol, name, number and map square agree with the answer key; 3-of-4 says "One away!", 2+2 is not a group, all 4 groups solve with the mistake count shown. Same family: 15 tiles, 5 groups of 3, solve and show the five family labels (alkali, alkaline earth, transition, halogens, noble gases).
- Spelling: Morphemes view opens by default and its "Where each name comes from" list has all 42 names once; Graphemes view boxes Ph/ph/or in Phosphorus and Ch/or/ne in Chlorine, its all-42 card spells every name, and no "_" notation appears; Phonemes view marks every spelling on the /k/ card.
- Sound claims (static, American IPA): every "/x/: one sound" card only lists names whose IPA contains /x/ (short /ɪ/ is not counted inside /aɪ/, /eɪ/, /ɔɪ/), and the one-spelling cards' stated sounds are checked against the IPA (c, g, s, y, i, -on). Every name has a meaning (ORIGIN) and graphemes of 1-4 letters.
- Wording rule (static check): the page and README never use "tricky", "sight word(s)", "heart word(s)", "sneaky", "whole word", "irregular", "memorize", or "doesn't follow", so nothing suggests a word can't be sounded out.
- Letter-teams view: Phosphorus shows Ph, ph, or boxed; Chlorine shows the i_e split team; all 42 names still spelled.
- Pronunciations: every name has an IPA transcription + respelling (hand-written, then cross-checked against the CMU Pronouncing Dictionary on 2026-10-17: 41 of 42 identical; Uranium uses the dictionary-standard /jʊˈreɪniəm/ where CMU has /jəˈreɪniəm/). Potassium was later changed to /poʊˈtæsiəm/ (long o) to match the recorded voice. The data check confirms the "-on" tip lists the "ahn" names (/ɑn/) and the "un" names (/ən/) correctly.
- Audio: all 42 clips exist at `audio/NN-name.mp3` and are real MP3s; the flashcard answer's, Find prompt's and Spelling detail's play buttons load the right clip without a media error.
- Static data check (no browser): the letter teams spell every name exactly, and no ladder piece boundary falls inside a letter team or between the halves of a split team.
- Find the Elements on Blank and Numbers-only boards: squares hide symbols, a correct tap counts and shows the symbol.
- With `localStorage` blocked, the warning banner shows and the cards still work.
- No JavaScript errors anywhere.

Verified by breaking the page on purpose: box promotion off, missed-card requeue removed, symbol case ignored, storage error unguarded, wrong game square accepted (2026-10-16); ladder step fixed at typing, near-miss not counted, sort always right, send-back disabled, any chunk order accepted, easy-round row not shown, easy round never marked done, row hint delayed to 3 misses (2026-10-17); see the commit log for later features. Each break made the test fail.

## Running locally

```sh
python3 scripts/site_guard.py
pip install -r tests/requirements.txt
python -m playwright install chromium
python3 tests/smoke_test.py
```

## If you change the page

The test relies on these IDs and attributes: `#jswarn`, `#nostore`, `#stNew`, `#stDue`, `#startReview`, `#startPractice`, `#fcFace .sym` / `.nm`, `#in-name`, `#in-cat`, `#in-sym`, `#f-name`, `#f-sym`, `#fcCheck`, `#fcNext`, `#fcStop`, `.result`, `#fcInputs .cat[data-c]`, `[data-set]`, `[data-catmode]`, `[data-tab]`, `[data-namemode]`, `#fcStep`, `#fcInputs .opt[data-o]`, `#tiles .tile[data-t]`, `#built`, `#fb-name`, `#sBoard [data-z]`, `#ovals .oval[data-c]`, `#ovals .chip[data-u]`, `#sBoard .sq.blk`, `#sCheck`, `#sRetry`, `#sScore`, `#sRule`, `#gEasy`, `[data-gboard]`, `[data-cxmode]`, `#cxGrid .cx[data-g]`, `#cxSubmit`, `#cxClear`, `#cxMsg`, `#cxSolved .lab`, `#fams .fname`, `[data-spellview]`, `#glegend`, `.gr.multi`, `.gr.split`, the `GRAPH` and `LADDER` tables, `.play[data-z]`, `window.__tklearn.audio`, the `audio/` file names, `#fdetail`, `#gStart`, `#gPrompt`, `#gStatus`, `#gBoard [data-z]`, `#pBoard`, `#bkOut`, `#bkIn`, `#bkReset`, `#bkRestore`, the storage key `tklearn-element-flashcards-v1`, and `window.__tklearn`. Rename one and update `tests/smoke_test.py` in the same commit.
