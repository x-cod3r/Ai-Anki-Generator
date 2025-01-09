# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=[],
    datas=[
          (
               'C:\\Users\\Drmah\\AppData\\Local\\Programs\\Python\\Python311\\Lib\\site-packages\\emoji\\unicode_codes\\*',
              'emoji\\unicode_codes'
          ),
           ('DejaVuSans.ttf', '.'),
           ('icon.png', '.'),
    ],
    hiddenimports=[
         'fpdf', # ==1.7.2
         'genanki', # ==0.13.1
         'PIL', # ==11.1.0
         'PIL._imaging',  # ==11.1.0
         'PIL.Image',  # ==11.1.0
         'protobuf', # ==5.29.2
         'google.protobuf', # ==5.29.2
         'pypdf', # ==5.1.0
         'pytesseract', # ==0.3.13
          'docx', # ==1.1.2
         'requests', # ==2.32.3
         'tqdm', # ==4.67.1
         'google.generativeai', # ==0.8.3
         'tkinter',
         'tkinter.filedialog',
         'tkinter.messagebox',
         'tkinter.ttk',
         'os',
         'pathlib',
         'threading',
         'logging',
          'io',
          'functools',
          'webbrowser',
           'subprocess'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)


pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Ai-AnkiCreator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # show console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.png',
)