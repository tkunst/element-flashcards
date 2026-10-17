#!/usr/bin/env python3
"""Browser smoke test for the element flashcards (Playwright, headless Chromium).

Covers what would hurt most if it broke: grading, the spaced-repetition
schedule surviving a reload, missed cards coming back in the same session,
the page still working when browser storage is blocked, the find-it game, and
the backup code round trip. Runs at laptop and phone sizes.

    pip install -r tests/requirements.txt && python -m playwright install chromium
    python3 tests/smoke_test.py
"""
import pathlib
import re
import sys

from playwright.sync_api import sync_playwright

PAGE = (pathlib.Path(__file__).resolve().parent.parent / "index.html").as_uri()
KEY = "tklearn-element-flashcards-v1"

# Independent answer key (also cross-checks the page's data).
EL = {
    1: ("H", "Hydrogen", "nonmetal"), 2: ("He", "Helium", "nonmetal"), 3: ("Li", "Lithium", "metal"),
    4: ("Be", "Beryllium", "metal"), 5: ("B", "Boron", "metalloid"), 6: ("C", "Carbon", "nonmetal"),
    7: ("N", "Nitrogen", "nonmetal"), 8: ("O", "Oxygen", "nonmetal"), 9: ("F", "Fluorine", "nonmetal"),
    10: ("Ne", "Neon", "nonmetal"), 11: ("Na", "Sodium", "metal"), 12: ("Mg", "Magnesium", "metal"),
    13: ("Al", "Aluminum", "metal"), 14: ("Si", "Silicon", "metalloid"), 15: ("P", "Phosphorus", "nonmetal"),
    16: ("S", "Sulfur", "nonmetal"), 17: ("Cl", "Chlorine", "nonmetal"), 18: ("Ar", "Argon", "nonmetal"),
    19: ("K", "Potassium", "metal"), 20: ("Ca", "Calcium", "metal"), 21: ("Sc", "Scandium", "metal"),
    22: ("Ti", "Titanium", "metal"), 23: ("V", "Vanadium", "metal"), 24: ("Cr", "Chromium", "metal"),
    25: ("Mn", "Manganese", "metal"), 26: ("Fe", "Iron", "metal"), 27: ("Co", "Cobalt", "metal"),
    28: ("Ni", "Nickel", "metal"), 29: ("Cu", "Copper", "metal"), 30: ("Zn", "Zinc", "metal"),
    35: ("Br", "Bromine", "nonmetal"), 36: ("Kr", "Krypton", "nonmetal"), 47: ("Ag", "Silver", "metal"),
    50: ("Sn", "Tin", "metal"), 53: ("I", "Iodine", "nonmetal"), 78: ("Pt", "Platinum", "metal"),
    79: ("Au", "Gold", "metal"), 80: ("Hg", "Mercury", "metal"), 82: ("Pb", "Lead", "metal"),
    86: ("Rn", "Radon", "nonmetal"), 92: ("U", "Uranium", "metal"), 94: ("Pu", "Plutonium", "metal"),
}
BY_SYM = {v[0]: (z,) + v for z, v in EL.items()}
BY_NAME = {v[1]: (z,) + v for z, v in EL.items()}
VIEWPORTS = {"laptop": {"width": 1366, "height": 900}, "phone": {"width": 390, "height": 844}}


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def find_name(page):
    """The element named in the Find the Elements prompt (minus its play button)."""
    return page.locator("#gPrompt").inner_text().replace("▶ Hear it", "").replace("Find:", "").strip()


def current(page):
    """(direction, z) of the card on screen."""
    sym = page.locator("#fcFace .sym")
    if sym.count():
        return "s", BY_SYM[sym.inner_text().strip()][0]
    return "n", BY_NAME[page.locator("#fcFace .nm").inner_text().strip()][0]


def answer(page, right=True, misspell=False, wrong_case=False):
    d, z = current(page)
    sym, name, cat = EL[z]
    if d == "s":
        nm = name if right else "Xenon"
        if misspell:
            nm = name[:-1] + ("x" if name[-1] != "x" else "y")
        page.fill("#in-name", nm.lower())
        page.click(f'#fcInputs .cat[data-c="{cat}"]')
    else:
        page.fill("#in-sym", sym.lower() if wrong_case else (sym if right else "Zz"))
    page.click("#fcCheck")
    return d, z


def stored(page):
    return page.evaluate(f"() => JSON.parse(localStorage.getItem('{KEY}') || '{{}}')")


