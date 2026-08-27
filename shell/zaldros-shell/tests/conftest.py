"""Make both packages importable however pytest was started.

The shell and the backend are sibling packages (`shell/zaldros-shell/zaldros_shell` and
`backend/zaldros_backend`), and on the ISO they end up side by side in /opt/zaldros. The tests run
from the shell directory, so the backend has to be put on the path here — the same thing
`zaldros_shell/__init__.py` does at runtime, done once for tests that import the backend without
importing the shell.
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

for path in (REPO / "shell" / "zaldros-shell", REPO / "backend"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
