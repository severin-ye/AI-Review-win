# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/core/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config', 'config'),  # 仅包含必要的配置文件
        ('material', 'material')  # 仅包含必要的资源文件
    ],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
        'win32com.client',
        'winshell',
        'json',
        'subprocess',
        'shutil',
        's_1_auto_ai',
        's_2_select_replace',
        's_3_clear_out',
        's_4_config_use',
        'w0_file_path',
        'w1_table_about',
        'w2_docx_to_md',
        'w3_smart_divide',
        'w4_ai_answer',
        'w5_same_find',
        'w6_1_key_generator',
        'w6_2_key_verifier',
        'time_lock'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ai_review',
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
    icon='material/2-logo.ico',
    version='build/file_version_info.txt',
)