def run(browser, label, viewport):
    ctx = browser.new_context(viewport=viewport, has_touch=label == "phone")
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(PAGE)

    check(page.locator("#jswarn").is_hidden(), "JS did not start")
    check(page.locator("#nostore").is_hidden(), "storage banner shown with working storage")
    check(page.locator('a[href="/"]').count() >= 1, "missing link back to the hub")
    check(page.locator("#stNew").inner_text() == "12", "set 1-15 should offer 12 new cards on day one")
    page.click('[data-namemode="type"]')  # ladder is tested separately in ladder(); this flow types every answer

    # --- review: right answer moves the card up a box ---
    page.click("#startReview")
    d, z = answer(page)
    check("right" in page.locator(".result").get_attribute("class"), "correct answer not marked right")
    if label == "laptop":   # hear it: the answer's play button loads that element's clip
        page.click("#fcAnswer .play")
        page.wait_for_function("() => { const a = window.__tklearn.audio(); return a && (a.readyState >= 2 || a.error); }", timeout=10000)
        src, err = page.evaluate("() => [window.__tklearn.audio().src, window.__tklearn.audio().error && window.__tklearn.audio().error.code]")
        check(not err and src.endswith(f"/audio/{z:02d}-{EL[z][1].lower()}.mp3"), f"play button loaded {src} (error {err})")
    check(stored(page)["items"][f"{z}{d}"]["b"] == 2, "correct answer should move a new card to box 2")
    page.click("#fcNext")

    # --- spelling doesn't count: a near-miss name is right, and the real spelling is shown ---
    d, z = current(page)
    check(d == "s", "second new card should be symbol -> name")
    answer(page, misspell=True)
    check("right" in page.locator(".result").get_attribute("class"), "near-miss spelling should count as right")
    check(EL[z][1] in page.locator("#fb-name").inner_text(), "near-miss should show the correct spelling")
    check(stored(page)["items"][f"{z}{d}"]["b"] == 2, "near-miss spelling should promote like a right answer")
    page.click("#fcNext")

    # --- miss: card returns within the next few cards in the same session ---
    d, z = answer(page, right=False)
    check("wrong" in page.locator(".result").get_attribute("class"), "wrong answer not marked wrong")
    missed = (d, z)
    seen_again = False
    for _ in range(5):
        page.click("#fcNext")
        if current(page) == missed:
            seen_again = True
            break
        answer(page)
    check(seen_again, "missed card did not come back within 4 cards")
    answer(page)  # clears it; the schedule keeps the miss (box 1)
    check(stored(page)["items"][f"{missed[1]}{missed[0]}"]["b"] == 1, "re-answering a missed card must not promote it")

    # --- reload keeps progress ---
    before = stored(page)["items"]
    page.reload()
    check(stored(page)["items"] == before, "progress lost on reload")
    check(int(page.locator("#stNew").inner_text()) < 12, "new-card count did not go down after reviewing")

    # --- tomorrow: correct cards from today come due ---
    page.evaluate("() => window.__tklearn.shiftDays(1)")
    check(int(page.locator("#stDue").inner_text()) >= 1, "nothing due the next day")

    # --- symbol case matters: "co" is close (must fix to "Co"), never right; fixing = 'fixed' ---
    page.click("#startPractice")
    for _ in range(30):
        d, z = current(page)
        if d == "n":
            answer(page, wrong_case=True)
            check("close" in page.locator("#f-sym").get_attribute("class"), "wrong-case symbol not marked close")
            check(page.locator("#fcNext").is_hidden(), "wrong-case symbol should not finish the card")
            page.fill("#in-sym", EL[z][0])
            page.click("#fcCheck")
            check("close" in page.locator(".result").get_attribute("class"), "fixed symbol should say it stays at the same level")
            break
        answer(page)
        page.click("#fcNext")
    else:
        raise AssertionError("no name -> symbol card found in practice")
    page.click("#fcStop")

    # --- category: tap a color only (no typing option) ---
    check(page.locator("[data-catmode]").count() == 0 and page.locator("#in-cat").count() == 0, "category must be tap-only")
    page.click("#startPractice")
    for _ in range(4):
        d, z = current(page)
        if d == "s":
            wrongcat = next(c for c in ("metal", "nonmetal", "metalloid") if c != EL[z][2])
            page.fill("#in-name", EL[z][1]) if page.locator("#in-name").count() else None
            page.click(f'#fcInputs .cat[data-c="{wrongcat}"]')
            page.click("#fcCheck")
            check("wrong" in page.locator(".result").get_attribute("class"), "wrong color should be graded wrong")
            break
        answer(page)
        page.click("#fcNext")
    page.click("#fcStop")

    # --- game, easy round first: the row is highlighted before any tap ---
    page.click('[data-tab="game"]')
    check(page.locator("#gEasy").is_checked(), "first round of a group should be the easy round")
    check(page.locator("#gPrompt").inner_text().startswith("Find:"), "opening the tab should start a round (no Start press needed)")
    check(page.locator("#gPrompt .findlbl").evaluate("e => getComputedStyle(e).color") == "rgb(30, 138, 68)", "Find: should be green")
    page.click("#gStart")
    name = find_name(page)
    check("rowhint" in page.locator(f'#gBoard [data-z="{BY_NAME[name][0]}"]').get_attribute("class"), "easy round should show the row first")
    for _ in range(15):
        name = find_name(page)
        page.click(f'#gBoard [data-z="{BY_NAME[name][0]}"]')
    check(page.locator("#gPrompt").inner_text() == "Done!", "easy round did not finish")
    check(not page.locator("#gEasy").is_checked(), "after an easy round the next round should be normal")

    # --- normal round: no row until 2 misses; 3 misses reveal it ---
    page.click("#gStart")
    name = find_name(page)
    check(page.locator("#gBoard .rowhint").count() == 0, "normal round should not show the row before misses")
    page.click("#gPrompt .play")   # hear the element being asked for
    page.wait_for_function("() => { const a = window.__tklearn.audio(); return a && (a.readyState >= 2 || a.error); }", timeout=10000)
    zz = BY_NAME[name][0]
    check(page.evaluate(f"() => !window.__tklearn.audio().error && window.__tklearn.audio().src.endsWith('/audio/{zz:02d}-{name.lower()}.mp3')"), "Find prompt should play the named element")
    z = BY_NAME[name][0]
    wrong = next(k for k in (37, 38, 55) if k != z)
    for i in range(3):
        page.click(f'#gBoard [data-z="{wrong}"]')
        if i == 1:
            check("rowhint" in page.locator(f'#gBoard [data-z="{z}"]').get_attribute("class"), "2 misses should show the row")
    check("reveal" in page.locator(f'#gBoard [data-z="{z}"]').get_attribute("class"), "3 misses should reveal the square")
    page.click(f'#gBoard [data-z="{z}"]')
    check(page.locator("#gStatus").inner_text().startswith("1 of 15 found"), "correct tap not counted")
    check("found" in page.locator(f'#gBoard [data-z="{z}"]').get_attribute("class"), "found square not colored")

    # --- backup code round trip ---
    page.click('[data-tab="progress"]')
    check(page.locator("#pBoard .sq").count() >= 118, "progress board missing")
    code = page.input_value("#bkOut")
    items = stored(page)["items"]
    page.click("#bkReset")
    page.click("#bkReset")
    check(stored(page)["items"] == {}, "reset did not clear progress")
    page.fill("#bkIn", code)
    page.click("#bkRestore")
    check(stored(page)["items"] == items, "restore did not bring progress back")

    check(not errors, f"JavaScript errors: {errors}")
    ctx.close()
    print(f"ok  {label}: grading, close/fix, miss returns, reload, schedule, tap mode, game, backup")


