from __future__ import annotations

from pathlib import Path


_REAL_PACKAGE = Path(__file__).resolve().parents[1] / "APLICACION" / "easy_deploy_app"
__path__ = [str(_REAL_PACKAGE)]
