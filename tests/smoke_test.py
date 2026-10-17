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

    # --- review: right answer moves the card up a box ---
    page.click("#startReview")
    d, z = answer(page)
    check("right" in page.locator(".result").get_attribute("class"), "correct answer not marked right")
    check(stored(page)["items"][f"{z}{d}"]["b"] == 2, "correct answer should move a new card to box 2")
    page.click("#fcNext")

    # --- spelling: close, fixable, counts as 'fixed' (stays in box 1) ---
    d, z = current(page)
    if d == "s":
        answer(page, misspell=True)
        check("close" in page.locator("#f-name").get_attribute("class"), "misspelling not marked close")
        check(page.locator("#fcNext").is_hidden(), "close answer should allow a fix before moving on")
        page.fill("#in-name", EL[z][1])
    else:
        answer(page, wrong_case=True)
        check("close" in page.locator("#f-sym").get_attribute("class"), "wrong-case symbol not marked close")
        page.fill("#in-sym", EL[z][0])
    page.click("#fcCheck")
    check("close" in page.locator(".result").get_attribute("class"), "fixed answer should say it stays at the same level")
    check(stored(page)["items"][f"{z}{d}"]["b"] == 1, "fixed answer should not promote the card")
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

    # --- symbol case matters: "co" is close (must fix to "Co"), never right ---
    page.click("#startPractice")
    for _ in range(30):
        d, z = current(page)
        if d == "n":
            answer(page, wrong_case=True)
            check("close" in page.locator("#f-sym").get_attribute("class"), "wrong-case symbol not marked close")
            check(page.locator("#fcNext").is_hidden(), "wrong-case symbol should not finish the card")
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


def blocked_storage(browser):
    ctx = browser.new_context()
    ctx.add_init_script("""Object.defineProperty(window, 'localStorage', { get() { throw new Error('blocked'); } });""")
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(PAGE)
    check(page.locator("#nostore").is_visible(), "blocked storage should show the warning banner")
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
            blocked_storage(browser)
        finally:
            browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