def ladder(browser):
    """Step 1 (pick the spelling) -> step 2 (build from chunks) -> step 3 (type; near miss counts)."""
    ctx = browser.new_context()
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(PAGE)
    check(page.locator('[data-namemode="ladder"]').get_attribute("class").count("on"), "step by step should be the default")

    # step 1: a new symbol card offers 3 spellings, one real; decoys are misspellings, never the real name
    page.click("#startReview")
    check("Step 1" in page.locator("#fcStep").inner_text(), "new card should start at step 1")
    opts = page.locator("#fcInputs .opt").all_inner_texts()
    check(len(opts) == 3 and opts.count("Hydrogen") == 1, f"step 1 options wrong: {opts}")
    page.click('#fcInputs .opt:not([data-o="Hydrogen"])')
    page.click('#fcInputs .cat[data-c="nonmetal"]')
    page.click("#fcCheck")
    check("wrong" in page.locator(".result").get_attribute("class"), "picking a misspelling should be wrong")
    check(stored(page)["items"]["1s"]["b"] == 1, "a miss at step 1 keeps the card at box 1")
    page.click("#fcStop")

    # step 2: box 2 -> build the name from chunk tiles (decoy chunks included)
    def due(box):
        page.evaluate(f"""() => {{ localStorage.setItem('{KEY}', JSON.stringify({{items: {{'1s': {{b: {box}, due: 0}}}},
            newDay: 99999999, newCount: 99, set: 'a', catMode: 'type', nameMode: 'ladder', best: {{}}}})); }}""")
        page.reload()
        page.click("#startReview")
    due(2)
    for t in ("hy", "gen", "dro"):                     # wrong order is wrong, and drops the card to box 1
        page.click(f'#tiles .tile[data-t="{t}"]')
    page.click('#fcInputs .cat[data-c="nonmetal"]')
    page.click("#fcCheck")
    check("wrong" in page.locator(".result").get_attribute("class"), "pieces in the wrong order should be wrong")
    check(stored(page)["items"]["1s"]["b"] == 1, "a miss at step 2 should drop the card to box 1")
    due(2)
    check("Step 2" in page.locator("#fcStep").inner_text(), "box 2 card should be at step 2")
    tiles = page.locator("#tiles .tile").all_inner_texts()
    check(sorted(tiles) == sorted(["hy", "dro", "gen", "hi"]), f"chunk tiles wrong: {tiles}")
    page.click('#tiles .tile[data-t="hi"]')          # wrong piece...
    page.click("#built .tile")                        # ...tapped again goes back
    for t in ("hy", "dro", "gen"):
        page.click(f'#tiles .tile[data-t="{t}"]')
    page.click('#fcInputs .cat[data-c="nonmetal"]')
    page.click("#fcCheck")
    check("right" in page.locator(".result").get_attribute("class"), "built name should be right")
    check(stored(page)["items"]["1s"]["b"] == 3, "right at step 2 should move the card to box 3")

    # step 3: box 3 -> type it cold; a near miss counts
    due(3)
    check("Step 3" in page.locator("#fcStep").inner_text(), "box 3 card should be typed")
    page.fill("#in-name", "hydrogin")
    page.click('#fcInputs .cat[data-c="nonmetal"]')
    page.click("#fcCheck")
    check("right" in page.locator(".result").get_attribute("class"), "near miss should count at step 3")
    check(stored(page)["items"]["1s"]["b"] == 4, "typed right should move the card to box 4 (solid)")

    check(not errors, f"JavaScript errors in ladder: {errors}")
    ctx.close()
    print("ok  ladder: pick spelling (miss stays box 1) -> build chunks -> type (near miss counts)")


