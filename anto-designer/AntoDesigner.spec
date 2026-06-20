# -*- mode: python ; coding: utf-8 -*-
# Configuration PyInstaller pour ANTO DESIGNER.
# Build :  pyinstaller AntoDesigner.spec
# Résultat : dist/AntoDesigner/AntoDesigner.exe  (+ dossier de dépendances)

block_cipher = None

a = Analysis(
    ['app_entry.py'],
    pathex=[],
    binaries=[],
    # On embarque les ressources (icône) et le projet de démonstration.
    datas=[
        ('anto_designer/assets/*', 'anto_designer/assets'),
    ],
    hiddenimports=[
        'demo', 'demo.build_demo',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'diffusers', 'numpy.tests'],
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
    name='AntoDesigner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                       # application fenêtrée (pas de terminal)
    disable_windowed_traceback=False,
    icon='anto_designer/assets/icon.ico',
    version='version_info.txt',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AntoDesigner',
)
