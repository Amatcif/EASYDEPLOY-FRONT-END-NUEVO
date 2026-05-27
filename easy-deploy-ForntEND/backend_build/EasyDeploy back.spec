# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\amatc\\Desktop\\PROYECTOS\\EASYDEPLOY\\Proyecto Phyton\\APLICACION\\easy_deploy_backend_launcher.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['serial', 'serial.tools.list_ports', 'easy_deploy_app.network_tools', 'easy_deploy_app.network_tools.switchCONF', 'easy_deploy_app.network_tools.switchCisco', 'easy_deploy_app.network_tools.r3', 'easy_deploy_app.network_tools.addressing', 'easy_deploy_app.network_tools.asa', 'easy_deploy_app.network_tools.checkpoint', 'easy_deploy_app.network_tools.topology'],
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
    name='EasyDeploy back',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