def sort(browser):
    ctx = browser.new_context(viewport={"width": 1366, "height": 1000})
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(PAGE)
    page.click('[data-tab="sort"]')
    # 1-15: H, Li, Be, B, C, N, Al, Si, P one by one, plus S, I, Sn (border, always in);
    # Na + Mg = metal block, He + O + F + Ne = nonmetal block -> 12 + 2 = 14 things to sort, 18 squares
    check(page.locator("#sBoard .sq.sortable").count() == 18, "set 1-15 sort should have 18 sortable squares")
    nb = sorted(int(x) for x in page.locator("#sBoard .sq.nblk").evaluate_all("els => els.map(e => e.dataset.z)"))
    check(nb == [2, 8, 9, 10], f"He, O, F, Ne should be the nonmetal block in 1-15, got {nb}")
    for z in (16, 53, 50):
        check("sortable" in page.locator(f'#sBoard [data-z="{z}"]').get_attribute("class"), f"element {z} should always be in the sort")
    check(sorted(int(x) for x in page.locator("#sBoard .sq.blk").evaluate_all("els => els.map(e => e.dataset.z)")) == [11, 12], "Na and Mg should be the block in 1-15")

    def tap_place(z, cat):
        page.click(f'#sBoard [data-z="{z}"]')
        page.click(f'#ovals .oval[data-c="{cat}"] h3')

    tap_place(1, "nonmetal")                                   # tap, then tap the oval
    sq = page.locator('#sBoard [data-z="3"]').bounding_box()  # drag lithium into the metal oval
    ov = page.locator('#ovals .oval[data-c="metal"]').bounding_box()
    page.mouse.move(sq["x"] + sq["width"] / 2, sq["y"] + sq["height"] / 2)
    page.mouse.down()
    page.mouse.move(sq["x"] + 40, sq["y"] + 40, steps=4)
    page.mouse.move(ov["x"] + ov["width"] / 2, ov["y"] + ov["height"] / 2, steps=8)
    page.mouse.up()
    check(page.locator('#ovals .oval[data-c="metal"] .chip[data-u="z3"]').count() == 1, "dragging Li to metal failed")
    tap_place(5, "nonmetal")                                   # boron is a metalloid: wrong on purpose
    page.click("#sCheck")
    check(page.locator("#sScore").inner_text().startswith("2 / 14 right"), f"sort score: {page.locator('#sScore').inner_text()}")
    check("wrong" in page.locator('#ovals .chip[data-u="z5"]').get_attribute("class"), "boron in nonmetal should be wrong")
    page.click("#sRetry")
    check(page.locator('#ovals .chip[data-u="z5"]').count() == 0, "send wrong ones back should return boron")
    check("placed" not in page.locator('#sBoard [data-z="5"]').get_attribute("class"), "boron should be back on the table")
    # the block: tapping Na and then the metal oval moves Na AND Mg as one chip
    tap_place(11, "metal")
    check(page.locator('#ovals .oval[data-c="metal"] .chip[data-u="blk"]').inner_text() == "2 metals", "block chip should say 2 metals")
    check(all("placed" in page.locator(f'#sBoard [data-z="{z}"]').get_attribute("class") for z in (11, 12)), "the whole block should leave the table")
    tap_place(8, "nonmetal")   # the nonmetal block: tap O, then the oval, moves He, O, F, Ne together
    check(page.locator('#ovals .oval[data-c="nonmetal"] .chip[data-u="nblk"]').inner_text() == "4 nonmetals", "nonmetal block chip should say 4 nonmetals")
    for z in (4, 5, 6, 7, 13, 14, 15, 16, 53, 50):
        tap_place(z, EL[z][2])
    page.click("#sCheck")
    check(page.locator("#sScore").inner_text().startswith("14 / 14 right"), f"all placed correctly should score 14/14: {page.locator('#sScore').inner_text()}")
    check(page.locator("#sRule").is_visible(), "the staircase rule should appear after a perfect sort")
    # ...and the whole table comes back, every element colored by category, so the full staircase shows
    check(page.locator("#sBoard .sq.found").count() == 118 and page.locator("#sBoard .sq.placed").count() == 0, "perfect sort should color the whole table")
    for z, cat in ((5, "metalloid"), (32, "metalloid"), (52, "metalloid"), (34, "nonmetal"), (54, "nonmetal"), (1, "nonmetal"), (55, "metal"), (84, "metalloid"), (85, "metalloid"), (83, "metal"), (13, "metal")):
        check(cat in page.locator(f'#sBoard [data-z="{z}"]').get_attribute("class").split(), f"element {z} should be colored {cat}")
    for e_z, (_, _, cat) in EL.items():   # the 42 agree with the page's own answer key
        check(cat in page.locator(f'#sBoard [data-z="{e_z}"]').get_attribute("class").split(), f"element {e_z} colored wrong")
    # 16-30: S, Cl, Ar one by one + K..Zn as one block -> 4 things; the block in nonmetal is wrong
    page.click('[data-set="b"]')
    check(page.locator("#sBoard .sq.blk").count() == 12, "K through Zn should be the block in 16-30")
    tap_place(19, "nonmetal")
    page.click("#sCheck")
    check(page.locator("#sScore").inner_text().startswith("0 / 5 right"), f"16-30 score: {page.locator('#sScore').inner_text()}")
    check("wrong" in page.locator('#ovals .chip[data-u="blk"]').get_attribute("class"), "metal block in nonmetal should be wrong")
    check(not errors, f"JavaScript errors in sort: {errors}")
    ctx.close()
    print("ok  sort: tap-place, drag, check, send back, metal block moves as one, perfect -> staircase rule")


