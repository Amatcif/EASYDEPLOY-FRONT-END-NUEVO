# -*- coding: utf-8 -*-
"""Regenera la marca de compilacion usada por la licencia local."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "easy_deploy_app" / "license_build.py"
SIGNING_KEY = b"EasyDeploy-build-license-v1::Adrian-Mata-Cifre::2026"


def main() -> None:
    build_dt = datetime.now(timezone.utc).replace(microsecond=0)
    build_utc = build_dt.isoformat().replace("+00:00", "Z")
    build_epoch = int(build_dt.timestamp())
    build_nonce = secrets.token_hex(16)
    build_id = hashlib.sha256(f"{build_utc}|{build_nonce}".encode("utf-8")).hexdigest()[:24]
    signature_payload = f"{build_utc}|{build_epoch}|{build_id}"
    build_signature = hmac.new(
        SIGNING_KEY,
        signature_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    TARGET.write_text(
        "\n".join(
            [
                "# -*- coding: utf-8 -*-",
                '"""Datos de licencia generados en la compilacion.',
                "",
                "No edites este archivo a mano. Se actualiza antes de crear el ejecutable.",
                '"""',
                "",
                f'BUILD_UTC = "{build_utc}"',
                f"BUILD_EPOCH = {build_epoch}",
                f'BUILD_ID = "{build_id}"',
                f'BUILD_SIGNATURE = "{build_signature}"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Licencia de build generada: {build_utc} ({build_id})")


if __name__ == "__main__":
    main()
