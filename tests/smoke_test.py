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
        page.fill("#in-cat", cat)
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

    # --- category by tapping colors ---
    page.click('[data-catmode="tap"]')
    page.click("#startPractice")
    for _ in range(4):
        d, z = current(page)
        if d == "s":
            page.fill("#in-name", EL[z][1])
            page.click(f'#fcInputs .cat[data-c="{EL[z][2]}"]')
            page.click("#fcCheck")
            check("right" in page.locator(".result").get_attribute("class"), "tap-a-color answer not graded right")
            break
        answer(page)
        page.click("#fcNext")
    page.click("#fcStop")
    page.click('[data-catmode="type"]')

    # --- game: prompt by name, tap the right square; 3 misses reveal it ---
    page.click('[data-tab="game"]')
    page.click("#gStart")
    name = re.sub(r"^Find:\s*", "", page.locator("#gPrompt").inner_text()).strip()
    z = BY_NAME[name][0]
    wrong = next(k for k in (37, 38, 55) if k != z)
    for _ in range(3):
        page.click(f'#gBoard [data-z="{wrong}"]')
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
    page.fill("#in-cat", "nonmetal")
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
    page.fill("#in-cat", "nonmetal")
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
    page.fill("#in-cat", "nonmetal")
    page.click("#fcCheck")
    check("right" in page.locator(".result").get_attribute("class"), "built name should be right")
    check(stored(page)["items"]["1s"]["b"] == 3, "right at step 2 should move the card to box 3")

    # step 3: box 3 -> type it cold; a near miss counts
    due(3)
    check("Step 3" in page.locator("#fcStep").inner_text(), "box 3 card should be typed")
    page.fill("#in-name", "hydrogin")
    page.fill("#in-cat", "nonmetal")
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
    check(page.locator("#sBoard .sq.sortable").count() == 15, "set 1-15 should have 15 sortable squares")

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
    check(page.locator('#ovals .oval[data-c="metal"] .chip[data-z="3"]').count() == 1, "dragging Li to metal failed")
    tap_place(5, "nonmetal")                                   # boron is a metalloid: wrong on purpose
    page.click("#sCheck")
    check(page.locator("#sScore").inner_text().startswith("2 / 15 right"), f"sort score: {page.locator('#sScore').inner_text()}")
    check("wrong" in page.locator('#ovals .chip[data-z="5"]').get_attribute("class"), "boron in nonmetal should be wrong")
    page.click("#sRetry")
    check(page.locator('#ovals .chip[data-z="5"]').count() == 0, "send wrong ones back should return boron")
    check("placed" not in page.locator('#sBoard [data-z="5"]').get_attribute("class"), "boron should be back on the table")
    for z in range(1, 16):
        if z in (1, 3):
            continue
        tap_place(z, EL[z][2])
    page.click("#sCheck")
    check(page.locator("#sScore").inner_text().startswith("15 / 15 right"), "all placed correctly should score 15/15")
    check(page.locator("#sRule").is_visible(), "the staircase rule should appear after a perfect sort")
    check(not errors, f"JavaScript errors in sort: {errors}")
    ctx.close()
    print("ok  sort: tap-place, drag, check, send back, perfect -> staircase rule")


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
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for label, vp in VIEWPORTS.items():
                run(browser, label, vp)
            ladder(browser)
            sort(browser)
            blocked_storage(browser)
        finally:
            browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