def connections_spelling_blank(browser):
    ctx = browser.new_context(viewport={"width": 1366, "height": 900})
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(PAGE)

    # --- Connections, same element: 16 tiles; one group = symbol + name + number + map of one element ---
    page.click('[data-tab="cx"]')
    check(page.locator("#cxGrid .cx").count() == 16, "connections should start with 16 tiles")
    for kind in ("sym", "nm", "num", "map"):
        check(page.locator(f"#cxGrid .cx.{kind}").count() == 4, f"expected 4 {kind} tiles")
    # tiles agree with the answer key: each group's symbol, name and number belong to one element
    for g in range(4):
        texts = {k: page.locator(f'#cxGrid .cx.{k}[data-g="{g}"]').inner_text() for k in ("sym", "nm", "num")}
        z = BY_SYM[texts["sym"]][0]
        check(EL[z][1] == texts["nm"] and texts["num"] == f"#{z}", f"group {g} tiles disagree: {texts}")
        mz = page.locator(f'#cxGrid .cx.map[data-g="{g}"] .sq.hit').get_attribute("data-z")
        check(int(mz) == z, f"group {g} map marks the wrong square")

    def pick(gs):
        for g in gs:
            i = page.locator(f'#cxGrid .cx[data-g="{g}"]:not(.sel)').first
            i.click()
        page.click("#cxSubmit")

    pick([0, 0, 0, 1])
    check(page.locator("#cxMsg").inner_text() == "One away!", "3 of a group should say one away")
    page.click("#cxClear")
    pick([0, 0, 1, 1])
    check(page.locator("#cxMsg").inner_text().startswith("Not a group"), "2+2 should not be a group")
    page.click("#cxClear")
    for g in range(4):
        pick([g] * 4)
    check(page.locator("#cxSolved .cx-solved").count() == 4, "all 4 groups should be solved")
    for lab in page.locator("#cxSolved .lab").all_inner_texts():   # as displayed, so CSS case changes are caught
        sym, name, num = lab.split(" · ")
        check(sym in BY_SYM and BY_SYM[sym][2] == name, f"solved label shows wrong capitals: {lab!r}")
    check(page.locator("#cxMsg").inner_text().startswith("Solved! 2 mistakes"), f"solved message: {page.locator('#cxMsg').inner_text()}")

    # --- Connections, same family: 5 groups of 4 = 3 elements (symbol + name on one tile) + a map of the whole family ---
    page.click('[data-cxmode="fam"]')
    check(page.locator("#cxGrid .cx").count() == 20, "family puzzle should have 20 tiles")
    check(page.locator("#cxGrid .cx.map").count() == 5 and page.locator("#cxGrid .cx.el2").count() == 15, "5 family maps + 15 element tiles")
    fam_all = {"Alkali metals": {3, 11, 19, 37, 55, 87}, "Alkaline": {4, 12, 20, 38, 56, 88}, "Halogens": {9, 17, 35, 53, 85, 117}, "Noble": {2, 10, 18, 36, 54, 86, 118}}
    for g in range(5):
        lit = {int(z) for z in page.locator(f'#cxGrid .cx.map[data-g="{g}"] .sq.hit').evaluate_all("els => els.map(e => e.dataset.z)")}
        els = page.locator(f'#cxGrid .cx.el2[data-g="{g}"] .s2').all_inner_texts()
        check(all(BY_SYM[x][0] in lit for x in els), f"group {g}: elements {els} must be inside their family map")
        for _ in range(4):
            page.locator(f'#cxGrid .cx[data-g="{g}"]:not(.sel)').first.click()
        page.click("#cxSubmit")
    labels = page.locator("#cxSolved .lab").all_inner_texts()
    want = ["Alkali metals (group 1)", "Alkaline earth metals (group 2)", "Transition metals (groups 3-12)", "Halogens (group 17)", "Noble gases (group 18)"]
    check(sorted(labels) == sorted(want), f"family labels: {labels}")
    for lab_el in page.locator("#cxSolved .cx-solved").all():
        lab = lab_el.locator(".lab").inner_text()
        lit = {int(z) for z in lab_el.locator(".sq.hit").evaluate_all("els => els.map(e => e.dataset.z)")}
        for key, zs in fam_all.items():
            if lab.startswith(key):
                check(lit == zs, f"{lab}: map should light exactly {sorted(zs)}, got {sorted(lit)}")
    check(page.locator("#cxMsg").inner_text().startswith("Solved!"), "family puzzle should solve")

    # --- Spelling: three views. Morphemes (default) list every name's meaning exactly once ---
    page.click('[data-tab="spell"]')
    check([b.strip() for b in page.locator("[data-spellview]").all_inner_texts()] == ["Phonemes (sounds)", "Morphemes (meaning)", "Graphemes (letters for a sound)"], "order: phonemes, morphemes, graphemes")
    check("phoneme" in page.locator("#spellDef").inner_text(), "Spelling should open on phonemes")
    page.click('[data-spellview="morph"]')
    check("morpheme" in page.locator("#spellDef").inner_text(), "morpheme view")
    mg = page.locator("#fams .fgroup")
    check(mg.count() == 2 and mg.nth(0).locator("h3").all_inner_texts()[:2] == ['-gen: "maker"', "Symbols from older names"]
          and all(h.startswith("Naming pattern") for h in mg.nth(1).locator("h3").all_inner_texts()), "morphemes first, then naming patterns")
    origins = page.locator("#fams .origins .fname").all_inner_texts()
    check(sorted(origins) == sorted(v[1] for v in EL.values()), "Where each name comes from must list all 42 names once")
    check(page.locator('#fams .fname:has-text("Hydrogen") b').first.inner_text() == "gen", "morpheme -gen not marked in Hydrogen")
    check("hydro + gen → hydrogen" in page.locator("#fams").inner_text() and "hydro + gen = water + maker" in page.locator("#fams").inner_text(), "word sum and meaning sum for hydrogen")
    lat = page.locator('#fams .fam:has(h3:has-text("Symbols from older names")) .fname')
    check(lat.count() == 9 and lat.first.inner_text() == "Sodium Na = natrium", f"Latin-symbol labels: {lat.all_inner_texts()[:2]}")
    check(lat.first.locator(".lat").inner_text() == "Na = natrium", "symbol and Latin should be in their own colored span")
    page.click('#fams .origins .fname:has-text("Potassium")')
    det = page.locator("#fdetail").inner_text()
    check("K · Potassium · 19" in det and "potash" in det, "tapping a name should show its details and meaning")
    page.click("#fdetail .play")
    page.wait_for_function("() => { const a = window.__tklearn.audio(); return a && (a.readyState >= 2 || a.error); }", timeout=10000)
    check(page.evaluate("() => !window.__tklearn.audio().error && window.__tklearn.audio().src.endsWith('/audio/19-potassium.mp3')"), "Spelling detail should play potassium")
    check("poh-TASS-ee-um" in det and "/poʊˈtæsiəm/" in det, "details should show how it sounds")
    # Graphemes: boxes; consonant + e is one grapheme (EBLI style), no "_" notation
    page.click('[data-spellview="graph"]')
    check("1 to 4 letters" in page.locator("#spellDef").inner_text(), "grapheme definition missing")
    allg = page.locator("#fams .allg .fname")
    check(sorted(allg.all_inner_texts()) == sorted(v[1] for v in EL.values()), "all-42 grapheme card must spell all 42 names")
    check(page.locator('#fams .allg .fname:has-text("Phosphorus") .gr.multi').all_inner_texts() == ["Ph", "ph", "or"], "Phosphorus graphemes should be Ph, ph, or")
    check(page.locator('#fams .allg .fname:has-text("Chlorine") .gr.multi').all_inner_texts() == ["Ch", "ne"], "Chlorine: ch and ne are graphemes; o + r are two sounds (/ɔr/)")
    check("_" not in page.locator("#tab-spell").inner_text(), "no underscore notation")
    # Phonemes: one sound/many spellings and one spelling/many sounds
    page.click('[data-spellview="phon"]')
    check("more than one spelling" in page.locator("#spellDef").inner_text(), "phoneme definition missing")
    groups = page.locator("#fams .fgroup")
    check(groups.count() == 2 and groups.nth(0).locator(".fam h3").all_inner_texts()[0].startswith("Same Sound")
          and all(h.startswith("Same Spelling") for h in groups.nth(1).locator(".fam h3").all_inner_texts()), "phoneme cards should be in two groups")
    check(page.locator('#fams .fam').first.locator('.fname b').all_inner_texts() == ["C", "C", "C", "c", "K", "Ch", "Ch", "ck", "c"], "the /k/ card should mark each spelling")
    page.click('[data-spellview="morph"]')

    # --- Find the Elements on a blank board: no symbols until found ---
    page.click('[data-tab="game"]')
    page.click('[data-gboard="blank"]')
    check(page.locator('#gBoard [data-z="26"]').inner_text().strip() == "", "blank board should show nothing in squares")
    page.click('[data-gboard="num"]')
    check(page.locator('#gBoard [data-z="26"]').inner_text().strip() == "26", "numbers-only board should show just the number")
    page.uncheck("#gEasy")
    page.click("#gStart")
    name = find_name(page)
    z = BY_NAME[name][0]
    page.click(f'#gBoard [data-z="{z}"]')
    check(EL[z][0] in page.locator(f'#gBoard [data-z="{z}"]').inner_text(), "a found square should show its symbol")
    check(page.locator("#gStatus").inner_text().startswith("1 of 15 found"), "numbers-only board: tap not counted")

    check(not errors, f"JavaScript errors: {errors}")
    ctx.close()
    print("ok  connections (element + family), spelling families, numbers-only/blank board")


