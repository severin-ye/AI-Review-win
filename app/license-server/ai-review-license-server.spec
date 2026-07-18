# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec：把许可证服务器打成单文件 句读授权中心.exe。

构建（在 app/license-server/ 下，venv 需 pip install pyinstaller）：
    ..\\server\\.venv\\Scripts\\python -m PyInstaller ai-review-license-server.spec --noconfirm
产物：app/license-server/dist/句读授权中心.exe

说明（仿 app/server/ai-review-backend.spec）：
- pkg_resources 运行时钩子（pyi_rth_pkgres）依赖 setuptools 78 的外部化依赖
  （jaraco.text / platformdirs / packaging / more_itertools 不再是 vendored，需显式收集——已踩过的坑）。
- admin_ui/index.html 作为数据文件打入包内。
"""
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

datas = [("license_server/admin_ui/index.html", "license_server/admin_ui")]
binaries = []
hiddenimports = collect_submodules("license_server")

# pkg_resources 外部化依赖（坑已踩过，务必保留）
for package in (
    "pkg_resources",
    "jaraco",
    "jaraco.text",
    "jaraco.functools",
    "jaraco.context",
    "platformdirs",
    "packaging",
    "more_itertools",
):
    try:
        hiddenimports += collect_submodules(package)
    except Exception:
        hiddenimports.append(package)

for package in ("uvicorn", "win32crypt"):
    datas += collect_data_files(package)

excludes = ["pytest", "PyInstaller", "pip", "setuptools", "tkinter", "tests", "torch"]

a = Analysis(
    ["run.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
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
    name="句读授权中心",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # 杀软误报规避，不压缩
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icon.ico",
)
