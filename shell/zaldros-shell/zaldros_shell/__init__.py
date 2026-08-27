"""Zaldros Shell — Windows 11-style desktop shell prototype (Qt 6 / QML)."""
__version__ = "0.1.0"

import os as _os
import sys as _sys
from pathlib import Path as _Path


def _add_backend_to_path() -> str:
    """Make `zaldros_backend` importable however the shell was started.

    Three layouts, one resolver — the same shape as `_data_dir()` and `_assets_dir()`, and for the
    same reason: run #24 died at startup because the ISO's layout was assumed instead of resolved.
      * the repository: `<repo>/backend/zaldros_backend`
      * the ISO:        `/opt/zaldros/zaldros_backend` (already on PYTHONPATH, nothing to do)
      * an override:    ZALDROS_BACKEND
    """
    candidates = [_Path(_os.environ["ZALDROS_BACKEND"])] if _os.environ.get("ZALDROS_BACKEND") else []
    here = _Path(__file__).resolve()
    candidates += [here.parents[3] / "backend", here.parents[1], _Path("/opt/zaldros")]
    for path in candidates:
        if (path / "zaldros_backend" / "__init__.py").is_file():
            if str(path) not in _sys.path:
                _sys.path.insert(0, str(path))
            return str(path)
    return ""


BACKEND_PATH = _add_backend_to_path()
