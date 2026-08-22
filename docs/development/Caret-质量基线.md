# Caret 质量基线

> 基线日期：2026-07-18  
> 执行入口：`powershell -NoProfile -ExecutionPolicy Bypass -File scripts/quality-baseline.ps1`

## 自动化结果

| 检查 | 结果 |
| --- | --- |
| TypeScript 类型检查 | 通过，退出码 0 |
| Electron 许可证测试 | 5 个文件、63 项通过 |
| 业务后端测试 | 34 项通过、2 条上游弃用警告 |
| Caret License Center 测试 | 72 项通过、0 警告 |
| Electron/Vite 构建 | 通过，退出码 0 |
| npm audit | 0 个已知漏洞 |
| 业务后端 pip-audit | 0 个适用的已知漏洞 |
| 授权端 pip-audit | 0 个已知漏洞 |
| `app/` / `legacy/` 边界 | 通过 |

两条保留警告均不是 Caret 自有弃用调用：一条来自 `jieba` 对 `pkg_resources` 的使用；一条来自 `langchain-community` 的整体 sunset 提示。BM25Retriever 截至本基线日期没有官方独立继任包，`langchain-classic` 只是转发回 `langchain-community` 的弃用兼容层，因此暂不做无效迁移。

## 安全审计说明

`transformers` 已从 4.x 升级并约束在 `>=5.5,<5.6`，用于修复旧版模型配置与检查点加载路径的 RCE。该范围已验证 `wtpsplit 2.2.1`、`sentence-transformers 5.6.0`、`torch 2.13.0+cpu` 和 `torchvision 0.28.0+cpu` 可导入且 `pip check` 通过。

审计仅临时忽略 `PYSEC-2025-217`（X-CLIP checkpoint conversion）：上游尚未发布修复版本，Caret 不加载 X-CLIP 模型。该例外在本地基线脚本和 CI 中按漏洞编号显式列出；不得改为全局忽略。

## Renderer 体积趋势

引入四个页面的路由级懒加载后，renderer 主 JS 从此前约 951 KB 降到 852.14 KB；页面 chunk 分别为：

- 文档库：37.71 KB；
- 审校工作台：39.70 KB；
- 知识库：10.42 KB；
- 设置：20.78 KB；
- 公共 CSS：41.38 KB。

此处只记录趋势，不设置硬性 bundle 门槛。

## 依赖安装链路

- `npm run deps:ci`：通过进程环境变量使用 Electron 镜像，验证成功；
- `npm run deps:ci:official`：不设置镜像，官方源路径验证成功；
- `force_no_cache=true` 的镜像安装验证成功；
- 项目级 `.npmrc` 已移除，npm 不再报告未知 `ELECTRON_MIRROR` 配置；
- `npm run backend:models` 从 PyTorch CPU 源安装 `torch` 与 `torchvision`。

## 持续维护

`.github/workflows/quality.yml` 在 push、pull request、每月定时和手动触发时执行完整 Node/Python 基线；`.github/dependabot.yml` 每月检查根 npm、业务后端 pip 与授权端 pip 依赖。
