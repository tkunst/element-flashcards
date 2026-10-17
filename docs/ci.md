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
- Game: three misses reveal the square; a correct tap counts and colors the square.
- Backup code: reset clears progress and restore brings it back exactly.
- With `localStorage` blocked, the warning banner shows and the cards still work.
- No JavaScript errors anywhere.

Verified when set up by breaking the page on purpose: box promotion off, missed-card requeue removed, symbol case ignored, storage error unguarded, and wrong game square accepted. Each break made the test fail.

## Running locally

```sh
python3 scripts/site_guard.py
pip install -r tests/requirements.txt
python -m playwright install chromium
python3 tests/smoke_test.py
```

## If you change the page

The test relies on these IDs and attributes: `#jswarn`, `#nostore`, `#stNew`, `#stDue`, `#startReview`, `#startPractice`, `#fcFace .sym` / `.nm`, `#in-name`, `#in-cat`, `#in-sym`, `#f-name`, `#f-sym`, `#fcCheck`, `#fcNext`, `#fcStop`, `.result`, `#fcInputs .cat[data-c]`, `[data-set]`, `[data-catmode]`, `[data-tab]`, `#gStart`, `#gPrompt`, `#gStatus`, `#gBoard [data-z]`, `#pBoard`, `#bkOut`, `#bkIn`, `#bkReset`, `#bkRestore`, the storage key `tklearn-element-flashcards-v1`, and `window.__tklearn`. Rename one and update `tests/smoke_test.py` in the same commit.
