#!/usr/bin/env python3
"""Static checks for the Drishti website. No build step, so this is the build:
every JSON file must parse, and every local file a page points at must exist.
Run from the repository root. Exits non-zero on the first category that fails."""

import json
import os
import re
import sys
from urllib.parse import unquote, urlparse

ROOT = os.getcwd()
SKIP_PREFIX = ("http://", "https://", "mailto:", "tel:", "data:", "javascript:", "//", "#")
REF = re.compile(r'(?:href|src)\s*=\s*["\']([^"\']+)["\']', re.I)

# Local files a page points at that are known to be absent on main today.
# The check stays green on them so the gate can go on, and prints them every
# run so they do not go quiet. Deleting a line here is the fix, not adding one:
# nothing new may be added without Avi saying so.
KNOWN_MISSING = {
    # The four Maakav gallery screenshots have 404'd on the live site since at
    # least 31 Aug 2026; index.html hides them with onerror, so the gallery
    # renders empty. Waiting on the images (or on removing the gallery).
    ("index.html", "/screenshots/maakav-1.png"),
    ("index.html", "/screenshots/maakav-2.png"),
    ("index.html", "/screenshots/maakav-3.png"),
    ("index.html", "/screenshots/maakav-4.png"),
}

errors = []
known = []


def rel_files(ext):
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in (".git", ".github", "node_modules")]
        for name in filenames:
            if name.endswith(ext):
                yield os.path.relpath(os.path.join(dirpath, name), ROOT)


# 1. JSON parses
json_files = sorted(rel_files(".json"))
for path in json_files:
    try:
        with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
            json.load(fh)
    except Exception as exc:
        errors.append(f"{path}: invalid JSON: {exc}")
print(f"json:  {len(json_files)} file(s) parsed")

# 2. Local references resolve
html_files = sorted(rel_files(".html"))
checked = 0
for path in html_files:
    with open(os.path.join(ROOT, path), encoding="utf-8", errors="replace") as fh:
        body = fh.read()
    base = os.path.dirname(path)
    for raw in REF.findall(body):
        ref = raw.strip()
        if not ref or ref.startswith(SKIP_PREFIX):
            continue
        if "${" in ref or "{{" in ref:
            continue  # a JS template literal, resolved in the browser
        target = unquote(urlparse(ref).path)
        if not target:
            continue
        candidate = target[1:] if target.startswith("/") else os.path.normpath(os.path.join(base, target))
        checked += 1
        full = os.path.join(ROOT, candidate)
        if os.path.isdir(full):
            full = os.path.join(full, "index.html")
        if not os.path.exists(full):
            if (path, ref) in KNOWN_MISSING:
                known.append(f"{path}: {ref}")
            else:
                errors.append(f"{path}: missing local file {ref!r}")
print(f"links: {checked} local reference(s) in {len(html_files)} page(s)")

if known:
    print(f"\nknown-missing, allowlisted ({len(known)}):")
    for k in known:
        print(f"  - {k}")

if errors:
    print(f"\nFAILED ({len(errors)}):", file=sys.stderr)
    for e in errors:
        print(f"  - {e}", file=sys.stderr)
    sys.exit(1)
print("\nOK")
