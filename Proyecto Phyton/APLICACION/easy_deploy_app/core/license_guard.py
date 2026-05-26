# -*- coding: utf-8 -*-
"""Licencia local de caducidad y proteccion basica contra cambios de reloj."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import winreg
except ImportError:  # pragma: no cover - la aplicacion es Windows, pero facilita pruebas.
    winreg = None

from .. import license_build
from ..constants import APP_VERSION


LICENSE_DAYS = 60
CLOCK_TOLERANCE = timedelta(hours=23)
SESSION_CHECK_MS = 60_000
_BUILD_SIGNING_KEY = b"EasyDeploy-build-license-v1::Adrian-Mata-Cifre::2026"
_STATE_SIGNING_KEY = b"EasyDeploy-local-state-v1::clock-guard::2026"
_REG_PATH = r"Software\EasyDeploy\Security"
_REG_VALUE = "LicenseState"


@dataclass(frozen=True)
class LicenseStatus:
    usable: bool
    blocked: bool
    expired: bool
    days_used: int
    days_remaining: int
    build_utc: datetime | None
    expires_utc: datetime | None
    message: str
    detail: str = ""

    @property
    def summary(self) -> str:
        if self.blocked:
            return "Licencia bloqueada"
        if self.expired:
            return "Licencia caducada"
        return f"Licencia activa: quedan {self.days_remaining} dias"


class LicenseGuard:
    """Gestiona una licencia offline vinculada a la fecha de compilacion."""

    def __init__(self, now_func=None, monotonic_func=None):
        self._now_func = now_func or (lambda: datetime.now(timezone.utc))
        self._monotonic_func = monotonic_func or time.monotonic
        self._build_utc = self._parse_build_utc()
        self._expires_utc = self._build_utc + timedelta(days=LICENSE_DAYS) if self._build_utc else None
        self._build_id = str(getattr(license_build, "BUILD_ID", "") or "")
        self._session_wall = None
        self._session_mono = None
        self.status = self.check_startup()

    @property
    def build_utc(self):
        return self._build_utc

    @property
    def expires_utc(self):
        return self._expires_utc

    @staticmethod
    def tolerance_hours():
        return int(CLOCK_TOLERANCE.total_seconds() // 3600)

    def check_startup(self):
        now = self._now()
        build_error = self._validate_build_signature()
        if build_error:
            return self._blocked_status(build_error, now, persist=False)
        if not self._build_utc or not self._expires_utc or not self._build_id:
            return self._blocked_status("La licencia de compilacion no es valida.", now, persist=False)

        invalid_state = self._find_invalid_state()
        if invalid_state:
            return self._block_permanently(invalid_state, now)

        states = self._load_valid_states()
        matching_states = [state for state in states if state.get("build_id") == self._build_id]
        if any(state.get("blocked") for state in matching_states):
            reason = self._newest_state(matching_states).get("reason") or "La licencia quedo bloqueada."
            return self._blocked_status(reason, now, persist=False)

        if now + CLOCK_TOLERANCE < self._build_utc:
            return self._block_permanently(
                "La fecha del sistema es anterior a la compilacion del programa.",
                now,
            )

        newest_state = self._newest_state(matching_states)
        last_seen = self._parse_dt(newest_state.get("last_seen_utc")) if newest_state else None
        if last_seen and now + CLOCK_TOLERANCE < last_seen:
            return self._block_permanently(
                "Se detecto retroceso de fecha superior a 23 horas.",
                now,
            )

        if now >= self._expires_utc:
            return self._block_permanently(
                "La licencia ha superado los 60 dias desde la compilacion.",
                now,
                expired=True,
            )

        status = self._ok_status(now)
        self._write_state(now, blocked=False, reason="")
        return status

    def start_session(self):
        self._session_wall = self._now()
        self._session_mono = self._monotonic_func()

    def check_session_clock(self):
        now = self._now()
        if not self.status.usable:
            return self.status
        if self._session_wall is None or self._session_mono is None:
            self.start_session()
            return self.status

        elapsed_wall = now - self._session_wall
        elapsed_mono = timedelta(seconds=max(0, self._monotonic_func() - self._session_mono))
        drift = elapsed_wall - elapsed_mono
        if abs(drift) >= timedelta(hours=24):
            self.status = self._block_permanently(
                "Se detecto un salto de fecha de 24 horas o mas durante la ejecucion.",
                now,
            )
            return self.status

        if now >= self._expires_utc:
            self.status = self._block_permanently(
                "La licencia ha caducado durante la ejecucion.",
                now,
                expired=True,
            )
            return self.status

        self.status = self._ok_status(now)
        self._write_state(now, blocked=False, reason="")
        return self.status

    def _now(self):
        now = self._now_func()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return now.astimezone(timezone.utc).replace(microsecond=0)

    def _parse_build_utc(self):
        return self._parse_dt(getattr(license_build, "BUILD_UTC", ""))

    def _validate_build_signature(self):
        build_utc = str(getattr(license_build, "BUILD_UTC", "") or "")
        build_epoch = str(getattr(license_build, "BUILD_EPOCH", "") or "")
        build_id = str(getattr(license_build, "BUILD_ID", "") or "")
        signature = str(getattr(license_build, "BUILD_SIGNATURE", "") or "")

        if build_id == "development-build":
            return ""
        payload = f"{build_utc}|{build_epoch}|{build_id}"
        expected = hmac.new(_BUILD_SIGNING_KEY, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return "La firma interna de licencia no coincide."
        return ""

    def _ok_status(self, now):
        elapsed_seconds = max(0, int((now - self._build_utc).total_seconds()))
        days_used = min(LICENSE_DAYS, elapsed_seconds // 86400)
        days_remaining = max(0, LICENSE_DAYS - days_used)
        return LicenseStatus(
            usable=True,
            blocked=False,
            expired=False,
            days_used=days_used,
            days_remaining=days_remaining,
            build_utc=self._build_utc,
            expires_utc=self._expires_utc,
            message=f"Dia {days_used} de {LICENSE_DAYS}. Quedan {days_remaining} dias.",
        )

    def _blocked_status(self, reason, now, persist=False, expired=False):
        days_used = 0
        days_remaining = 0
        if self._build_utc:
            days_used = min(LICENSE_DAYS, max(0, int((now - self._build_utc).total_seconds()) // 86400))
            days_remaining = max(0, LICENSE_DAYS - days_used)
        status = LicenseStatus(
            usable=False,
            blocked=True,
            expired=expired,
            days_used=days_used,
            days_remaining=days_remaining,
            build_utc=self._build_utc,
            expires_utc=self._expires_utc,
            message=reason,
            detail="Solicita una nueva copia compilada de Easy Deploy.",
        )
        if persist and self._build_id:
            self._write_state(now, blocked=True, reason=reason)
        self.status = status
        return status

    def _block_permanently(self, reason, now, expired=False):
        return self._blocked_status(reason, now, persist=True, expired=expired)

    def _state_paths(self):
        paths = []
        program_data = os.environ.get("PROGRAMDATA")
        local_app_data = os.environ.get("LOCALAPPDATA")
        app_data = os.environ.get("APPDATA")
        for root in (program_data, local_app_data, app_data):
            if root:
                paths.append(Path(root) / "EasyDeploy" / "license_state.json")
        return paths

    def _state_key(self):
        return hashlib.sha256(_STATE_SIGNING_KEY).digest()

    def _sign_payload(self, payload):
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hmac.new(self._state_key(), raw, hashlib.sha256).hexdigest()

    def _encode_state(self, payload):
        envelope = {"payload": payload, "signature": self._sign_payload(payload)}
        raw = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii")

    def _decode_state(self, text):
        raw = base64.urlsafe_b64decode(str(text).encode("ascii"))
        envelope = json.loads(raw.decode("utf-8"))
        payload = envelope.get("payload")
        signature = envelope.get("signature", "")
        if not isinstance(payload, dict):
            raise ValueError("payload invalido")
        expected = self._sign_payload(payload)
        if not hmac.compare_digest(str(signature), expected):
            raise ValueError("firma invalida")
        return payload

    def _write_state(self, now, blocked=False, reason=""):
        payload = {
            "app_version": APP_VERSION,
            "build_id": self._build_id,
            "build_utc": self._format_dt(self._build_utc),
            "expires_utc": self._format_dt(self._expires_utc),
            "last_seen_utc": self._format_dt(now),
            "blocked": bool(blocked),
            "reason": str(reason or ""),
        }
        encoded = self._encode_state(payload)
        for path in self._state_paths():
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(encoded, encoding="ascii")
                if sys.platform.startswith("win"):
                    try:
                        import ctypes

                        ctypes.windll.kernel32.SetFileAttributesW(str(path), 0x02)
                    except Exception:
                        pass
            except OSError:
                pass
        self._write_registry_state(encoded)

    def _find_invalid_state(self):
        for text in self._read_raw_states():
            try:
                self._decode_state(text)
            except Exception:
                return "El estado local de licencia fue modificado o esta corrupto."
        return ""

    def _load_valid_states(self):
        states = []
        for text in self._read_raw_states():
            try:
                states.append(self._decode_state(text))
            except Exception:
                continue
        return states

    def _read_raw_states(self):
        values = []
        for path in self._state_paths():
            try:
                if path.exists():
                    text = path.read_text(encoding="ascii").strip()
                    if text:
                        values.append(text)
            except OSError:
                continue
        reg_value = self._read_registry_state()
        if reg_value:
            values.append(reg_value)
        return values

    def _read_registry_state(self):
        if winreg is None:
            return ""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH) as key:
                value, _ = winreg.QueryValueEx(key, _REG_VALUE)
                return str(value or "").strip()
        except OSError:
            return ""

    def _write_registry_state(self, encoded):
        if winreg is None:
            return
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, _REG_PATH)
            with key:
                winreg.SetValueEx(key, _REG_VALUE, 0, winreg.REG_SZ, encoded)
        except OSError:
            pass

    @staticmethod
    def _newest_state(states):
        newest = {}
        newest_dt = None
        for state in states:
            seen = LicenseGuard._parse_dt(state.get("last_seen_utc"))
            if seen and (newest_dt is None or seen > newest_dt):
                newest = state
                newest_dt = seen
        return newest

    @staticmethod
    def _parse_dt(value):
        if not value:
            return None
        text = str(value).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(text).astimezone(timezone.utc).replace(microsecond=0)
        except ValueError:
            return None

    @staticmethod
    def _format_dt(value):
        if not value:
            return ""
        return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
