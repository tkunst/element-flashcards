#!/usr/bin/env python3
"""Static checks for a tklearn study-resource page (stdlib only).

Shared by tkunst.github.io and every resource repo; keep the copies identical.
Run from the repo root: python3 scripts/site_guard.py

Checks every tracked *.html (and *.md for the text rules):
  1. No em-dashes (public, bylined writing).
  2. No outside subresources: no <script src>, stylesheet, <img>, <iframe>,
     CSS url()/@import, or fetch() to http(s). The privacy panel promises that
     nothing loads from anywhere else.
  3. Only the published contact address appears (hello@trishakunst.com).
  4. Any page that mentions AP carries the College Board trademark notice.
  5. Basic page hygiene: lang, <title>, viewport meta, alt on every <img>.
  6. Resource pages (not the hub) link back to the hub ("/").

Exit 1 with a list of problems if anything fails.
"""
import re
import subprocess
import sys

CONTACT = "hello@trishakunst.com"
AP_NOTICE = "is a trademark registered by the College Board"
HUB_REPO = "tkunst.github.io"

EXTERNAL_SUBRESOURCE = [
    (r'<script\b[^>]*\bsrc\s*=\s*["\']?(?:https?:)?//', "external <script src>"),
    (r'<link\b[^>]*\bhref\s*=\s*["\']?(?:https?:)?//', "external <link href> (stylesheet/font/preload)"),
    (r'<(?:img|iframe|video|audio|source|embed|object)\b[^>]*\b(?:src|data)\s*=\s*["\']?(?:https?:)?//', "external media/iframe"),
    (r'url\(\s*["\']?(?:https?:)?//', "external CSS url()"),
    (r'@import\s+(?:url\()?\s*["\']?(?:https?:)?//', "external CSS @import"),
    (r'\bfetch\(\s*["\'](?:https?:)?//', "fetch() to an outside host"),
]
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Mentions of the AP program ("AP World", "AP®", "AP exam"), not words like "APP".
AP_MENTION = re.compile(r"\bAP(?:®|&reg;|\s+[A-Z])")


def tracked(*globs):
    out = subprocess.run(["git", "ls-files", *globs], capture_output=True, text=True, check=True).stdout
    return [p for p in out.splitlines() if p]


def strip_data_uris(s):
    # Embedded images are megabytes of base64; nothing to check inside them.
    return re.sub(r"data:[a-z/+.-]+;base64,[A-Za-z0-9+/=\s]+", "data:", s)


def line_of(text, idx):
    return text.count("\n", 0, idx) + 1


def main():
    repo = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True).stdout.strip()
    is_hub = repo.rstrip("/").endswith("/" + HUB_REPO)
    problems = []

    for path in tracked("*.html", "*.md"):
        text = strip_data_uris(open(path, encoding="utf-8").read())
        for m in re.finditer("—", text):
            problems.append(f"{path}:{line_of(text, m.start())}: em-dash (use a period, comma, colon, or parentheses)")
        for m in EMAIL.finditer(text):
            if m.group(0).lower() != CONTACT:
                problems.append(f"{path}:{line_of(text, m.start())}: email address other than {CONTACT}")

    for path in tracked("*.html"):
        raw = open(path, encoding="utf-8").read()
        text = strip_data_uris(raw)
        for pat, label in EXTERNAL_SUBRESOURCE:
            for m in re.finditer(pat, text, re.I):
                problems.append(f"{path}:{line_of(text, m.start())}: {label}")
        if AP_MENTION.search(text) and AP_NOTICE not in text:
            problems.append(f"{path}: mentions AP but lacks the College Board trademark notice")
        if not re.search(r"<html\b[^>]*\blang=", text, re.I):
            problems.append(f"{path}: <html> has no lang attribute")
        if not re.search(r"<title>\s*\S", text, re.I):
            problems.append(f"{path}: missing or empty <title>")
        if not re.search(r'<meta\b[^>]*name=["\']viewport', text, re.I):
            problems.append(f"{path}: missing viewport meta (phones/iPads)")
        for m in re.finditer(r"<img\b[^>]*>", text, re.I):
            if not re.search(r"\balt\s*=", m.group(0), re.I):
                problems.append(f"{path}:{line_of(text, m.start())}: <img> without alt text")
        if not is_hub and path == "index.html" and not re.search(r'<a\b[^>]*href=["\']/["\']', text):
            problems.append(f'{path}: no link back to the hub (<a href="/">)')

    if problems:
        print("site_guard: FAILED")
        for p in problems:
            print("  - " + p)
        return 1
    print("site_guard: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