def data_checks():
    """Static checks on the page's data: letter teams spell each name, and ladder pieces never split a team."""
    html = (pathlib.Path(__file__).resolve().parent.parent / "index.html").read_text()
    graph = dict(re.findall(r"(\w+): '([A-Za-z* ]+)'", html[html.index("var GRAPH = {"):html.index("// How each name sounds")]))
    ladder = {int(z): ch for z, ch in re.findall(r"(\d+): \['([a-z ]+)',", html[html.index("var LADDER = {"):html.index("EL.forEach(function (e) {\n    var L")])}
    check(sorted(graph) == sorted(v[1] for v in EL.values()), "letter teams must cover all 42 names")
    check(sorted(ladder) == sorted(EL), "ladder must cover all 42 elements")
    for z, (_, name, _) in EL.items():
        toks = graph[name].split()
        check("".join(toks) == name, f"graphemes don't spell {name}")
        check(all(1 <= len(t) <= 4 for t in toks), f"{name}: a grapheme must be 1-4 letters")
        bad, pos, split_start = set(), 0, None
        for t in toks:
            letters = t.replace("*", "")
            bad.update(range(pos + 1, pos + len(letters)))   # inside a multi-letter team
            if t.endswith("*"):
                split_start = pos
            if t.startswith("*"):
                bad.update(range(split_start + 1, pos + 1))   # between the halves of a split team
            pos += len(letters)
        cuts, pos = set(), 0
        for piece in ladder[z].split()[:-1]:
            pos += len(piece)
            cuts.add(pos)
        check(not (cuts & bad), f"ladder pieces for {name} split a letter team: {ladder[z]} vs {graph[name]}")
    # Pronunciations (IPA, checked against the CMU Pronouncing Dictionary when written) back the tips' sound claims.
    say = dict(re.findall(r"(\w+): \['([^']+)', '[^']+'\]", html[html.index("var SAY = {"):html.index("function teams")]))
    check(sorted(say) == sorted(v[1] for v in EL.values()), "every name needs a pronunciation")
    tip = re.search(r"All spelled <b>-on</b>([^']+)'", html).group(1)
    for n in ("Boron", "Neon", "Argon", "Krypton", "Radon"):
        check(n in tip.split("/ɑn/")[1].split("/ən/")[0] and say[n].endswith("ɑn"), f"-on tip: {n} should be listed under /ɑn/ and end in /ɑn/")
    for n in ("Carbon", "Silicon"):
        check(n in tip.split("/ən/")[1] and say[n].endswith("ən"), f"-on tip: {n} should be listed under /ən/ and end in /ən/")
    # Every element has its recorded clip: audio/NN-name.mp3, a real MP3.
    for z, (_, name, _) in EL.items():
        clip = pathlib.Path(__file__).resolve().parent.parent / "audio" / f"{z:02d}-{name.lower()}.mp3"
        check(clip.exists() and clip.stat().st_size > 2000, f"missing or empty clip: {clip.name}")
        head = clip.read_bytes()[:3]
        check(head == b"ID3" or (head[0] == 0xFF and head[1] & 0xE0 == 0xE0), f"{clip.name} is not an MP3")
    # Wording rule for learning tools: explain sound-to-letter mappings; never label spellings "tricky",
    # "sight/heart words", or suggest a word can't be sounded out. Code comments may state the rule itself.
    banned = re.compile(r"tricky|sight words?|heart words?|sneaky|whole word|irregular|memori[sz]e|doesn.t follow", re.I)
    readme = (pathlib.Path(__file__).resolve().parent.parent / "README.md").read_text()
    for src, text in (("index.html", html), ("README.md", readme)):
        for line in text.splitlines():
            if line.strip().startswith("//"):
                continue
            m = banned.search(line)
            check(not m, f"{src}: banned wording {m.group(0)!r} in: {line.strip()[:90]}" if m else "")
    # Every phoneme-card claim must be true in the page's American IPA (SAY, checked against CMU):
    # "/x/: one sound ..." cards -> every listed name contains /x/; one-spelling cards -> each name has the stated sound.
    ph = html[html.index("    phon: {"):html.index("  // Where each name comes from")]
    cards = re.findall(r"\['([^']+)', '(?:[^'\\]|\\.)*',\s*'([^']+)'\]", ph)
    check(len(cards) == 14, f"expected the phoneme cards, found {len(cards)}")
    check(all(c[0].startswith(("Same Sound, Different Spelling: ", "Same Spelling, Different Sound: ")) for c in cards), "phoneme cards must be titled Same Sound, Different Spelling / Same Spelling, Different Sound")
    check(sum(c[0].startswith("Same Sound") for c in cards) == 8, "expected 8 Same Sound, Different Spelling cards")
    def has(name, sound):
        ipa = say[name].replace("ˈ", "").replace("ɝ", "ɚ")  # stressed /ɝ/ and unstressed /ɚ/ are the same r-colored vowel
        if sound == "ɪ":  # short i on its own, not the second half of /aɪ/, /eɪ/, /ɔɪ/
            ipa = ipa.replace("aɪ", "").replace("eɪ", "").replace("ɔɪ", "")
        return sound in ipa
    one_sound = {"/k/": "k", "/f/": "f", "/s/": "s", "/z/": "z", "/ɪ/": "ɪ", "/aɪ/": "aɪ", "/i/": "i", "/ɚ/": "ɚ"}
    for title, items in cards:
        key = title.split(": ")[-1] if title.startswith("Same Sound, Different Spelling") else None
        if key in one_sound:
            for w in items.split():
                n = w.replace("[", "").replace("]", "")
                check(has(n, one_sound[key]), f"phoneme card {title!r}: {n} /{say[n]}/ has no {one_sound[key]}")
    stated = {  # one spelling, more than one sound: the sound each name is said to have
        "Carbon": "k", "Silicon": "k", "Calcium": "ls",
        "Hydrogen": "dʒ", "Nitrogen": "dʒ", "Oxygen": "dʒ", "Gold": "ɡ", "Argon": "ɡ", "Magnesium": "z",
        "Sodium": "s", "Krypton": "ɪp", "Beryllium": "rɪ", "Mercury": "ɚi", "Lithium": "lɪ", "Iron": "aɪ", "Chlorine": "rin",
    }
    for n, snd in stated.items():
        check(has(n, snd), f"sound claim: {n} /{say[n]}/ should contain {snd}")
    check(say["Hydrogen"].replace("ˈ", "").startswith("haɪ") and "ksə" in say["Oxygen"], "y claims: Hydrogen 'eye', Oxygen 'uh'")
    origin = dict(re.findall(r"(\w+): '([^']+)'", html[html.index("var ORIGIN = {"):html.index("var NAMEZ")]))
    check(sorted(origin) == sorted(v[1] for v in EL.values()), "every name needs a meaning (ORIGIN)")
    for n, o in origin.items():   # the language goes right after the word: "iodes (Greek) = violet", not "iodes = violet (Greek)"
        check(not re.search(r"= [^;]*\((Greek|Latin|German|Spanish)\)", o), f"{n}: put the language right after the word: {o}")
    print("ok  data: 42 recorded clips; phoneme claims match the IPA; graphemes (1-4 letters) spell all 42 names; no ladder piece splits a team; -on sound claims match the IPA")


def blocked_storage(browser):
    ctx = browser.new_context()
    ctx.add_init_script("""Object.defineProperty(window, 'localStorage', { get() { throw new Error('blocked'); } });""")
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(PAGE)
    check(page.locator("#nostore").is_visible(), "blocked storage should show the warning banner")
    page.click('[data-namemode="type"]')
    page.click("#startReview")
    answer(page)
    check(page.locator(".result").count() == 1, "cards should still work without storage")
    check(not errors, f"JavaScript errors with storage blocked: {errors}")
    ctx.close()
    print("ok  storage blocked: banner shown, cards still work")


def main():
    data_checks()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for label, vp in VIEWPORTS.items():
                run(browser, label, vp)
            ladder(browser)
            sort(browser)
            connections_spelling_blank(browser)
            blocked_storage(browser)
        finally:
            browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
