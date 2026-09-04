# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: A（one-folder, GUI）。

A 専用 venv でビルドする。PySide6 を同梱し、numpy は一切含めない。
    pyinstaller app_a.spec
出力: dist/app_a/  （中に A 実行ファイル + PySide6）

B_worker はこの spec では同梱しない。パッケージング段階（§7）で
dist/b_worker/ の中身を A の配布ディレクトリへ配置する。
"""

block_cipher = None

a = Analysis(
    ['run_app_a.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=['app_a', 'app_a.main_window', 'app_a.worker_client', 'app_a.paths'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # B 側の依存を絶対に巻き込まないよう明示的に除外する（依存分離の担保）。
    excludes=['numpy', 'b_core'],
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
    name='app_a',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # GUI アプリなのでコンソール無し
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
    name='app_a',
)
