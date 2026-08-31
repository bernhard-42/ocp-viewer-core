"""Extract three-cad-viewer's change-notification name table.

Usage:  python tools/extract_notifications.py <path-to-three-cad-viewer>

Writes tests/fixtures/three_cad_viewer_notifications.json. Run after upgrading the
renderer, then run the tests: a new or renamed key shows up as a failure rather than
as an option that silently does nothing.
"""

import json
import pathlib
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit(__doc__)

source = pathlib.Path(sys.argv[1]) / "src" / "core" / "viewer-state.ts"
text = source.read_text()

# Scope to STATE_TO_NOTIFICATION_KEY. Scraping the whole file silently picks up
# unrelated object literals - `activeTab: "tree"` at another declaration once
# overwrote the real `activeTab: "tab"` mapping, which is the class of error this
# table exists to prevent.
start = text.index("STATE_TO_NOTIFICATION_KEY")
brace = text.index("{", start)
depth, i = 0, brace
while True:
    depth += (text[i] == "{") - (text[i] == "}")
    i += 1
    if depth == 0:
        break
body = text[brace:i]
pairs = dict(re.findall(r'(?m)^\s*(\w+):\s*"([a-z0-9_]+)",', body))
target = pathlib.Path(__file__).parent.parent / "tests" / "fixtures" / "three_cad_viewer_notifications.json"
target.write_text(json.dumps(pairs, indent=1, sort_keys=True) + "\n")
print(f"{len(pairs)} entries -> {target}")
