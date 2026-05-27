import os
import shutil
import subprocess
from pathlib import Path

try:
    import winreg
except ImportError:  # pragma: no cover - Easy Deploy se ejecuta en Windows.
    winreg = None


class GuidesTasksMixin:
    """Apertura directa de guias PDF desde la carpeta GUIAS."""

    GUIDE_FILES = {
        "Guía DC1": "GUIA DC1.pdf",
        "Guía DC2": "GUIA DC2.pdf",
        "Guía Intercambio Roles": "GUIA INTERCAMBIO ROLES.pdf",
        "Guía Relación de Confianza": "GUIA RELACION DE CONFIANZA.pdf",
        "Guía Jchat": "GUIA JCHAT.pdf",
        "Guía Exchange": "GUIA EXCHANGE.pdf",
        "Guía Skype": "GUIA SKYPE.pdf",
        "Guía D2 D4": "GUIA D2 D4.pdf",
        "Guía Sharepoint": "GUIA SHAREPOINT.pdf",
        "Guía Certificados": "GUIA CERTIFICADOS.pdf",
        "Guía DHCP": "GUIA DHCP.pdf",
        "Guía File Server": "GUIA FILE SERVER.pdf",
        "Guía WDS": "GUIA WDS.pdf",
        "Guía WSUS": "GUIA WSUS.pdf",
    }

    def open_guide_pdf(self, guide_name):
        filename = self.GUIDE_FILES.get(guide_name)
        if not filename:
            self.ui_showerror("Guías", f"No existe una ruta configurada para: {guide_name}")
            return

        guide_path = self._find_guide_pdf(filename)
        if not guide_path:
            checked = "\n".join(f"- {path}" for path in self._guide_roots())
            self.ui_showerror(
                guide_name,
                "No se ha encontrado el PDF solicitado.\n\n"
                f"Archivo buscado: {filename}\n\n"
                "Rutas comprobadas:\n"
                f"{checked}",
            )
            return

        try:
            self._open_pdf_with_windows(guide_path)
        except Exception as exc:
            self.ui_showerror(
                guide_name,
                f"No se pudo abrir la guía PDF.\n\nRuta:\n{guide_path}\n\nDetalle: {exc}",
            )

    def _open_pdf_with_windows(self, pdf_path):
        """Abre un PDF con Firefox si existe; si no, con Microsoft Edge."""
        pdf_path = os.path.abspath(pdf_path)
        opener = self._find_firefox_executable()
        if opener:
            self._launch_browser(opener, pdf_path, firefox=True)
            return

        opener = self._find_edge_executable()
        if opener:
            self._launch_browser(opener, pdf_path, firefox=False)
            return

        raise FileNotFoundError(
            "No se ha encontrado Firefox ni Microsoft Edge.\n\n"
            "Instala Firefox en este equipo y vuelve a pulsar la guía."
        )

    def _launch_browser(self, browser_path, pdf_path, firefox=True):
        pdf_url = Path(pdf_path).as_uri()
        args = [browser_path, "-new-window", pdf_url] if firefox else [browser_path, "--new-window", pdf_url]
        subprocess.Popen(
            args,
            cwd=os.path.dirname(pdf_path),
            close_fds=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    def _find_edge_executable(self):
        candidates = [
            os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(os.environ.get("ProgramFiles", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
        ]
        candidates.extend(
            self._registry_app_candidates(
                (
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe",
                    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe",
                )
            )
        )
        edge_in_path = shutil.which("msedge.exe") or shutil.which("msedge")
        if edge_in_path:
            candidates.append(edge_in_path)
        return self._first_existing_file(candidates)

    def _find_firefox_executable(self):
        candidates = [
            os.path.join(os.environ.get("ProgramFiles", ""), "Mozilla Firefox", "firefox.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Mozilla Firefox", "firefox.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Mozilla Firefox", "firefox.exe"),
        ]
        candidates.extend(
            self._registry_app_candidates(
                (
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\firefox.exe",
                    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\firefox.exe",
                )
            )
        )
        firefox_in_path = shutil.which("firefox.exe") or shutil.which("firefox")
        if firefox_in_path:
            candidates.append(firefox_in_path)
        return self._first_existing_file(candidates)

    def _registry_app_candidates(self, subkeys):
        if winreg is None:
            return []

        candidates = []
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for subkey in subkeys:
                try:
                    with winreg.OpenKey(hive, subkey) as key:
                        path, _ = winreg.QueryValueEx(key, "")
                except OSError:
                    continue
                candidates.append(path)
        return candidates

    def _first_existing_file(self, candidates):
        seen = set()
        for candidate in candidates:
            if not candidate:
                continue
            norm = os.path.normcase(os.path.abspath(candidate))
            if norm in seen:
                continue
            seen.add(norm)
            if os.path.isfile(candidate):
                return candidate
        return None

    def _guide_roots(self):
        roots = []

        payload_root = getattr(self, "payload_root", "")
        if payload_root:
            roots.append(os.path.join(payload_root, "GUIAS"))

        base_path = getattr(self, "base_path", "")
        if base_path:
            current = os.path.abspath(base_path)
            for _ in range(6):
                roots.append(os.path.join(current, "GUIAS"))
                roots.append(os.path.join(current, "EASY DEPLOY", "GUIAS"))
                parent = os.path.dirname(current)
                if parent == current:
                    break
                current = parent

        roots.append(r"C:\Users\amatc\Desktop\PROYECTOS\EASYDEPLOY\EASY DEPLOY\GUIAS")

        unique = []
        seen = set()
        for root in roots:
            norm = os.path.normcase(os.path.abspath(root))
            if norm in seen:
                continue
            seen.add(norm)
            unique.append(root)
        return unique

    def _find_guide_pdf(self, filename):
        target = filename.casefold()
        for root in self._guide_roots():
            if not os.path.isdir(root):
                continue
            exact = os.path.join(root, filename)
            if os.path.isfile(exact):
                return exact
            for entry in os.listdir(root):
                candidate = os.path.join(root, entry)
                if os.path.isfile(candidate) and entry.casefold() == target:
                    return candidate
        return None
