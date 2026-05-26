from __future__ import annotations

import sys
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent / "APLICACION"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from easy_deploy_app.bridge.bridge_server import main


if __name__ == "__main__":
    main()
