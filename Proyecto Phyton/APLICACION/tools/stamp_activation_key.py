# -*- coding: utf-8 -*-
"""Genera la clave de activacion de build y actualiza solo su hash."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONSTANTS_PATH = ROOT / "easy_deploy_app" / "constants.py"
LICENSE_BUILD_PATH = ROOT / "easy_deploy_app" / "license_build.py"


def _read_build_id() -> str:
    text = LICENSE_BUILD_PATH.read_text(encoding="utf-8")
    match = re.search(r'BUILD_ID\s*=\s*"([^"]+)"', text)
    if not match:
        raise RuntimeError("No se pudo leer BUILD_ID desde license_build.py")
    return match.group(1)


def _developer_desktop() -> Path:
    userprofile = os.environ.get("USERPROFILE")
    if userprofile:
        desktop = Path(userprofile) / "Desktop"
        desktop.mkdir(parents=True, exist_ok=True)
        return desktop
    return Path.home() / "Desktop"


def _write_hash_to_constants(sha256_value: str) -> None:
    text = CONSTANTS_PATH.read_text(encoding="utf-8")
    replacement = f'DEFAULT_LICENSE_SHA256 = "{sha256_value}"'
    updated, count = re.subn(
        r'DEFAULT_LICENSE_SHA256\s*=\s*"[a-fA-F0-9]{64}"',
        replacement,
        text,
        count=1,
    )
    if count != 1:
        raise RuntimeError("No se pudo actualizar DEFAULT_LICENSE_SHA256 en constants.py")
    CONSTANTS_PATH.write_text(updated, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    args = parser.parse_args()

    build_id = _read_build_id()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    machine = os.environ.get("COMPUTERNAME") or "DEV"
    user = os.environ.get("USERNAME") or "developer"
    key = f"ED-{machine}-{stamp}-{build_id[:8]}"
    key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()

    _write_hash_to_constants(key_hash)

    key_path = _developer_desktop() / f"EASYDEPLOY_CLAVE_ACTIVACION_v{args.version}.txt"
    key_path.write_text(
        "\n".join(
            [
                "EASY DEPLOY - CLAVE DE ACTIVACION DE COMPILACION",
                f"Version: {args.version}",
                f"Fecha local: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Equipo: {machine}",
                f"Usuario: {user}",
                "",
                "Clave generada SOLO en este equipo de desarrollo:",
                key,
                "",
                "No incluir este archivo en el instalador ni entregarlo al cliente.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(str(key_path))


if __name__ == "__main__":
    main()
