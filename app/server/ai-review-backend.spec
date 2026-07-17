# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec：把 FastAPI 后端打成单文件 ai-review-backend.exe（设计文档 §9）。

构建（在 app/server/ 下，venv 需 pip install pyinstaller）：
    .venv\\Scripts\\python -m PyInstaller ai-review-backend.spec --noconfirm
产物：app/server/dist/ai-review-backend.exe → electron-builder extraResources 映射到 resources/backend/。

说明：
- 模型文件（.data/models/，数 GB）与 CUDA 相关动态库不打入包内：模型走首次启动后
  设置页预下载（POST /api/models/download）；本机 torch 为 CPU 版，nvidia/* 排除只是保险。
- collect_data_files 覆盖含运行时数据文件的包（lancedb 的 native 清单、langchain 等）；
  hiddenimports 收集 app 全部子模块 + uvicorn 的常用 worker/loop 实现。
"""
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

block_cipher = None

datas = []
binaries = []
hiddenimports = collect_submodules("app")

for package in ("lancedb", "langchain", "langchain_community", "wtpsplit", "jieba"):
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
        datas += pkg_datas
        binaries += pkg_binaries
        hiddenimports += pkg_hidden
    except Exception:
        # 包结构变化导致 collect 失败时退化为仅数据文件收集
        datas += collect_data_files(package)

# pkg_resources 运行时钩子（pyi_rth_pkgres）依赖 jaraco.* 子模块，需显式收集
for package in ("pkg_resources", "jaraco", "jaraco.text", "jaraco.functools", "jaraco.context"):
    try:
        hiddenimports += collect_submodules(package)
    except Exception:
        hiddenimports.append(package)

# 排除：测试/构建工具与 CUDA（CPU 版 torch 不需要 nvidia 运行库）
excludes = ["pytest", "PyInstaller", "pip", "setuptools", "tkinter", "tests"]
binaries = [b for b in binaries if "nvidia" not in b[0].lower() and "cudnn" not in b[0].lower()]

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
    name="ai-review-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # 杀软误报规避，不压缩
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # sidecar 日志经 Electron onLog 透传，保留控制台
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
