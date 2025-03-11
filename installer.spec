# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['scripts/installer.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('material/1-logo.ico', '.'),  # 安装程序图标
        ('material/2-logo.ico', '.'),  # 主程序图标
        ('dist/AI审校助手.exe', '.')  # 主程序
    ],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
        'tkinter.filedialog',
        'win32com.client',
        'win32api',
        'win32gui',
        'win32con',
        'winreg',
        'json',
        'subprocess',
        'shutil',
        'traceback',
        'logging',
        'datetime'
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
    name='AI审校助手安装程序',
    debug=True,  # 启用调试模式
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 保持控制台窗口以显示错误
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='material/1-logo.ico',
) 