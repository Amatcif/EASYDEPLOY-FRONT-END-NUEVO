# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import runpy

from PyInstaller.utils.hooks import collect_submodules


APP_DIR = Path(SPECPATH)
STAMP_SCRIPT = APP_DIR / "tools" / "stamp_license_build.py"
if STAMP_SCRIPT.exists():
    runpy.run_path(str(STAMP_SCRIPT), run_name="__main__")


def _validate_no_python_datas(datas):
    bad = [str(source) for source, _target in datas if Path(str(source)).suffix.casefold() == ".py"]
    if bad:
        raise RuntimeError(
            "Build bloqueado: no se permite incluir archivos .py como datas/add-data: "
            + ", ".join(bad)
        )
    return datas


def _validate_no_python_add_data_in_build_scripts():
    build_files = [
        APP_DIR / "Crear .EXE" / "build_easy_deploy_seguro.bat",
        APP_DIR / "Crear .EXE" / "Comando crear exe.txt",
    ]
    matches = []
    for path in build_files:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line_number, line in enumerate(text.splitlines(), start=1):
            lowered = line.casefold()
            if "--add-data" in lowered and ".py" in lowered:
                matches.append(f"{path}:{line_number}")
    if matches:
        raise RuntimeError(
            "Build bloqueado: hay --add-data con .py en scripts de build: "
            + ", ".join(matches)
        )


_validate_no_python_add_data_in_build_scripts()

serial_hiddenimports = collect_submodules("serial")
network_tool_hiddenimports = [
    "easy_deploy_app.network_tools.switchCONF",
    "easy_deploy_app.network_tools.switchCisco",
    "easy_deploy_app.network_tools.r3",
]


a = Analysis(
    [str(APP_DIR / 'EASY DEPLOY.py')],
    pathex=[str(APP_DIR)],
    binaries=[],
    datas=_validate_no_python_datas([
        (str(APP_DIR / 'iconos' / 'logotipo.ico'), 'iconos'),
        (str(APP_DIR / 'iconos' / 'EscudoRt.png'), 'iconos'),
    ]),
    hiddenimports=serial_hiddenimports + network_tool_hiddenimports + ['sqlite3', '_sqlite3'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='EASY DEPLOY',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
    icon=[str(APP_DIR / 'iconos' / 'logotipo.ico')],
)
