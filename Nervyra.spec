# -*- mode: python ; coding: utf-8 -*-
# Nervyra.spec (compatible across PyInstaller versions)

import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None


def collect_tree(src_dir: str, dest_root: str):
    """
    Collect an entire folder into PyInstaller 'datas' as 2-tuples (src_file, dest_dir).

    Works across PyInstaller versions (does not rely on Tree()).
    """
    datas_local = []
    src_dir = os.path.abspath(src_dir)

    if not os.path.isdir(src_dir):
        return datas_local

    for root, _, files in os.walk(src_dir):
        for filename in files:
            src_file = os.path.join(root, filename)
            rel_dir = os.path.relpath(root, src_dir)  # '.' or subfolder path
            dest_dir = dest_root if rel_dir == "." else os.path.join(dest_root, rel_dir)
            datas_local.append((src_file, dest_dir))
    return datas_local


# Collect all submodules (safe for future lazy imports)
hiddenimports = collect_submodules('nervyra')

# Data files to bundle
datas = []
datas += collect_tree('Property', 'Property')
datas += collect_tree('Liability', 'Liability')

# Root-level files (only if present)
for fname in ('users.json', 'icon.ico', 'icon.png'):
    if os.path.isfile(fname):
        datas.append((fname, '.'))

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Nervyra',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'] if os.path.isfile('icon.ico') else None,
)
