# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: B_worker（one-folder）。

B 専用 venv でビルドする。numpy を同梱し、PySide6 は一切含めない。
    pyinstaller b_worker.spec
出力: dist/b_worker/  （中に b_worker 実行ファイル + numpy）
"""

block_cipher = None

a = Analysis(
    ['worker.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=['b_core', 'b_core.stats'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # A 側の依存を絶対に巻き込まないよう明示的に除外する。
    excludes=['PySide6', 'PyQt6', 'PyQt5', 'shiboken6', 'tkinter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='b_worker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,  # worker は stdin/stdout でやり取りするのでコンソール型
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='b_worker',
)
